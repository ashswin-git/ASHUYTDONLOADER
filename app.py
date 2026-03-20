from flask import Flask, request, render_template, jsonify, send_file
import os
import tempfile
import requests
import re
from datetime import datetime
import yt_dlp
import instaloader
import shutil
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-vercel-app'

# Global dictionary to track progress (Note: on Vercel at scale, this might require Redis, but works locally or on single-instance)
progress_data = {}

class UniversalDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) width/537.36'
        })
        
    def detect_platform(self, url):
        url = url.lower()
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'instagram.com' in url:
            return 'instagram'
        elif 'tiktok.com' in url:
            return 'tiktok'
        elif 'twitter.com' in url or 'x.com' in url:
            return 'twitter'
        elif 'facebook.com' in url or 'fb.watch' in url:
            return 'facebook'
        elif 'reddit.com' in url:
            return 'reddit'
        return 'unknown'
            
    def fetch_info(self, url):
        platform = self.detect_platform(url)
        
        if platform == 'instagram':
            return {
                'status': 'success',
                'title': 'Instagram Content',
                'platform': platform,
                'formats': [{'format_id': 'default', 'label': 'Default Quality'}]
            }
        
        try:
            ydl_opts = {'noplaylist': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                available_heights = set()
                formats = info.get('formats', [])
                for f in formats:
                    height = f.get('height')
                    vcodec = f.get('vcodec')
                    if height and vcodec and vcodec != 'none':
                        available_heights.add(height)
                        
                available_heights = sorted(list(available_heights), reverse=True)
                
                formats_data = []
                if available_heights:
                    for h in available_heights:
                        # Try to merge video and audio for high quality, fallback to best pre-merged if ffmpeg is missing
                        formats_data.append({
                            'format_id': f'bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]/b[ext=mp4][height<={h}]/b[height<={h}]/best',
                            'label': f'{h}p Video (MP4)'
                        })
                else:
                    formats_data.append({'format_id': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/b[ext=mp4]/best', 'label': 'Best Available Video (MP4)'})
                    
                formats_data.append({'format_id': 'bestaudio[ext=m4a]/bestaudio/best', 'label': 'Audio Only (MP3/M4A)'})

                title_clean = info.get('title', 'Unknown Content')
                return {
                    'status': 'success',
                    'title': title_clean,
                    'platform': platform,
                    'formats': formats_data
                }
        except Exception as e:
            return {'status': 'error', 'message': f'Fetch error: {str(e)}'}
            
    def download_to_path(self, url, path, format_id):
        platform = self.detect_platform(url)
        try:
            if platform == 'instagram':
                loader = instaloader.Instaloader(
                    dirname_pattern=path,
                    filename_pattern='{profile}_{mediaid}',
                    download_videos=True,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=False,
                    compress_json=False
                )
                
                if '/stories/' in url:
                    username = re.search(r'instagram\.com/([^/?]+)', url)
                    if not username: return {'status': 'error', 'message': 'Invalid story URL'}
                    profile = instaloader.Profile.from_username(loader.context, username.group(1))
                    for story in loader.get_stories([profile.userid]):
                        for item in story.get_items():
                            loader.download_storyitem(item, target=path)
                    return {'status': 'success'}
                    
                else:
                    patterns = [r'/p/([^/?]+)', r'/reel/([^/?]+)', r'/tv/([^/?]+)']
                    shortcode = None
                    for pattern in patterns:
                        match = re.search(pattern, url)
                        if match:
                            shortcode = match.group(1)
                            break
                    if not shortcode: return {'status': 'error', 'message': 'Invalid post URL'}
                    
                    post = instaloader.Post.from_shortcode(loader.context, shortcode)
                    loader.download_post(post, target=path)
                    return {'status': 'success'}
            
            else:
                actual_format = format_id if format_id and format_id != 'default' else 'best'
                
                # Setup progress hook
                task_id = request.args.get('task_id') if request else None
                
                def progress_hook(d):
                    if task_id and d['status'] == 'downloading':
                        percent_str = d.get('_percent_str', '0%').strip()
                        # Clean ansi escape codes from yt-dlp output if any
                        percent_clean = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                        progress_data[task_id] = percent_clean
                        
                ydl_opts = {
                    'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
                    'format': actual_format,
                    'ignoreerrors': True,
                    'noplaylist': True,
                    'progress_hooks': [progress_hook]
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)
                    if task_id:
                        progress_data[task_id] = '100%'
                    return {'status': 'success'}
                
        except Exception as e:
            return {'status': 'error', 'message': f'Unexpected error: {str(e)}'}

downloader = UniversalDownloader()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fetch-info', methods=['POST'])
def fetch_info():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        if not url: return jsonify({'status': 'error', 'message': 'URL is required'})
            
        return jsonify(downloader.fetch_info(url))
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Server error: {str(e)}'})

@app.route('/api/progress', methods=['GET'])
def get_progress():
    task_id = request.args.get('task_id')
    if not task_id: return jsonify({'progress': '0%'})
    return jsonify({'progress': progress_data.get(task_id, '0%')})

@app.route('/api/download-direct', methods=['GET'])
def download_direct():
    url = request.args.get('url')
    format_id = request.args.get('format_id', 'default')
    task_id = request.args.get('task_id')
    if not url: return "URL is required", 400
        
    temp_dir = tempfile.mkdtemp()
    
    # Initialize basic progress tracking
    if task_id:
        progress_data[task_id] = 'Starting...'
        
    result = downloader.download_to_path(url, temp_dir, format_id)
    
    if result.get('status') == 'success':
        files = os.listdir(temp_dir)
        if not files: return "Failed to download file", 500
            
        media_files = [f for f in files if f.endswith(('.mp4', '.mkv', '.webm', '.jpg', '.mp3', '.m4a'))]
        filename = media_files[0] if media_files else files[0]
        file_path = os.path.join(temp_dir, filename)
        
        # On Vercel, the /tmp directory is automatically cleared between cold starts.
        # No disruptive threading cleanup needed.
        return send_file(file_path, as_attachment=True)
    
    return f"Failed to download: {result.get('message', 'Unknown error')}", 500

@app.route('/supported-platforms')
def supported_platforms():
    return jsonify({
        'video_platforms': ['YouTube', 'TikTok', 'Twitter', 'Facebook', 'Instagram', 'Reddit'],
        'features': ['Auto-platform detection', 'Quality selection', 'Direct downloads to device', 'Privacy focused']
    })

# For vercel testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)