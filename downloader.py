import yt_dlp
import os

class YouTubeDownloader:
    def __init__(self, progress_callback=None, status_callback=None):
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.download_dir = "downloads"
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                percent = float(p)
                if self.progress_callback:
                    self.progress_callback(percent / 100)
            except ValueError:
                pass
            
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            if self.status_callback:
                self.status_callback(f"Downloading... {p}% | Speed: {speed} | ETA: {eta}")
        
        elif d['status'] == 'finished':
            if self.status_callback:
                self.status_callback("Download complete! Processing...")

    def _parse_time(self, t_str):
        if not t_str or str(t_str).strip() == "*":
            return "*"
        try:
            parts = str(t_str).split(':')
            if len(parts) == 3: # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2: # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1: # SS
                return int(parts[0])
        except:
            pass
        return t_str

    def get_video_info(self, url, browser_name=None):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
        }
        if browser_name:
            ydl_opts['cookiesfrombrowser'] = (browser_name,)
            print(f"DEBUG: Fetching info using cookies from {browser_name}")
        elif os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                formats = []
                for f in info.get('formats', []):
                    # Filter for video+audio or just video formats that are useful
                    if f.get('vcodec') != 'none':
                        # Ensure res is a string to avoid sorting errors
                        res = f.get('resolution') or f'{f.get("width")}x{f.get("height")}'
                        res = str(res) 
                        ext = f.get('ext')
                        note = f.get('format_note') or ''
                        formats.append({
                            'id': f.get('format_id'),
                            'res': res,
                            'ext': ext,
                            'note': note,
                            'filesize': f.get('filesize') or f.get('filesize_approx')
                        })
                
                # Sort unique resolutions descending
                def sort_key(r):
                    # Handle "1080x1920" or "1080p" or "1080"
                    match = str(r).split('x')
                    if len(match) == 2:
                        return int(match[1]) if match[1].isdigit() else 0
                    nums = "".join([c for c in str(r) if c.isdigit()])
                    return int(nums) if nums else 0

                res_list = [f['res'] for f in formats if 'x' in str(f['res']) or str(f['res']).isdigit()]
                unique_res = sorted(list(set(res_list)), key=sort_key, reverse=True)
                
                res_options = ["Highest Quality"] + unique_res[:10]
                
                return {
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'duration': info.get('duration'),
                    'formats': formats,
                    'resolutions': res_options
                }
            except Exception as e:
                print(f"DEBUG: Error in get_video_info: {e}")
                return {'error': str(e)}

    def download(self, url, resolution="Highest Quality", start_time=None, end_time=None, browser_name=None):
        outtmpl = os.path.join(self.download_dir, '%(title).100s.%(ext)s')
        if start_time or end_time:
            # Add timestamps to filename to avoid "already downloaded" skip
            # and to allow multiple crops of the same video
            s_tag = str(start_time).replace(':', '-') if start_time else "start"
            e_tag = str(end_time).replace(':', '-') if end_time else "end"
            outtmpl = os.path.join(self.download_dir, f'%(title).100s_{s_tag}_{e_tag}.%(ext)s')

        # Format logic:
        # If Highest Quality: use absolute best
        # If specific res (e.g. 1080p): limit height
        if resolution == "Highest Quality":
            format_str = 'bestvideo+bestaudio/best'
        else:
            height = "".join([c for c in str(resolution) if c.isdigit()])
            if 'x' in str(resolution):
                height = str(resolution).split('x')[1]
            format_str = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'

        ydl_opts = {
            'format': format_str,
            'outtmpl': outtmpl,
            'progress_hooks': [self._progress_hook],
            'merge_output_format': 'mp4',
            'ffmpeg_location': r'C:\ProgramData\chocolatey\bin\ffmpeg.exe' if os.name == 'nt' else 'ffmpeg',
            'quiet': False,
            'no_warnings': False,
            'restrictedfilenames': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'n_sig_check': False, # Avoid some signature check issues
        }

        # Handle Cookies for bot detection bypass
        if browser_name:
            ydl_opts['cookiesfrombrowser'] = (browser_name,)
            print(f"DEBUG: Using cookies from {browser_name}")
        elif os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
            print("DEBUG: Using cookies.txt for authentication")

        if start_time or end_time:
            from yt_dlp.utils import download_range_func
            s = self._parse_time(start_time)
            e = self._parse_time(end_time)
            
            print(f"DEBUG: Trimming from {s} to {e}")
            
            # download_ranges is the correct API parameter for Python
            ydl_opts['download_ranges'] = download_range_func(None, [(s, e)])
            ydl_opts['force_keyframes_at_cuts'] = True

        print(f"DEBUG: ydl_opts being used: {ydl_opts}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info_dict = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info_dict)
                return os.path.basename(downloaded_file)
            except Exception as e:
                import traceback
                print(f"DEBUG: Download error: {e}")
                print(traceback.format_exc())
                if self.status_callback:
                    self.status_callback(f"Error: {str(e)}")
                return False
