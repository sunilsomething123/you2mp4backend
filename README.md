# YouTube to MP4 Converter Backend

This is the backend for a YouTube to MP4 converter application.

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in a `.env` file
4. Run the application: `flask run`

## API Endpoints

- POST `/api/video-info`: Get information about a YouTube video
- POST `/api/download`: Download a YouTube video
- POST `/api/convert-to-mp3`: Convert a video to MP3
- GET `/api/download-file/<filename>`: Download a processed file
- POST `/api/delete-file`: Delete a processed file

## Deployment

This application is configured for deployment on Render. See `render.yaml` for details.
