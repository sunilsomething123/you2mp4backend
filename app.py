import os
import re
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pytube import YouTube
from moviepy.editor import VideoFileClip
import requests

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'mp4'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_video_id(url):
    """
    Extract the video ID from the YouTube URL.
    """
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.match(pattern, url)
    return match.group(1) if match else None

def fetch_video_info(video_id):
    """
    Fetch video information from YouTube API.
    """
    params = {
        'part': 'snippet,contentDetails',
        'id': video_id,
        'key': API_KEY
    }
    response = requests.get(YOUTUBE_API_URL, params=params)
    
    if response.status_code != 200:
        logger.error(f"YouTube API error: {response.status_code}, {response.text}")
        response.raise_for_status()
    
    video_info = response.json()
    if 'items' not in video_info or not video_info['items']:
        raise ValueError("No video information found")
    
    item = video_info['items'][0]
    return {
        'title': item['snippet']['title'],
        'description': item['snippet']['description'],
        'thumbnail': item['snippet']['thumbnails']['high']['url'],
        'duration': item['contentDetails']['duration']
    }

@app.route('/api/video-info', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '720p')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4', resolution=quality).first()

        if not video:
            return jsonify({'error': f'No {quality} version available'}), 400

        download_url = video.url  # This is the direct URL to the video
        return jsonify({'download_url': download_url})
    except Exception as e:
        logger.error(f"Error processing download request: {str(e)}")
        return jsonify({'error': 'Failed to process download request'}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '720p')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4', resolution=quality).first()

        if not video:
            return jsonify({'error': f'No {quality} version available'}), 400

        sanitized_title = re.sub(r'[^\w\s-]', '', yt.title)
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{sanitized_title}.mp4")
        video.download(output_path=app.config['UPLOAD_FOLDER'], filename=f"{sanitized_title}.mp4")

        return jsonify({
            'message': 'Video downloaded successfully',
            'filename': os.path.basename(output_path),
            'path': output_path
        })
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return jsonify({'error': 'Failed to download video'}), 500

@app.route('/api/convert-to-mp3', methods=['POST'])
def convert_to_mp3():
    data = request.json
    filename = data.get('filename')

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    try:
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.splitext(filename)[0] + '.mp3')

        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_path)

        video.close()
        audio.close()

        return jsonify({
            'message': 'Video converted to MP3 successfully',
            'filename': os.path.basename(audio_path),
            'path': audio_path
        })
    except Exception as e:
        logger.error(f"Error converting video to MP3: {str(e)}")
        return jsonify({'error': 'Failed to convert video to MP3'}), 500

@app.route('/api/download-file/<filename>')
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.isfile(file_path):
            return jsonify({'error': 'File not found'}), 404
        return send_file(file_path, as_attachment=True)
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
