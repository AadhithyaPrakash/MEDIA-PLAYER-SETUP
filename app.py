from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import os
import subprocess
import requests
import time
import threading
import base64
import json
import mimetypes
from urllib.parse import quote

app = Flask(__name__)
CORS(app)

# Configuration
MEDIA_FOLDER = r'D:\movies'  # Update to your media folder
VLC_PATH = r'C:\Program Files\VideoLAN\VLC\vlc.exe'  # Update to your VLC path
VLC_HTTP_PORT = 8080
VLC_PASSWORD = 'vlcpass'  # Change this password
VLC_STREAM_PORT = 8081

class VLCController:
    def __init__(self):
        self.vlc_process = None
        self.current_media = None
        self.is_playing = False
        self.vlc_auth = base64.b64encode(f':{VLC_PASSWORD}'.encode()).decode()
        
    def start_vlc_http_interface(self):
        """Start VLC with HTTP interface"""
        if self.vlc_process and self.vlc_process.poll() is None:
            return True
            
        try:
            cmd = [
                VLC_PATH,
                '--intf', 'http',
                '--http-host', '127.0.0.1',
                '--http-port', str(VLC_HTTP_PORT),
                '--http-password', VLC_PASSWORD,
                '--no-video-title-show',
                '--quiet'
            ]
            
            self.vlc_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for VLC to start
            time.sleep(3)
            return self.is_vlc_running()
            
        except Exception as e:
            print(f"Error starting VLC: {e}")
            return False
    
    def is_vlc_running(self):
        """Check if VLC HTTP interface is responding"""
        try:
            headers = {'Authorization': f'Basic {self.vlc_auth}'}
            response = requests.get(
                f'http://127.0.0.1:{VLC_HTTP_PORT}/requests/status.json',
                headers=headers,
                timeout=2
            )
            return response.status_code == 200
        except:
            return False
    
    def vlc_request(self, endpoint, params=None):
        """Make HTTP request to VLC"""
        try:
            headers = {'Authorization': f'Basic {self.vlc_auth}'}
            url = f'http://127.0.0.1:{VLC_HTTP_PORT}/requests/{endpoint}'
            
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                if endpoint.endswith('.json'):
                    return response.json()
                return response.text
            return None
        except Exception as e:
            print(f"VLC request error: {e}")
            return None
    
    def play_media(self, file_path):
        """Play media file through VLC"""
        if not self.is_vlc_running():
            if not self.start_vlc_http_interface():
                return False
        
        # Clear playlist and add new media
        self.vlc_request('status.json', {'command': 'pl_empty'})
        
        # Add media to playlist
        params = {
            'command': 'in_play',
            'input': file_path
        }
        
        result = self.vlc_request('status.json', params)
        if result:
            self.current_media = file_path
            self.is_playing = True
            return True
        return False
    
    def get_status(self):
        """Get current VLC status"""
        if not self.is_vlc_running():
            return {'state': 'stopped', 'position': 0, 'length': 0, 'volume': 100}
        
        status = self.vlc_request('status.json')
        if status:
            return {
                'state': status.get('state', 'stopped'),
                'position': status.get('position', 0),
                'length': status.get('length', 0),
                'volume': status.get('volume', 100),
                'current_media': self.current_media
            }
        return {'state': 'stopped', 'position': 0, 'length': 0, 'volume': 100}
    
    def play_pause(self):
        """Toggle play/pause"""
        return self.vlc_request('status.json', {'command': 'pl_pause'})
    
    def stop(self):
        """Stop playback"""
        result = self.vlc_request('status.json', {'command': 'pl_stop'})
        if result:
            self.is_playing = False
        return result
    
    def set_volume(self, volume):
        """Set volume (0-512)"""
        return self.vlc_request('status.json', {'command': 'volume', 'val': volume})
    
    def seek(self, position):
        """Seek to position (percentage)"""
        return self.vlc_request('status.json', {'command': 'seek', 'val': f'{position}%'})
    
    def cleanup(self):
        """Clean up VLC process"""
        if self.vlc_process and self.vlc_process.poll() is None:
            try:
                self.vlc_process.terminate()
                self.vlc_process.wait(timeout=5)
            except:
                self.vlc_process.kill()

# Global VLC controller instance
vlc_controller = VLCController()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/media')
def get_media():
    """Get list of all media files"""
    media_list = []
    
    if not os.path.exists(MEDIA_FOLDER):
        return jsonify({'error': 'Media folder not found'}), 404
    
    try:
        for filename in os.listdir(MEDIA_FOLDER):
            file_path = os.path.join(MEDIA_FOLDER, filename)
            
            if os.path.isdir(file_path) or filename.startswith('.'):
                continue
                
            # Support more formats since VLC can handle them
            audio_exts = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma')
            video_exts = ('.mp4', '.avi', '.mkv', '.mov', '.wmv', '.webm', '.flv', '.m4v', '.3gp')
            
            if filename.lower().endswith(audio_exts):
                media_type = 'audio'
            elif filename.lower().endswith(video_exts):
                media_type = 'video'
            else:
                continue
                
            try:
                file_size = os.path.getsize(file_path)
                file_size_mb = round(file_size / (1024 * 1024), 2)
            except:
                file_size_mb = 0
                
            media_list.append({
                'name': filename,
                'type': media_type,
                'path': file_path,
                'size': f'{file_size_mb} MB'
            })
    except Exception as e:
        return jsonify({'error': f'Error reading media folder: {str(e)}'}), 500
    
    return jsonify(media_list)

@app.route('/api/play', methods=['POST'])
def play_media():
    """Play selected media file"""
    data = request.get_json()
    file_path = data.get('path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    success = vlc_controller.play_media(file_path)
    if success:
        return jsonify({'status': 'playing', 'file': os.path.basename(file_path)})
    else:
        return jsonify({'error': 'Failed to play media'}), 500

@app.route('/api/control/<action>', methods=['POST'])
def control_playback(action):
    """Control VLC playback"""
    if action == 'play_pause':
        vlc_controller.play_pause()
    elif action == 'stop':
        vlc_controller.stop()
    elif action == 'volume':
        data = request.get_json()
        volume = data.get('volume', 100)
        vlc_controller.set_volume(volume)
    elif action == 'seek':
        data = request.get_json()
        position = data.get('position', 0)
        vlc_controller.seek(position)
    
    return jsonify({'status': 'ok'})

@app.route('/api/status')
def get_status():
    """Get current playback status"""
    return jsonify(vlc_controller.get_status())

@app.route('/api/vlc/start', methods=['POST'])
def start_vlc():
    """Manually start VLC HTTP interface"""
    success = vlc_controller.start_vlc_http_interface()
    return jsonify({'success': success, 'running': vlc_controller.is_vlc_running()})

def cleanup_vlc():
    """Cleanup function for VLC"""
    vlc_controller.cleanup()

# Register cleanup function
import atexit
atexit.register(cleanup_vlc)

if __name__ == '__main__':
    print(f"Media folder: {MEDIA_FOLDER}")
    print(f"VLC path: {VLC_PATH}")
    print(f"VLC HTTP interface will run on: http://127.0.0.1:{VLC_HTTP_PORT}")
    print(f"VLC HTTP password: {VLC_PASSWORD}")
    
    # Check if VLC exists
    if not os.path.exists(VLC_PATH):
        print("⚠️  WARNING: VLC not found at specified path!")
        print("   Please update VLC_PATH in the code")
    
    # Check media folder
    if os.path.exists(MEDIA_FOLDER):
        files = [f for f in os.listdir(MEDIA_FOLDER) if not f.startswith('.')]
        print(f"Media files found: {len(files)}")
    else:
        print("⚠️  WARNING: Media folder not found!")
    
    print("\n🚀 Starting server at http://127.0.0.1:5000")
    print("📺 VLC will handle all media playback and transcoding")
    
    try:
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        cleanup_vlc()