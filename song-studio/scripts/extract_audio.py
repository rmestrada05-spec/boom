#!/usr/bin/env python3
"""
Step 4: Extract pure audio from video to 48 kHz, 16-bit PCM WAV.
Usage: extract_audio.py <video_path> <wav_path>
"""

import sys

AUDIO_FPS = 48000
NBYTES = 2  # 16-bit


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_audio.py <video_path> <wav_path>")
        sys.exit(1)
    video_path = sys.argv[1]
    wav_path = sys.argv[2]
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(video_path)
        if clip.audio is None:
            clip.close()
            print("No audio track", file=sys.stderr)
            sys.exit(1)
        clip.audio.write_audiofile(
            wav_path,
            fps=AUDIO_FPS,
            nbytes=NBYTES,
            verbose=False,
            logger=None,
        )
        clip.close()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
