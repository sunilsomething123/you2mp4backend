import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pytube import YouTube
from moviepy.editor import *
import logging

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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        yt = YouTube(url)
        return jsonify({
            'title': yt.title,
            'duration': yt.length,
            'thumbnail': yt.thumbnail_url,
            'author': yt.author,
            'views': yt.views,
            'publish_date': yt.publish_date.isoformat() if yt.publish_date else None
        })
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}")
        return jsonify({'error': 'Failed to fetch video information'}), 500

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

        output_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(yt.title) + '.mp4')
        video.download(output_path=app.config['UPLOAD_FOLDER'], filename=secure_filename(yt.title) + '.mp4')

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
