import os
import re
import shutil
import smtplib
import threading
import zipfile
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

import yt_dlp
from flask import Flask, render_template_string, request, jsonify
from moviepy.editor import AudioFileClip, concatenate_audioclips

app = Flask(__name__)

# -------------------------------------------------------------------
# Email configuration – set these via environment variables
# -------------------------------------------------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")      # your Gmail address
SMTP_PASS = os.environ.get("SMTP_PASS", "")      # your Gmail App Password

# -------------------------------------------------------------------
# HTML Template
# -------------------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>🎵 Mashup Generator</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .card {
      background: rgba(255,255,255,0.05);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 20px;
      padding: 40px;
      width: 100%;
      max-width: 480px;
      box-shadow: 0 25px 50px rgba(0,0,0,0.4);
    }
    h1 {
      color: #e94560;
      font-size: 2rem;
      margin-bottom: 6px;
      text-align: center;
    }
    .subtitle {
      color: rgba(255,255,255,0.5);
      text-align: center;
      font-size: 0.9rem;
      margin-bottom: 30px;
    }
    label {
      display: block;
      color: rgba(255,255,255,0.8);
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 6px;
      margin-top: 18px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    input {
      width: 100%;
      padding: 12px 16px;
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 10px;
      color: #fff;
      font-size: 1rem;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus { border-color: #e94560; }
    input::placeholder { color: rgba(255,255,255,0.3); }
    .hint {
      color: rgba(255,255,255,0.35);
      font-size: 0.75rem;
      margin-top: 4px;
    }
    button {
      margin-top: 28px;
      width: 100%;
      padding: 14px;
      background: linear-gradient(90deg, #e94560, #c62a47);
      border: none;
      border-radius: 10px;
      color: #fff;
      font-size: 1.05rem;
      font-weight: 700;
      cursor: pointer;
      letter-spacing: 0.04em;
      transition: opacity 0.2s, transform 0.1s;
    }
    button:hover { opacity: 0.9; transform: translateY(-1px); }
    button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
    #status {
      margin-top: 20px;
      padding: 14px 18px;
      border-radius: 10px;
      display: none;
      font-size: 0.95rem;
    }
    .status-info { background: rgba(99,179,237,0.15); color: #90cdf4; border: 1px solid rgba(99,179,237,0.3); }
    .status-success { background: rgba(72,187,120,0.15); color: #9ae6b4; border: 1px solid rgba(72,187,120,0.3); }
    .status-error { background: rgba(245,101,101,0.15); color: #feb2b2; border: 1px solid rgba(245,101,101,0.3); }
    .spinner {
      display: inline-block;
      width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      vertical-align: middle;
      margin-right: 8px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div class="card">
    <h1>🎵 Mashup Generator</h1>
    <p class="subtitle">YouTube → Audio Mashup → Your Inbox</p>

    <label>Singer Name</label>
    <input type="text" id="singer" placeholder="e.g. Sharry Maan" />

    <label># of Videos</label>
    <input type="number" id="num_videos" placeholder="e.g. 11" min="11" />
    <div class="hint">Must be greater than 10</div>

    <label>Duration per clip (seconds)</label>
    <input type="number" id="duration" placeholder="e.g. 25" min="21" />
    <div class="hint">Must be greater than 20</div>

    <label>Your Email</label>
    <input type="email" id="email" placeholder="you@example.com" />

    <button id="submitBtn" onclick="submitForm()">Generate & Send Mashup</button>
    <div id="status"></div>
  </div>

  <script>
    function setStatus(msg, type) {
      const el = document.getElementById('status');
      el.style.display = 'block';
      el.className = 'status-' + type;
      el.innerHTML = msg;
    }

    function validateEmail(email) {
      return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email);
    }

    async function submitForm() {
      const singer = document.getElementById('singer').value.trim();
      const num_videos = parseInt(document.getElementById('num_videos').value);
      const duration = parseInt(document.getElementById('duration').value);
      const email = document.getElementById('email').value.trim();

      if (!singer) return setStatus('❗ Singer name is required.', 'error');
      if (isNaN(num_videos) || num_videos <= 10) return setStatus('❗ Number of videos must be greater than 10.', 'error');
      if (isNaN(duration) || duration <= 20) return setStatus('❗ Duration must be greater than 20 seconds.', 'error');
      if (!validateEmail(email)) return setStatus('❗ Please enter a valid email address.', 'error');

      const btn = document.getElementById('submitBtn');
      btn.disabled = true;
      setStatus('<span class="spinner"></span>Processing your mashup... this may take a few minutes.', 'info');

      try {
        const resp = await fetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ singer, num_videos, duration, email })
        });
        const data = await resp.json();
        if (data.success) {
          setStatus('✅ ' + data.message, 'success');
        } else {
          setStatus('❌ ' + data.message, 'error');
        }
      } catch (e) {
        setStatus('❌ Network error. Please try again.', 'error');
      } finally {
        btn.disabled = false;
      }
    }
  </script>
</body>
</html>
"""

# -------------------------------------------------------------------
# Core mashup logic
# -------------------------------------------------------------------
def download_videos(singer_name, num_videos, download_dir):
    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": os.path.join(download_dir, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    search_query = f"ytsearch{num_videos}:{singer_name} songs"
    downloaded = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=True)
        if "entries" in info:
            for entry in info["entries"]:
                if entry:
                    vid_id = entry.get("id")
                    for f in os.listdir(download_dir):
                        if f.startswith(vid_id):
                            downloaded.append(os.path.join(download_dir, f))
                            break
    return downloaded


def convert_and_cut(video_files, duration_sec, audio_dir):
    clips = []
    for video_path in video_files:
        try:
            base = os.path.splitext(os.path.basename(video_path))[0]
            audio_path = os.path.join(audio_dir, f"{base}.mp3")
            clip = AudioFileClip(video_path)
            end = min(duration_sec, clip.duration)
            cut = clip.subclip(0, end)
            cut.write_audiofile(audio_path, logger=None)
            cut.close()
            clip.close()
            clips.append(audio_path)
        except Exception as e:
            print(f"Warning: skipping {video_path}: {e}")
    return clips


def merge_clips(clip_files, output_path):
    clips = [AudioFileClip(f) for f in clip_files]
    final = concatenate_audioclips(clips)
    final.write_audiofile(output_path, logger=None)
    final.close()
    for c in clips:
        c.close()


def send_email(recipient, zip_path, singer_name):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = recipient
    msg["Subject"] = f"🎵 Your Mashup for {singer_name} is Ready!"

    body = f"""Hi there!

Your audio mashup for "{singer_name}" has been generated successfully.

Please find the attached ZIP file containing your mashup MP3.

Enjoy the music! 🎶

-- Mashup Generator
"""
    msg.attach(MIMEText(body, "plain"))

    with open(zip_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(zip_path)}"')
        msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipient, msg.as_string())


def process_mashup(singer_name, num_videos, duration, email):
    job_id = str(uuid.uuid4())[:8]
    base_dir = f"mashup_job_{job_id}"
    video_dir = os.path.join(base_dir, "videos")
    audio_dir = os.path.join(base_dir, "audios")

    for d in [video_dir, audio_dir]:
        os.makedirs(d, exist_ok=True)

    try:
        print(f"[{job_id}] Downloading videos for '{singer_name}'...")
        videos = download_videos(singer_name, num_videos, video_dir)
        if not videos:
            raise RuntimeError("No videos downloaded.")

        print(f"[{job_id}] Converting & cutting {len(videos)} videos...")
        clips = convert_and_cut(videos, duration, audio_dir)
        if not clips:
            raise RuntimeError("No audio clips produced.")

        output_mp3 = os.path.join(base_dir, f"{singer_name.replace(' ', '_')}_mashup.mp3")
        print(f"[{job_id}] Merging clips...")
        merge_clips(clips, output_mp3)

        # Zip the output
        zip_path = os.path.join(base_dir, "mashup.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(output_mp3, os.path.basename(output_mp3))

        print(f"[{job_id}] Sending email to {email}...")
        send_email(email, zip_path, singer_name)
        print(f"[{job_id}] Done!")

    except Exception as e:
        print(f"[{job_id}] Error: {e}")
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()

    singer = data.get("singer", "").strip()
    num_videos = data.get("num_videos")
    duration = data.get("duration")
    email = data.get("email", "").strip()

    # Server-side validation
    if not singer:
        return jsonify(success=False, message="Singer name is required.")
    if not isinstance(num_videos, int) or num_videos <= 10:
        return jsonify(success=False, message="Number of videos must be greater than 10.")
    if not isinstance(duration, int) or duration <= 20:
        return jsonify(success=False, message="Duration must be greater than 20 seconds.")
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        return jsonify(success=False, message="Invalid email address.")
    if not SMTP_USER or not SMTP_PASS:
        return jsonify(success=False, message="Email service not configured on server. Set SMTP_USER and SMTP_PASS env vars.")

    # Run in background thread
    thread = threading.Thread(
        target=process_mashup,
        args=(singer, num_videos, duration, email),
        daemon=True
    )
    thread.start()

    return jsonify(
        success=True,
        message=f"Mashup generation started! You'll receive an email at {email} once it's ready (may take a few minutes)."
    )


if __name__ == "__main__":
    print("=" * 55)
    print("  Mashup Web App")
    print("  Before running, set environment variables:")
    print("    SMTP_USER=your_gmail@gmail.com")
    print("    SMTP_PASS=your_app_password")
    print("  Then visit: http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, host="0.0.0.0", port=5000)
