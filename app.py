from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import threading
from downloader import YouTubeDownloader

app = Flask(__name__)

# Ensure downloads directory exists
# Use /tmp for Vercel compatibility
if os.environ.get('VERCEL'):
    DOWNLOADS_DIR = '/tmp/downloads'
else:
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
    url = request.form.get('url')
    if not url:
        # Fallback for old JSON requests
        if request.is_json:
            url = request.json.get('url')
        if not url:
            return jsonify({"error": "No URL provided"}), 400
    
    cookiefile_path = None
    if 'cookies' in request.files:
        file = request.files['cookies']
        if file.filename != '':
            cookiefile_path = os.path.join(DOWNLOADS_DIR, f"temp_cookies_{os.urandom(4).hex()}.txt")
            file.save(cookiefile_path)

    downloader = YouTubeDownloader()
    info = downloader.get_video_info(url, cookiefile_path=cookiefile_path)
    
    # Clean up temp cookie file
    if cookiefile_path and os.path.exists(cookiefile_path):
        try: os.remove(cookiefile_path)
        except: pass

    return jsonify(info)

@app.route('/api/download', methods=['POST'])
def download_video():
    url = request.form.get('url')
    resolution = request.form.get('resolution', 'Best')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    
    # Fallback for old JSON requests
    if not url and request.is_json:
        data = request.json
        url = data.get('url')
        resolution = data.get('resolution', 'Best')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    video_id = url.split('=')[-1] # Simple ID extraction
    progress_storage[video_id] = 0
    
    cookiefile_path = None
    if 'cookies' in request.files:
        file = request.files['cookies']
        if file.filename != '':
            cookiefile_path = os.path.join(DOWNLOADS_DIR, f"dl_cookies_{video_id}_{os.urandom(4).hex()}.txt")
            file.save(cookiefile_path)

    def run_download():
        downloader = YouTubeDownloader(
            progress_callback=lambda p: progress_callback(p, video_id),
            status_callback=lambda s: status_callback(s, video_id)
        )
        # Point to the correct directory
        downloader.download_dir = DOWNLOADS_DIR
        filename = downloader.download(url, resolution, start_time, end_time, cookiefile_path=cookiefile_path)
        
        # Clean up temp cookie file
        if cookiefile_path and os.path.exists(cookiefile_path):
            try: os.remove(cookiefile_path)
            except: pass

        if filename:
            progress_storage[video_id + "_file"] = filename
            progress_storage[video_id] = 100 # Ensure it hits 100%

    threading.Thread(target=run_download).start()
    return jsonify({"status": "Started", "video_id": video_id})

@app.route('/api/download_file/<video_id>')
def download_file(video_id):
    filename = progress_storage.get(video_id + "_file")
    if not filename:
        return jsonify({"error": "File not found or still processing"}), 404
    
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)

@app.route('/api/progress/<video_id>')
def get_progress(video_id):
    progress = progress_storage.get(video_id, 0)
    return jsonify({"progress": progress})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
