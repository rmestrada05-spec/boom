#!/usr/bin/env python3
"""
Step 6: Re-attach audio to original video, export as MP4 (H.264 + AAC).
Usage: export_video.py <video_path> <audio_wav_path> <output_mp4_path>
"""

import sys


def main():
    if len(sys.argv) < 4:
        print("Usage: export_video.py <video_path> <audio_wav_path> <output_mp4_path>", file=sys.stderr)
        sys.exit(1)
    video_path = sys.argv[1]
    audio_path = sys.argv[2]
    out_path = sys.argv[3]
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        video = VideoFileClip(video_path)
        audio = AudioFileClip(audio_path)
        video = video.set_audio(audio)
        video.write_videofile(
            out_path,
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None,
        )
        video.close()
        audio.close()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
