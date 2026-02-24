#!/usr/bin/env python3
"""
Step 20: Check for required Python packages.
Prints JSON to stdout: {"missing": ["torch", ...]} (package names as pip would know them).
"""
import json
import sys

# pip package name -> import name (some differ, e.g. ffmpeg-python -> ffmpeg)
PACKAGES = [
    ("torch", "torch"),
    ("torchaudio", "torchaudio"),
    ("demucs", "demucs"),
    ("librosa", "librosa"),
    ("moviepy", "moviepy"),
    ("pydub", "pydub"),
    ("ffmpeg-python", "ffmpeg"),
    ("numpy", "numpy"),
    ("soundfile", "soundfile"),
]


def main():
    missing = []
    for pip_name, import_name in PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pip_name)
    print(json.dumps({"missing": missing}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"missing": [p[0] for p in PACKAGES], "error": str(e)}), file=sys.stderr)
        sys.exit(1)
