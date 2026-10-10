from flask import Flask, request, send_file, render_template, jsonify
import yt_dlp
import os
import uuid
import subprocess
import threading
from flask import after_this_request

app = Flask(__name__)

# Path where videos will be temporarily stored
DOWNLOAD_FOLDER = 'downloads'

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def update_ytdlp():
    """
    Attempts to update yt-dlp using pip.
    Since we are using a venv, we need to call the pip inside that venv.
    """
    try:
        # In a typical venv setup, we can use the current python executable to run pip
        import sys
        python_exe = sys.executable
        subprocess.check_call([python_exe, '-m', 'pip', 'install', '-U', 'yt-dlp'])
        app.logger.info("yt-dlp updated successfully.")
    except Exception as e:
        app.logger.error(f"Failed to update yt-dlp: {e}")

def check_and_update_ytdlp():
    """
    Checks for yt-dlp updates and triggers update if needed.
    Run in a separate thread to avoid blocking server startup.
    """
    try:
        # yt-dlp has a built-in update command
        # We check if an update is available.
        # Note: updating in a venv requires pip, as we did in update_ytdlp.
        update_ytdlp()
    except Exception as e:
        app.logger.error(f"Error during yt-dlp update check: {e}")

# Start update check in background on startup
threading.Thread(target=check_and_update_ytdlp, daemon=True).start()

def download_video(url, format_type):
    # Generate a unique filename to avoid collisions
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_FOLDER, f"{file_id}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    if format_type == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # Best video + best audio merged into mp4
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        # If it was mp3, the filename extension changes after post-processing
        if format_type == 'mp3':
            filename = os.path.splitext(filename)[0] + '.mp3'

        return filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    try:
        # Usando process_video_info para pegar apenas o necessário rapidamente
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'Título não disponível'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader') or info.get('channel'),
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json()
    url = data.get('url')
    format_type = data.get('format', 'mp4')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        file_path = download_video(url, format_type)

        @after_this_request
        def remove_file(response):
            try:
                # This is a simple cleanup. In a production app,
                # you'd use a background task or cron job.
                # However, we can't easily delete the file *immediately* after send_file
                # without a custom response wrapper or delay.
                pass
            except Exception as e:
                app.logger.error(f"Error cleaning up file: {e}")
            return response

        return send_file(file_path, as_attachment=True)
    except Exception as e:
        app.logger.error(f"Download error: {str(e)}")
        return jsonify({'error': f'Failed to download video: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=6713)
