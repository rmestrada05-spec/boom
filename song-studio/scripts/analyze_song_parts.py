#!/usr/bin/env python3
"""
Step 3: Analyze and organize song parts (librosa only, no stems).
Output: four numbered sections in fixed format for scrollable monospaced display.
Target: < 30 seconds on average song length.
"""

import json
import os
import sys
import tempfile

# Limit analysis duration to keep under 30s wall time (tune if needed)
MAX_DURATION_S = 600
SR = 22050
HOP_LENGTH = 1024
N_FFT = 2048


def sec_to_mmss(sec):
    if sec is None or sec < 0:
        return "0:00"
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}:{s:02d}"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing file path"}))
        sys.exit(1)

    path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(path):
        print(json.dumps({"error": "File not found"}))
        sys.exit(1)

    try:
        import librosa
        import numpy as np
    except ImportError as e:
        print(json.dumps({"error": f"Missing dependency: {e}"}))
        sys.exit(1)

    # Extract audio from video if needed
    ext = os.path.splitext(path)[1].lower()
    if ext in (".mp4", ".mov", ".mkv", ".avi"):
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(path)
            if clip.audio is None:
                clip.close()
                print(json.dumps({"error": "No audio track in file"}))
                sys.exit(1)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_wav = f.name
            try:
                clip.audio.write_audiofile(temp_wav, verbose=False, logger=None, fps=SR, nbytes=2)
                clip.close()
                path = temp_wav
            except Exception:
                if clip:
                    clip.close()
                raise
        except Exception as e:
            print(json.dumps({"error": f"Could not extract audio: {e}"}))
            sys.exit(1)
    else:
        temp_wav = None

    try:
        y, sr = librosa.load(path, sr=SR, mono=True, duration=MAX_DURATION_S)
    except Exception as e:
        print(json.dumps({"error": f"Could not load audio: {e}"}))
        sys.exit(1)
    finally:
        if temp_wav and os.path.isfile(temp_wav):
            try:
                os.unlink(temp_wav)
            except Exception:
                pass

    duration_s = len(y) / sr
    if duration_s < 1:
        print(json.dumps({"error": "Audio too short"}))
        sys.exit(1)

    # --- Features (heuristics for speed) ---
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP_LENGTH, n_fft=N_FFT)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=HOP_LENGTH)
    if hasattr(tempo, "__iter__"):
        tempo = float(np.median(tempo))
    else:
        tempo = float(tempo)

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=HOP_LENGTH, n_fft=N_FFT)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=HOP_LENGTH, n_fft=N_FFT)[0]
    rms = librosa.feature.rms(y=y, hop_length=HOP_LENGTH)[0]

    # Normalize for heuristics (0–1 scale)
    def norm(x):
        x = np.asarray(x)
        mn, mx = x.min(), x.max()
        if mx <= mn:
            return np.zeros_like(x, dtype=float)
        return (x - mn) / (mx - mn)

    onset_n = norm(onset_env)
    centroid_n = norm(centroid)
    rms_n = norm(rms)
    rolloff_n = norm(rolloff)

    # Harmonic/percussive split for vocal vs percussive
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    harmonic_energy = np.mean(librosa.feature.rms(y=y_harmonic, hop_length=HOP_LENGTH))
    percussive_energy = np.mean(librosa.feature.rms(y=y_percussive, hop_length=HOP_LENGTH))
    harmonic_ratio = harmonic_energy / (harmonic_energy + percussive_energy + 1e-8)

    # Mean values over time for layer detection
    mean_onset = float(np.mean(onset_n))
    mean_centroid = float(np.mean(centroid_n))
    mean_rms = float(np.mean(rms_n))
    mean_rolloff = float(np.mean(rolloff_n))

    # --- 1. Functional Musical Layers (presence/confidence) ---
    layers = []

    # Percussion: high onset strength, broadband
    perc_score = mean_onset * 0.7 + (1 - mean_centroid) * 0.3
    if perc_score > 0.5:
        layers.append(("Percussion / Drums", "High confidence", perc_score))
    elif perc_score > 0.25:
        layers.append(("Percussion / Drums", "Possible presence", perc_score))
    else:
        layers.append(("Percussion / Drums", "Low or no presence", perc_score))

    # Bass: low spectral centroid
    bass_score = 1 - mean_centroid
    if bass_score > 0.5:
        layers.append(("Bass", "High confidence", bass_score))
    elif bass_score > 0.25:
        layers.append(("Bass", "Possible presence", bass_score))
    else:
        layers.append(("Bass", "Low or no presence", bass_score))

    # Melody / Keys / Synth: mid–high centroid, harmonic
    melody_score = mean_centroid * 0.5 + harmonic_ratio * 0.5
    if melody_score > 0.5:
        layers.append(("Melody / Keys / Synth", "High confidence", melody_score))
    elif melody_score > 0.25:
        layers.append(("Melody / Keys / Synth", "Possible presence", melody_score))
    else:
        layers.append(("Melody / Keys / Synth", "Low or no presence", melody_score))

    # Pad / Texture: high rolloff, sustained
    pad_score = mean_rolloff * 0.5 + (1 - mean_onset) * 0.5
    if pad_score > 0.5:
        layers.append(("Pad / Texture", "High confidence", pad_score))
    elif pad_score > 0.25:
        layers.append(("Pad / Texture", "Possible presence", pad_score))
    else:
        layers.append(("Pad / Texture", "Low or no presence", pad_score))

    # --- 2. Vocal Specifics ---
    # Heuristic: harmonic content in typical vocal range + mid centroid
    vocal_score = harmonic_ratio * 0.6 + (0.3 + 0.4 * mean_centroid) * 0.4
    if vocal_score > 0.55:
        vocal_specifics = "High confidence vocal presence; harmonic content and mid-range energy detected."
    elif vocal_score > 0.35:
        vocal_specifics = "Possible vocal presence; moderate harmonic and mid-range content."
    else:
        vocal_specifics = "Low confidence vocal presence; mix may be instrumental or heavily processed."

    # --- 3. Structural Parts (novelty → boundaries, then label) ---
    # Novelty: chroma-based frame difference (structure boundaries)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP_LENGTH)
    # Simple novelty: L1 difference between consecutive frames (smoothed)
    chroma_diff = np.abs(np.diff(chroma, axis=1)).sum(axis=0)
    chroma_diff = np.convolve(chroma_diff, np.ones(5) / 5, mode="same")
    # Peak picking for boundaries (every N seconds minimum)
    min_gap_frames = max(1, int(8.0 * sr / HOP_LENGTH))  # ~8 s min segment
    thresh = float(np.percentile(chroma_diff, 75))
    peaks = []
    for i in range(1, len(chroma_diff) - 1):
        if chroma_diff[i] < thresh:
            continue
        if chroma_diff[i] <= chroma_diff[i - 1] or chroma_diff[i] <= chroma_diff[i + 1]:
            continue
        if peaks and (i - peaks[-1]) < min_gap_frames:
            if chroma_diff[i] > chroma_diff[peaks[-1]]:
                peaks[-1] = i
            continue
        peaks.append(i)
    boundaries = [0] + peaks + [chroma.shape[1] - 1]
    boundaries = sorted(set(boundaries))

    times = librosa.frames_to_time(boundaries, sr=sr, hop_length=HOP_LENGTH)
    time_ranges = []
    for i in range(len(times) - 1):
        start_s = float(times[i])
        end_s = float(times[i + 1])
        time_ranges.append((sec_to_mmss(start_s), sec_to_mmss(end_s)))

    # Label segments heuristically; mark repeated high-energy as possible chorus
    n_seg = len(time_ranges)
    labels = []
    high_energy_idxs = []
    for i in range(n_seg):
        if i == 0:
            labels.append("Intro")
        elif i == n_seg - 1:
            labels.append("Outro")
        else:
            start_f = boundaries[i]
            end_f = boundaries[i + 1]
            seg_rms = float(np.mean(rms_n[start_f:end_f])) if end_f > start_f else 0
            if seg_rms > 0.6:
                labels.append("Chorus / High energy")
                high_energy_idxs.append(i)
            elif seg_rms > 0.4:
                labels.append("Verse / Mid energy")
            else:
                labels.append("Bridge / Low energy")

    structural_lines = ["  (Segment boundaries from chroma novelty; confidence qualifiers below.)", ""]
    for (start, end), label, idx in zip(time_ranges, labels, range(n_seg)):
        structural_lines.append(f"  {start} – {end}  {label}")
    if len(high_energy_idxs) >= 2:
        structural_lines.append("")
        structural_lines.append("  High confidence chorus repetition (multiple high-energy segments detected).")

    # --- 4. Descriptive Terms for Sound ---
    terms = []
    if tempo < 90:
        terms.append("Slow tempo")
    elif tempo > 130:
        terms.append("Fast tempo")
    else:
        terms.append("Medium tempo")
    if mean_centroid > 0.6:
        terms.append("Bright")
    elif mean_centroid < 0.4:
        terms.append("Dark")
    if mean_rolloff > 0.6:
        terms.append("Crisp / present high end")
    if mean_rms > 0.6:
        terms.append("Loud / high dynamics")
    elif mean_rms < 0.3:
        terms.append("Quiet / low dynamics")
    if harmonic_ratio > 0.6:
        terms.append("Harmonic")
    else:
        terms.append("Percussive / rhythmic")
    if mean_onset > 0.5:
        terms.append("Rhythmically active")
    descriptive = ", ".join(terms) + "."

    # --- Build exact four-section output ---
    section1_lines = ["1. Functional Musical Layers (list each role with detected presence/confidence)", ""]
    for role, conf, _ in layers:
        section1_lines.append(f"  - {role}: {conf}")

    section2_lines = ["2. Vocal Specifics", "", f"  {vocal_specifics}"]

    section3_lines = ["3. Structural Parts (with approximate time ranges in mm:ss)", ""] + structural_lines

    section4_lines = ["4. Descriptive Terms for Sound", "", f"  {descriptive}"]

    full_text = "\n".join(
        section1_lines + [""] + section2_lines + [""] + section3_lines + [""] + section4_lines
    )

    print(json.dumps({"analysis": full_text, "durationFormatted": sec_to_mmss(duration_s)}))


if __name__ == "__main__":
    main()
