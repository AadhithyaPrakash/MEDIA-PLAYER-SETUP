from flask import Flask, jsonify, render_template, send_from_directory
import os

app = Flask(__name__)

MEDIA_FOLDER = 'D:\movies'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/media')
def get_media():
    media_list = []
    for filename in os.listdir(MEDIA_FOLDER):
        if filename.endswith(('.mp3', '.mp4')):
            media_type = 'audio' if filename.endswith('.mp3') else 'video'
            media_list.append({
                'name': filename,
                'type': media_type,
                'url': f'/media_files/{filename}'
            })
    return jsonify(media_list)

@app.route('/media_files/<path:filename>')
def media_files(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
