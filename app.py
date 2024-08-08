import os
import re
import unicodedata
import logging
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import yt_dlp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
limiter = Limiter(
       get_remote_address,
       app=app,
       default_limits=["200 per day", "50 per hour"],
       storage_uri="memory://"
   )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'mp4', 'mp3', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
MAX_FILESIZE = 2 * 1024 * 1024 * 1024  # 2GB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
API_KEY = os.environ.get('YOUTUBE_API_KEY')

if not API_KEY:
    logger.error("YouTube API key not found. Please set the YOUTUBE_API_KEY environment variable.")
    raise ValueError("YouTube API key is missing")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_filename(filename):
    return re.sub(r'[^\w\-_\. ]', '_', filename)

@app.route('/api/video-info', methods=['POST'])
@limiter.limit("30 per minute")
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
        formats = fetch_video_formats(url)
        
        return jsonify({**video_data, "formats": formats})
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return jsonify({"error": "Network error occurred"}), 500
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

def extract_video_id(url):
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?(?:live\/)?(?P<id>[^\/\?\&]+)',
        r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?P<id>[^\/\?\&]+)',
    ]
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group('id')
    return None

def fetch_video_info(video_id):
    params = {
        'part': 'snippet,contentDetails,statistics',
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
        'id': video_id,
        'title': item['snippet']['title'],
        'description': item['snippet']['description'],
        'thumbnail': item['snippet']['thumbnails']['high']['url'],
        'duration': item['contentDetails']['duration'],
        'viewCount': item['statistics']['viewCount'],
        'likeCount': item['statistics'].get('likeCount', 'N/A'),
        'publishedAt': item['snippet']['publishedAt']
    }

def fetch_video_formats(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'youtube_include_dash_manifest': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = []
        for f in info['formats']:
            if 'asr' not in f:  # Skip formats without audio
                formats.append({
                    'format_id': f['format_id'],
                    'ext': f['ext'],
                    'resolution': f.get('resolution', 'N/A'),
                    'filesize': f.get('filesize', 0),
                    'vcodec': f.get('vcodec', 'N/A'),
                    'acodec': f.get('acodec', 'N/A'),
                })
        return formats

@app.route('/api/download', methods=['GET'])
@limiter.limit("10 per minute")
def download_video():
    url = request.args.get('url')
    format_id = request.args.get('format')

    if not url or not format_id:
        return jsonify({'error': 'URL and format are required'}), 400

    try:
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            sanitized_filename = sanitize_filename(filename)

            def generate():
                with open(filename, 'rb') as file:
                    while True:
                        chunk = file.read(8192)
                        if not chunk:
                            break
                        yield chunk
                os.remove(filename)  # Clean up the file after streaming

        headers = {
            'Content-Disposition': f'attachment; filename="{sanitized_filename}"',
            'Content-Type': 'application/octet-stream'
        }

        return Response(stream_with_context(generate()), headers=headers)

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
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            mp3_filename = os.path.splitext(filename)[0] + '.mp3'
            sanitized_mp3_filename = sanitize_filename(mp3_filename)

        return jsonify({
            'message': 'Audio extracted and converted to MP3 successfully',
            'filename': sanitized_mp3_filename,
            'path': mp3_filename
        })
    except Exception as e:
        logger.error(f"Error converting to MP3: {str(e)}")
        return jsonify({'error': f'Failed to convert to MP3: {str(e)}'}), 500

@app.route('/api/download-file/<filename>')
def download_file(filename):
    try:
        return Response(
            stream_with_context(generate_file_stream(filename)),
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/octet-stream",
            },
        )
    except Exception as e:
        logger.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Failed to send file'}), 500

def generate_file_stream(filename):
    with open(os.path.join(app.config['UPLOAD_FOLDER'], filename), 'rb') as file:
        while True:
            chunk = file.read(8192)
            if not chunk:
                break
            yield chunk

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
    os.makedirs('downloads', exist_ok=True)
    app.run(debug=True)
