import os
from flask import Blueprint, request, jsonify, send_file, current_app
from app.downloader import download_video, get_video_id

main = Blueprint('main', __name__)

@main.route('/api/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '720p')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        result = download_video(url, quality, current_app.config['UPLOAD_FOLDER'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/video-info', methods=['POST'])
def video_info():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        video_id = get_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        return jsonify({'video_id': video_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/api/download-file/<filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
