#!/usr/bin/env python3
"""
Step 6: Export audio as MP3 (320 kbps) or WAV.
Usage: export_audio.py <input_wav_path> <output_path>
Output path extension determines format: .mp3 or .wav.
"""

import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: export_audio.py <input_wav> <output_path>", file=sys.stderr)
        sys.exit(1)
    wav_path = sys.argv[1]
    out_path = sys.argv[2]
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(wav_path)
        if out_path.lower().endswith(".mp3"):
            clip.write_audiofile(out_path, bitrate="320k", verbose=False, logger=None)
        else:
            clip.write_audiofile(out_path, verbose=False, logger=None)
        clip.close()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
