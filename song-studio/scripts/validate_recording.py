#!/usr/bin/env python3
"""
Step 2: Validate screen recording is not corrupted and can play fully.
Check 1: File exists and size > 1 KB
Check 2: Opens with moviepy.VideoFileClip without exception
Check 3: Duration readable and > 5 seconds
Check 4: Audio duration ≈ video duration (±0.5 s)
Check 5: Seek to 10%, 50%, 90% and read frame + audio sample without error
Outputs JSON to stdout: { "ok": true, "duration": 222.5, "durationFormatted": "3:42" } or { "ok": false, "error": "..." }
"""

import json
import os
import sys

TOLERANCE_S = 0.5
MIN_SIZE_BYTES = 1024
MIN_DURATION_S = 5.0
SEEK_FRACTIONS = (0.1, 0.5, 0.9)


def format_duration(seconds):
    if not (isinstance(seconds, (int, float)) and seconds >= 0):
        return "0:00"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "Missing file path"}))
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isabs(path):
        path = os.path.abspath(path)

    # Check 1: File exists and size > 1 KB
    if not os.path.isfile(path):
        print(json.dumps({"ok": False, "error": "File does not exist"}))
        sys.exit(0)
    size = os.path.getsize(path)
    if size <= MIN_SIZE_BYTES:
        print(json.dumps({"ok": False, "error": f"File too small (must be > {MIN_SIZE_BYTES} bytes)"}))
        sys.exit(0)

    # Check 2 & 3 & 4 & 5: MoviePy
    try:
        from moviepy.editor import VideoFileClip
    except ImportError:
        print(json.dumps({"ok": False, "error": "MoviePy not installed (pip install moviepy)"}))
        sys.exit(0)

    clip = None
    try:
        clip = VideoFileClip(path)

        # Check 3: Duration readable and > 5 seconds
        dur = float(clip.duration)
        if not (dur > MIN_DURATION_S):
            print(json.dumps({"ok": False, "error": f"Duration must be > {MIN_DURATION_S} seconds (got {dur:.1f}s)"}))
            sys.exit(0)

        # Check 4: Audio track and duration ≈ video duration
        if clip.audio is None:
            print(json.dumps({"ok": False, "error": "No audio track in file"}))
            sys.exit(0)
        audio_dur = float(clip.audio.duration)
        if abs(audio_dur - dur) > TOLERANCE_S:
            print(json.dumps({
                "ok": False,
                "error": f"Audio duration ({audio_dur:.1f}s) does not match video duration ({dur:.1f}s); tolerance ±{TOLERANCE_S}s",
            }))
            sys.exit(0)

        # Check 5: Seek to 10%, 50%, 90% and read frame + audio sample
        for frac in SEEK_FRACTIONS:
            t = dur * frac
            clip.get_frame(t)
            clip.audio.get_frame(t)

        print(json.dumps({
            "ok": True,
            "duration": dur,
            "durationFormatted": format_duration(dur),
        }))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(0)
    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
