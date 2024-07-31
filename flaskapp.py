from flask import Flask, request, jsonify
import os
import re

app = Flask(__name__)

YOUTUBE_API_KEY = os.getenv('AIzaSyBuLDbPhS5QddaZaETco_-MUtngmGSscH8')

def is_valid_youtube_url(url):
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/.+')
    return youtube_regex.match(url) is not None

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    video_url = data.get('url')
    if not video_url or not is_valid_youtube_url(video_url):
        return jsonify({"success": False, "message": "Invalid URL"}), 400

    video_id = video_url.split('v=')[1] if 'v=' in video_url else video_url.split('/')[-1]
    download_url = f"https://youtube.com/download/{video_id}.mp4"

    return jsonify({"success": True, "downloadUrl": download_url, "videoId": video_id})

if __name__ == '__main__':
    app.run(debug=True)
