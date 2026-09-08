"""
Uses ffmpeg to strip the video track and compress audio before sending
it to Deepgram. This matters most for video files, where the video
track accounts for the vast majority of file size — a 60-second video
can easily be 20-50x larger than the audio alone. Stripping it cuts
what gets uploaded to Deepgram from tens of MB down to a few hundred
KB, which directly reduces network transfer time.

Falls back silently to the original file if ffmpeg isn't installed,
so this never breaks the pipeline — it's purely a speed optimization.
"""
import subprocess
import os


def compress_audio_for_transcription(input_path: str) -> str:
    output_path = os.path.splitext(input_path)[0] + "_compressed.ogg"

    command = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn",              # strip video track entirely — we only need audio
        "-ac", "1",         # mono — Deepgram doesn't need stereo for transcription
        "-ar", "16000",     # 16kHz is plenty for speech recognition, cuts size further
        "-c:a", "libopus",
        "-b:a", "24k",      # low bitrate, still clear enough for accurate transcription
        output_path,
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, timeout=60)
        original_mb = os.path.getsize(input_path) / (1024 * 1024)
        compressed_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Compressed audio: {original_mb:.2f} MB -> {compressed_mb:.2f} MB")
        return output_path
    except FileNotFoundError:
        print("ffmpeg not found on PATH — sending original file uncompressed. "
              "Install ffmpeg for faster processing on video/large files.")
        return input_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Audio compression failed ({e}) — falling back to original file.")
        return input_path