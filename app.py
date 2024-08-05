import os
import re
import logging
import traceback
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pytube import YouTube
import requests
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

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
def get_video_info():
    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        logger.info(f"Fetching info for video ID: {video_id}")

        video_data = fetch_video_info(video_id)
        
        return jsonify(video_data)
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}")
        return jsonify({"error": "Failed to fetch video information"}), 500

def extract_video_id(url):
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.match(pattern, url)
    return match.group(1) if match else None

def fetch_video_info(video_id):
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
        video_filename = f"{sanitized_title}.mp4"
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        video.download(output_path=app.config['UPLOAD_FOLDER'], filename=video_filename)

        # Extract audio
        audio = yt.streams.filter(only_audio=True).first()
        audio_filename = f"{sanitized_title}.mp3"
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename)
        audio.download(output_path=app.config['UPLOAD_FOLDER'], filename=audio_filename)

        # Convert audio to mp3
        AudioSegment.from_file(audio_path).export(audio_path, format="mp3")

        return jsonify({
            'message': 'Video downloaded and audio extracted successfully',
            'video_filename': video_filename,
            'video_path': video_path,
            'audio_filename': audio_filename,
            'audio_path': audio_path
        })
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to download video: {str(e)}'}), 500

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
