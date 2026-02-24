#!/usr/bin/env python3
"""
Step 14: Mix a layer into the main track.
Usage: mix_audio.py <main_wav> <layer_wav> <output_wav> <mode> [start_sec end_sec]
Modes: overlay50 | replace | append | sidechain
  overlay50  - overlay layer at 50% volume on main
  replace    - replace main[start:end] with layer (trimmed); requires start_sec end_sec
  append     - append layer after main
  sidechain  - overlay with ducking: main reduced when layer has signal (simplified: main -3dB + layer)
"""

import sys


def main():
    if len(sys.argv) < 5:
        print("Usage: mix_audio.py <main_wav> <layer_wav> <output_wav> <mode> [start_sec end_sec]",
              file=sys.stderr)
        sys.exit(1)
    main_path = sys.argv[1]
    layer_path = sys.argv[2]
    out_path = sys.argv[3]
    mode = sys.argv[4].lower()
    start_sec = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    end_sec = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0

    try:
        from pydub import AudioSegment
    except ImportError:
        print("pydub required: pip install pydub", file=sys.stderr)
        sys.exit(1)

    main = AudioSegment.from_wav(main_path)
    layer = AudioSegment.from_wav(layer_path)
    # Match frame rate if needed (pydub often handles this)
    if main.frame_rate != layer.frame_rate:
        layer = layer.set_frame_rate(main.frame_rate)
    if main.channels != layer.channels:
        layer = layer.set_channels(main.channels)

    if mode == "overlay50":
        # Layer at 50% volume (~ -6 dB)
        layer_50 = layer - 6
        out = main.overlay(layer_50, position=0, gain_during_overlay=0)
    elif mode == "replace":
        start_ms = int(start_sec * 1000)
        end_ms = int(end_sec * 1000)
        if start_ms >= end_ms or start_ms < 0:
            raise ValueError("Invalid start/end times")
        segment_len = end_ms - start_ms
        layer_trimmed = layer[:segment_len]
        out = main[:start_ms] + layer_trimmed + main[end_ms:]
    elif mode == "append":
        out = main.append(layer, crossfade=0)
    elif mode == "sidechain":
        # Simplified ducking: main at -3 dB, layer full; layer stands out
        main_duck = main - 3
        out = main_duck.overlay(layer, position=0, gain_during_overlay=0)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    out.export(out_path, format="wav")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
