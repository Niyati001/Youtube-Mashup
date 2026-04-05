import sys
import os
import re
import yt_dlp
from moviepy.editor import AudioFileClip, concatenate_audioclips


def validate_inputs(singer_name, num_videos, audio_duration, output_filename):
    """Validate command line inputs."""
    errors = []

    if not singer_name.strip():
        errors.append("Singer name cannot be empty.")

    try:
        n = int(num_videos)
        if n <= 10:
            errors.append("Number of videos must be greater than 10.")
    except ValueError:
        errors.append("Number of videos must be a valid integer.")

    try:
        y = int(audio_duration)
        if y <= 20:
            errors.append("Audio duration must be greater than 20 seconds.")
    except ValueError:
        errors.append("Audio duration must be a valid integer.")

    if not output_filename.endswith(".mp3"):
        errors.append("Output filename must end with .mp3")

    return errors


def download_videos(singer_name, num_videos, download_dir):
    """Download predefined YouTube videos."""

    print(f"\n[1/4] Downloading videos for '{singer_name}'...")

    video_urls = [
        "https://youtu.be/Kd57YHWqrsI",
        "https://youtu.be/LIG3Yl5pZ1Y",
        "https://youtu.be/tYME9OPEgko",
        "https://youtu.be/lKB2AoDopM4",
        "https://youtu.be/tR6XkXy-gjY",
        "https://youtu.be/THEwbUfdDBg",
        "https://youtu.be/bJ-170c5z-E",
        "https://youtu.be/oi5C_MNYgnU",
        "https://youtu.be/zXjmAbFyf0M",
        "https://youtu.be/SrrPetM9GI0",
        "https://youtu.be/B0f4xyZSfvU"
    ]

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": os.path.join(download_dir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "cookiefile": "cookies.txt",
        "ignoreerrors": True,
    }

    downloaded_files = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            for url in video_urls[:num_videos]:
                try:
                    info = ydl.extract_info(url, download=True)

                    if info:
                        video_id = info.get("id")

                        for f in os.listdir(download_dir):
                            if f.startswith(video_id):
                                downloaded_files.append(
                                    os.path.join(download_dir, f)
                                )
                                break

                except Exception as e:
                    print(f"Skipping {url}: {e}")

    except Exception as e:
        print(f"Error during download: {e}")
        raise

    print(f"Downloaded {len(downloaded_files)} video(s).")
    return downloaded_files


def convert_to_audio(video_files, audio_dir):
    """Convert video files to MP3 audio."""
    print(f"\n[2/4] Converting {len(video_files)} video(s) to audio...")
    audio_files = []

    for i, video_path in enumerate(video_files):
        try:
            base = os.path.splitext(os.path.basename(video_path))[0]
            audio_path = os.path.join(audio_dir, f"{base}.mp3")
            clip = AudioFileClip(video_path)
            clip.write_audiofile(audio_path, logger=None)
            clip.close()
            audio_files.append(audio_path)
            print(f"    Converted [{i+1}/{len(video_files)}]: {base}.mp3")
        except Exception as e:
            print(f"    Warning: Could not convert {video_path}: {e}")

    print(f"    Converted {len(audio_files)} audio file(s).")
    return audio_files


def cut_audios(audio_files, duration_sec, cut_dir):
    """Cut the first Y seconds from each audio file."""
    print(f"\n[3/4] Cutting first {duration_sec} seconds from each audio...")
    cut_files = []

    for i, audio_path in enumerate(audio_files):
        try:
            base = os.path.basename(audio_path)
            cut_path = os.path.join(cut_dir, f"cut_{base}")
            clip = AudioFileClip(audio_path)
            end = min(duration_sec, clip.duration)
            cut_clip = clip.subclip(0, end)
            cut_clip.write_audiofile(cut_path, logger=None)
            cut_clip.close()
            clip.close()
            cut_files.append(cut_path)
            print(f"    Cut [{i+1}/{len(audio_files)}]: {base}")
        except Exception as e:
            print(f"    Warning: Could not cut {audio_path}: {e}")

    print(f"    Cut {len(cut_files)} audio file(s).")
    return cut_files


def merge_audios(cut_files, output_path):
    """Merge all cut audio clips into one output file."""
    print(f"\n[4/4] Merging {len(cut_files)} clips into '{output_path}'...")

    clips = []
    try:
        for f in cut_files:
            clips.append(AudioFileClip(f))
        final = concatenate_audioclips(clips)
        final.write_audiofile(output_path, logger=None)
        final.close()
        for c in clips:
            c.close()
        print(f"    Mashup saved: {output_path}")
    except Exception as e:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        raise RuntimeError(f"Error merging audio: {e}")


def main():
    # Check argument count
    if len(sys.argv) != 5:
        print("Usage: python mashup.py <SingerName> <NumberOfVideos> <AudioDuration> <OutputFileName>")
        print("Example: python mashup.py \"Sharry Maan\" 20 20 output.mp3")
        sys.exit(1)

    singer_name = sys.argv[1]
    num_videos_str = sys.argv[2]
    audio_duration_str = sys.argv[3]
    output_filename = sys.argv[4]

    # Validate inputs
    errors = validate_inputs(singer_name, num_videos_str, audio_duration_str, output_filename)
    if errors:
        print("Input Error(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    num_videos = int(num_videos_str)
    audio_duration = int(audio_duration_str)

    # Create temp directories
    base_dir = "mashup_temp"
    video_dir = os.path.join(base_dir, "videos")
    audio_dir = os.path.join(base_dir, "audios")
    cut_dir = os.path.join(base_dir, "cuts")

    for d in [video_dir, audio_dir, cut_dir]:
        os.makedirs(d, exist_ok=True)

    try:
        video_files = download_videos(singer_name, num_videos, video_dir)

        if not video_files:
            print("No videos downloaded. Exiting.")
            sys.exit(1)

        audio_files = convert_to_audio(video_files, audio_dir)

        if not audio_files:
            print("No audio files created. Exiting.")
            sys.exit(1)

        cut_files = cut_audios(audio_files, audio_duration, cut_dir)

        if not cut_files:
            print("No audio clips cut. Exiting.")
            sys.exit(1)

        merge_audios(cut_files, output_filename)

        print(f"\n✅ Mashup complete! Output saved to: {output_filename}")

    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        # Optional: clean up temp files
        import shutil
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
            print("Temporary files cleaned up.")


if __name__ == "__main__":
    main()
