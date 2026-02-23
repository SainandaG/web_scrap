import customtkinter as ctk
import threading
import requests
from PIL import Image, ImageTk
from io import BytesIO
import os
from downloader import YouTubeDownloader

# Set appearance mode and color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("High Speed YouTube Downloader")
        self.geometry("800x650")
        
        self.downloader = YouTubeDownloader(
            progress_callback=self.update_progress,
            status_callback=self.update_status
        )

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Title Label
        self.title_label = ctk.CTkLabel(self, text="YouTube Downloader", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # URL Entry Frame
        self.url_frame = ctk.CTkFrame(self)
        self.url_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Paste YouTube URL here...")
        self.url_entry.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")

        self.fetch_button = ctk.CTkButton(self.url_frame, text="Fetch Info", command=self.start_fetch_thread)
        self.fetch_button.grid(row=0, column=1, padx=(5, 10), pady=10)

        # Preview Frame (16:9 Ratio Area)
        # 640 x 360 is a classic 16:9 resolution
        self.preview_frame = ctk.CTkFrame(self, width=640, height=360, fg_color="#1a1a1a")
        self.preview_frame.grid(row=2, column=0, padx=20, pady=10)
        self.preview_frame.grid_propagate(False) # Keep size fixed for 16:9
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_rowconfigure(0, weight=1)

        self.thumbnail_label = ctk.CTkLabel(self.preview_frame, text="Video Preview", text_color="gray")
        self.thumbnail_label.grid(row=0, column=0)

        # Video Info Labels
        self.info_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14))
        self.info_label.grid(row=3, column=0, padx=20, pady=5)

        # Control Frame (Quality & Download)
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure(1, weight=1)

        self.quality_label = ctk.CTkLabel(self.control_frame, text="Quality:")
        self.quality_label.grid(row=0, column=0, padx=10, pady=10)

        self.quality_dropdown = ctk.CTkOptionMenu(self.control_frame, values=["Best"])
        self.quality_dropdown.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.download_button = ctk.CTkButton(self.control_frame, text="Download Video", command=self.start_download_thread, state="disabled")
        self.download_button.grid(row=0, column=2, padx=10, pady=10)

        # Crop Options Frame
        self.crop_frame = ctk.CTkFrame(self)
        self.crop_frame.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        self.crop_frame.grid_columnconfigure((1, 3), weight=1)

        self.crop_switch = ctk.CTkSwitch(self.crop_frame, text="Crop Video", command=self.toggle_crop)
        self.crop_switch.grid(row=0, column=0, padx=10, pady=10)

        self.start_label = ctk.CTkLabel(self.crop_frame, text="Start:")
        self.start_label.grid(row=0, column=1, padx=(10, 2), pady=10, sticky="e")
        self.start_entry = ctk.CTkEntry(self.crop_frame, placeholder_text="00:00:00", width=100, state="disabled")
        self.start_entry.grid(row=0, column=2, padx=(2, 10), pady=10, sticky="w")

        self.end_label = ctk.CTkLabel(self.crop_frame, text="End:")
        self.end_label.grid(row=0, column=3, padx=(10, 2), pady=10, sticky="e")
        self.end_entry = ctk.CTkEntry(self.crop_frame, placeholder_text="00:00:10", width=100, state="disabled")
        self.end_entry.grid(row=0, column=4, padx=(2, 10), pady=10, sticky="w")

        # Authentication & Status Frame
        self.auth_status_frame = ctk.CTkFrame(self)
        self.auth_status_frame.grid(row=6, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.auth_status_frame.grid_columnconfigure(1, weight=1)

        # Authentication Section
        self.auth_label = ctk.CTkLabel(self.auth_status_frame, text="Auth (Bypass Bot):")
        self.auth_label.grid(row=0, column=0, padx=10, pady=10)

        self.browser_var = ctk.StringVar(value="None")
        self.browser_dropdown = ctk.CTkOptionMenu(
            self.auth_status_frame, 
            values=["None", "chrome", "firefox", "edge", "brave", "opera", "safari"],
            variable=self.browser_var,
            width=120
        )
        self.browser_dropdown.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.auth_status_frame)
        self.progress_bar.grid(row=1, column=0, columnspan=3, padx=20, pady=(10, 5), sticky="ew")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.auth_status_frame, text="Ready", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=2, column=0, columnspan=3, padx=20, pady=5)

        self.current_video_info = None

    def update_progress(self, progress):
        self.progress_bar.set(progress)

    def update_status(self, text):
        self.status_label.configure(text=text)

    def toggle_crop(self):
        state = "normal" if self.crop_switch.get() else "disabled"
        self.start_entry.configure(state=state)
        self.end_entry.configure(state=state)

    def start_fetch_thread(self):
        url = self.url_entry.get()
        if not url:
            self.update_status("Please enter a URL first!")
            return
        
        self.fetch_button.configure(state="disabled")
        self.update_status("Fetching video information...")
        
        browser = self.browser_var.get()
        browser_name = None if browser == "None" else browser
        
        threading.Thread(target=self.fetch_info, args=(url, browser_name), daemon=True).start()

    def fetch_info(self, url, browser_name=None):
        info = self.downloader.get_video_info(url, browser_name=browser_name)
        if "error" in info:
            err_msg = info['error']
            if "not a bot" in err_msg.lower() or "sign in" in err_msg.lower():
                self.after(0, lambda: self.update_status("Bot Detected! Select your browser in 'Auth' dropdown below."))
            else:
                self.after(0, lambda: self.update_status(f"Error: {err_msg[:50]}..."))
            self.after(0, lambda: self.fetch_button.configure(state="normal"))
            return

        self.current_video_info = info
        self.after(0, self.display_info)

    def display_info(self):
        info = self.current_video_info
        self.info_label.configure(text=info['title'][:80] + "..." if len(info['title']) > 80 else info['title'])
        
        # Load Thumbnail
        try:
            response = requests.get(info['thumbnail'])
            img_data = response.content
            img = Image.open(BytesIO(img_data))
            
            # Crop/Resize to 16:9 for the 640x360 frame
            target_w, target_h = 640, 360
            img_w, img_h = img.size
            img_aspect = img_w / img_h
            target_aspect = target_w / target_h
            
            if img_aspect > target_aspect:
                # Image is wider - crop sides
                new_w = int(img_h * target_aspect)
                left = (img_w - new_w) / 2
                img = img.crop((left, 0, left + new_w, img_h))
            elif img_aspect < target_aspect:
                # Image is taller - crop top/bottom
                new_h = int(img_w / target_aspect)
                top = (img_h - new_h) / 2
                img = img.crop((0, top, img_w, top + new_h))
            
            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_w, target_h))
            self.thumbnail_label.configure(image=ctk_img, text="")
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
            self.thumbnail_label.configure(text="Failed to load preview")

        # Update Resolutions
        res_values = [str(r) for r in info['resolutions']]
        if not res_values:
            res_values = ["Best"]
        self.quality_dropdown.configure(values=res_values)
        self.quality_dropdown.set(res_values[0])
        
        self.download_button.configure(state="normal")
        self.fetch_button.configure(state="normal")
        self.update_status("Information retrieved.")

    def start_download_thread(self):
        url = self.url_entry.get()
        resolution = self.quality_dropdown.get()
        
        start_time = None
        end_time = None
        
        if self.crop_switch.get():
            start_time = self.start_entry.get().strip() or None
            end_time = self.end_entry.get().strip() or None

        self.download_button.configure(state="disabled")
        self.fetch_button.configure(state="disabled")
        self.progress_bar.set(0)
        
        browser = self.browser_var.get()
        browser_name = None if browser == "None" else browser
        
        threading.Thread(target=self.run_download, args=(url, resolution, start_time, end_time, browser_name), daemon=True).start()

    def run_download(self, url, resolution, start_time, end_time, browser_name=None):
        success = self.downloader.download(url, resolution, start_time, end_time, browser_name=browser_name)
        self.after(0, lambda: self.download_button.configure(state="normal"))
        self.after(0, lambda: self.fetch_button.configure(state="normal"))
        
        if success is not False:
            self.after(0, lambda: self.update_status("Download Finished! Saved in 'downloads' folder."))
        else:
            # Note: status_label is already updated by status_callback in downloader.download
            # but we can improve the message if it's a bot error
            current_status = self.status_label.cget("text")
            if "not a bot" in current_status.lower() or "sign in" in current_status.lower():
                self.after(0, lambda: self.update_status("Bot Detected! Please select your browser in the Auth dropdown."))
            else:
                self.after(0, lambda: self.update_status("Download failed. See logs or select browser."))

if __name__ == "__main__":
    app = App()
    app.mainloop()
