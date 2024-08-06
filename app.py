import os
import re
import unicodedata
import logging
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
from pytube import YouTube
from moviepy.editor import VideoFileClip
import requests
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
CORS(app)
limiter = Limiter(app, key_func=get_remote_address)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'mp4', 'mp3'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
API_KEY = "AIzaSyBuLDbPhS5QddaZaETco_-MUtngmGSscH8"  # Replace with your actual API key

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/video-info', methods=['POST'])
@limiter.limit("30 per minute")
def get_video_info():
    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400

        yt = YouTube(url)
        
        if is_age_restricted(yt):
            return jsonify({'error': 'This video is age-restricted and cannot be downloaded'}), 403

        formats = []
        for stream in yt.streams:
            formats.append({
                'itag': stream.itag,
                'mimeType': stream.mime_type,
                'qualityLabel': stream.resolution if stream.resolution else 'Audio Only',
                'bitrate': stream.bitrate,
                'audioBitrate': stream.abr,
                'contentLength': stream.filesize,
                'fps': stream.fps if stream.includes_video_track else None,
            })

        return jsonify({
            'videoDetails': {
                'videoId': yt.video_id,
                'title': yt.title,
                'lengthSeconds': yt.length,
                'channelId': yt.channel_id,
                'channelName': yt.author,
                'description': yt.description,
                'viewCount': yt.views,
                'publishDate': yt.publish_date.isoformat() if yt.publish_date else None,
                'uploadDate': yt.publish_date.isoformat() if yt.publish_date else None,
                'thumbnails': [yt.thumbnail_url],
            },
            'formats': formats
        })
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}")
        return jsonify({"error": "Failed to fetch video information"}), 500

def is_age_restricted(yt):
    return yt.age_restricted

def select_format(formats, quality='highest'):
    if quality == 'highest':
        return max(formats, key=lambda f: f['bitrate'] if f['mimeType'].startswith('video') else 0)
    elif quality == 'lowest':
        return min(formats, key=lambda f: f['bitrate'] if f['mimeType'].startswith('video') else float('inf'))
    else:
        return next((f for f in formats if f['qualityLabel'] == quality), None)

@app.route('/api/download', methods=['GET'])
@limiter.limit("10 per minute")
def download_video():
    url = request.args.get('url')
    itag = request.args.get('itag')

    if not url or not itag:
        return jsonify({'error': 'URL and itag are required'}), 400

    try:
        yt = YouTube(url)
        
        if is_age_restricted(yt):
            return jsonify({'error': 'This video is age-restricted and cannot be downloaded'}), 403

        stream = yt.streams.get_by_itag(itag)
        
        if not stream:
            return jsonify({'error': 'Selected format not available'}), 400

        sanitized_title = re.sub(r'[^\w\s-]', '', yt.title)
        filename = f"{sanitized_title}.mp4"

        def generate():
            with stream.stream() as stream_data:
                while True:
                    chunk = stream_data.read(8192)
                    if not chunk:
                        break
                    yield chunk

        headers = {
            'Content-Type': stream.mime_type,
            'Content-Disposition': f'attachment; filename="{filename}"'
        }

        return Response(generate(), headers=headers)
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return jsonify({'error': f'Failed to download video: {str(e)}'}), 500

@app.route('/api/convert-to-mp3', methods=['POST'])
@limiter.limit("5 per minute")
def convert_to_mp3():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        yt = YouTube(url)
        
        if is_age_restricted(yt):
            return jsonify({'error': 'This video is age-restricted and cannot be downloaded'}), 403

        audio_stream = yt.streams.filter(only_audio=True).first()
        
        if not audio_stream:
            return jsonify({'error': 'No audio stream available'}), 400

        sanitized_title = re.sub(r'[^\w\s-]', '', yt.title)
        temp_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{sanitized_title}.mp4")
        audio_stream.download(output_path=app.config['UPLOAD_FOLDER'], filename=temp_file)

        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{sanitized_title}.mp3")
        video = VideoFileClip(temp_file)
        audio = video.audio
        audio.write_audiofile(audio_path)

        video.close()
        audio.close()
        os.remove(temp_file)

        return jsonify({
            'message': 'Audio extracted and converted to MP3 successfully',
            'filename': os.path.basename(audio_path),
            'path': audio_path
        })
    except Exception as e:
        logger.error(f"Error converting to MP3: {str(e)}")
        return jsonify({'error': f'Failed to convert to MP3: {str(e)}'}), 500

@app.route('/api/download-file/<filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)
    except Exception as e:
        logger.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Failed to send file'}), 500

@app.route('/api/delete-file', methods=['POST'])
def delete_file():
    data = request.json
    filename = data.get('filename')

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'message': 'File deleted successfully'})
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return jsonify({'error': 'Failed to delete file'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True)
