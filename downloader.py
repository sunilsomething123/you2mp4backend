import os
import re
from pytube import YouTube
from urllib.parse import parse_qs, urlparse

def sanitize_filename(title):
    return re.sub(r'[^\w\-_\. ]', '_', title)

def get_video_id(url):
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in {'www.youtube.com', 'youtube.com'}:
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    return None

def download_video(url, quality, output_path):
    try:
        yt = YouTube(url)
        video = yt.streams.filter(progressive=True, file_extension='mp4', resolution=quality).first()

        if not video:
            raise ValueError(f'No {quality} version available')

        filename = f"{sanitize_filename(yt.title)}_{quality}.mp4"
        filepath = os.path.join(output_path, filename)
        video.download(output_path=output_path, filename=filename)

        video_id = get_video_id(url)
        return {
            'filename': filename,
            'filepath': filepath,
            'title': yt.title,
            'video_id': video_id
        }
    except Exception as e:
        raise Exception(f"Error downloading video: {str(e)}")
