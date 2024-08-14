import os
import re
import logging
from flask import Flask, request, jsonify, send_file, redirect
from flask_cors import CORS
from moviepy.editor import VideoFileClip
import requests

app = Flask(__name__)
# Configure CORS with specific settings
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST"]}})

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
API_KEY = os.getenv('YOUTUBE_API_KEY', 'AIzaSyAL6k2uiQclis3E0nhj-1YSVJVjF-iBy9g')  # Replace with your actual API key

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_video_id(youtube_url):
    """
    Extract the video ID from a YouTube URL.
    """
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def generate_google_video_url(video_id):
    """
    Generate a Google Video URL for the given YouTube video ID.
    """
    base_url = "https://rr4---sn-gwpa-cagel.googlevideo.com/videoplayback"
    params = {
        "expire": "1723369330",  # Example expiration time
        "ei": "EjO4ZsKHJbms9fwPsJi86AY",  # Example parameter
        "ip": "2409%3A408c%3Aae3d%3A75c1%3Ae311%3Aec28%3A7505%3A966e",  # Example IP
        "id": f"o-{video_id}",
        "itag": "18",
        "source": "youtube",
        "requiressl": "yes",
        "mime": "video/mp4",
        "dur": "219.985",
        "lmt": "1697894246773778",
        "mt": "1723347409",
        "ratebypass": "yes",
        "vprv": "1",
        "clen": "13884482",
        "n": video_id
    }
    # Construct the URL
    url_params = "&".join([f"{key}={value}" for key, value in params.items()])
    return f"{base_url}?{url_params}"
    
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
        app.logger.error(f"YouTube API error: {response.status_code}, {response.text}")
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
def get_video_info():
    try:
        data = request.json
        url = data.get('url')
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Extract video ID from the URL
        video_id = extract_video_id(url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        # Log the video ID
        app.logger.debug(f"Fetching info for video ID: {video_id}")

        # Fetch video information from YouTube API
        video_data = fetch_video_info(video_id)
        
        return jsonify(video_data)
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}")
        return jsonify({"error": "Failed to fetch video information"}), 500

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

@app.route('/api/get-google-video-url', methods=['GET'])
def get_google_video_url():
    youtube_url = request.args.get('url')
    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400
    
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    google_video_url = generate_google_video_url(video_id)
    
    # Directly redirect to the Google video playback URL
    return redirect(google_video_url, code=302)

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
    
if __name__ == '__main__':
    app.run(debug=True)
