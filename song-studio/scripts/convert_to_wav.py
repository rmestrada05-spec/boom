#!/usr/bin/env python3
"""
Convert any audio (or video) file to 48 kHz 16-bit WAV.
Usage: convert_to_wav.py <input_path> <output_wav_path>
"""

import sys


def main():
    if len(sys.argv) < 3:
        print("Usage: convert_to_wav.py <input_path> <output_wav_path>", file=sys.stderr)
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2]
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(inp)
        clip.write_audiofile(out, fps=48000, nbytes=2, verbose=False, logger=None)
        clip.close()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
