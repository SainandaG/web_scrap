from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
from downloader import YouTubeDownloader

app = Flask(__name__)

# Ensure downloads directory exists
DOWNLOADS_DIR = os.path.join(os.getcwd(), 'downloads')
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# Dictionary to store progress of active downloads
progress_storage = {}

def progress_callback(progress, video_id):
    progress_storage[video_id] = progress * 100

def status_callback(status, video_id):
    print(f"Status for {video_id}: {status}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    downloader = YouTubeDownloader()
    info = downloader.get_video_info(url)
    return jsonify(info)

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')
    resolution = data.get('resolution', 'Best')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    video_id = url.split('=')[-1] # Simple ID extraction
    progress_storage[video_id] = 0
    
    def run_download():
        downloader = YouTubeDownloader(
            progress_callback=lambda p: progress_callback(p, video_id),
            status_callback=lambda s: status_callback(s, video_id)
        )
        downloader.download(url, resolution, start_time, end_time)

    threading.Thread(target=run_download).start()
    return jsonify({"status": "Started", "video_id": video_id})

@app.route('/api/progress/<video_id>')
def get_progress(video_id):
    progress = progress_storage.get(video_id, 0)
    return jsonify({"progress": progress})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
