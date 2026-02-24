import json
import math
import os
import tempfile
import unittest
import wave

import numpy as np

from garageband_agent.song_analyzer import (
    analysis_to_json,
    analysis_to_pretty_text,
    analyze_song,
)


def _add_tone_burst(
    signal: np.ndarray,
    sample_rate: int,
    start_time: float,
    duration: float,
    frequency_hz: float,
    amplitude: float,
    decay: float = 10.0,
    harmonics: tuple[float, ...] = (),
) -> None:
    start_idx = int(start_time * sample_rate)
    sample_count = int(duration * sample_rate)
    if sample_count <= 0 or start_idx >= signal.size:
        return
    end_idx = min(signal.size, start_idx + sample_count)
    sample_count = end_idx - start_idx
    if sample_count <= 0:
        return

    t = np.arange(sample_count, dtype=np.float32) / float(sample_rate)
    envelope = np.exp(-decay * t)
    base = np.sin(2.0 * math.pi * frequency_hz * t)
    for ratio in harmonics:
        base += (1.0 / (1.0 + ratio)) * np.sin(2.0 * math.pi * frequency_hz * ratio * t)
    signal[start_idx:end_idx] += amplitude * envelope * base


def _add_vocal_phrase(
    signal: np.ndarray,
    sample_rate: int,
    start_time: float,
    duration: float,
    base_freq_hz: float,
    amplitude: float,
) -> None:
    start_idx = int(start_time * sample_rate)
    sample_count = int(duration * sample_rate)
    if sample_count <= 0 or start_idx >= signal.size:
        return
    end_idx = min(signal.size, start_idx + sample_count)
    sample_count = end_idx - start_idx
    if sample_count <= 0:
        return

    t = np.arange(sample_count, dtype=np.float32) / float(sample_rate)
    # Lightweight vocal-like synthetic source with gentle vibrato and harmonics.
    freq_curve = base_freq_hz * (1.0 + 0.03 * np.sin(2.0 * math.pi * 5.0 * t))
    phase = 2.0 * math.pi * np.cumsum(freq_curve) / float(sample_rate)
    phrase = (
        np.sin(phase)
        + 0.42 * np.sin(2.0 * phase)
        + 0.25 * np.sin(3.0 * phase)
        + 0.12 * np.sin(4.0 * phase)
    )
    attack = np.clip(t / 0.05, 0.0, 1.0)
    release = np.clip((duration - t) / 0.09, 0.0, 1.0)
    envelope = attack * release
    signal[start_idx:end_idx] += amplitude * envelope * phrase


def _write_wav(path: str, signal: np.ndarray, sample_rate: int) -> None:
    clipped = np.clip(signal, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


class SongAnalyzerTests(unittest.TestCase):
    def _build_test_song(self) -> tuple[str, dict[str, list[float]]]:
        sample_rate = 22050
        duration = 12.0
        signal = np.zeros(int(duration * sample_rate), dtype=np.float32)

        expected: dict[str, list[float]] = {
            "bass": [],
            "synth": [],
            "guitar": [],
            "lead_vocal": [],
            "background_vocal": [],
        }

        beat_times = np.arange(0.5, duration - 0.1, 0.5)
        for beat_time in beat_times:
            # Kick-like low burst + short click for strong onset.
            _add_tone_burst(signal, sample_rate, float(beat_time), 0.09, 58.0, 0.9, decay=19.0)
            _add_tone_burst(signal, sample_rate, float(beat_time), 0.03, 2200.0, 0.18, decay=35.0)
            expected["bass"].append(float(beat_time))

        synth_times = [0.75, 1.75, 2.75, 4.75, 6.75, 8.75, 10.75]
        for synth_time in synth_times:
            _add_tone_burst(
                signal,
                sample_rate,
                synth_time,
                0.18,
                720.0,
                0.42,
                decay=9.0,
                harmonics=(2.0, 3.0),
            )
            expected["synth"].append(synth_time)

        guitar_times = [1.25, 3.25, 5.25, 7.25, 9.25]
        for guitar_time in guitar_times:
            # Triad-like pluck with fast decay.
            _add_tone_burst(
                signal,
                sample_rate,
                guitar_time,
                0.22,
                246.0,
                0.36,
                decay=14.0,
                harmonics=(1.5, 2.2, 2.8),
            )
            _add_tone_burst(signal, sample_rate, guitar_time, 0.22, 329.0, 0.22, decay=14.0)
            expected["guitar"].append(guitar_time)

        lead_vocal_times = [2.0, 5.6, 8.6]
        for lead_time in lead_vocal_times:
            _add_vocal_phrase(signal, sample_rate, lead_time, 0.62, 175.0, 0.47)
            expected["lead_vocal"].append(lead_time)

        background_vocal_times = [3.4, 6.9, 10.0]
        for bg_time in background_vocal_times:
            _add_vocal_phrase(signal, sample_rate, bg_time, 0.45, 208.0, 0.24)
            expected["background_vocal"].append(bg_time)

        rng = np.random.default_rng(7)
        signal += 0.01 * rng.standard_normal(signal.size).astype(np.float32)
        signal /= np.max(np.abs(signal)) + 1e-8

        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file.close()
        _write_wav(temp_file.name, signal, sample_rate)
        return temp_file.name, expected

    def test_song_analysis_detects_tempo_and_events(self) -> None:
        wav_path, expected = self._build_test_song()
        try:
            report = analyze_song(wav_path)
        finally:
            os.unlink(wav_path)

        self.assertIsNotNone(report.bpm)
        assert report.bpm is not None
        self.assertGreater(report.bpm, 108.0)
        self.assertLess(report.bpm, 132.0)

        events = report.events_by_type
        self.assertGreater(len(events["bass_hits"]), 8)
        self.assertGreater(len(events["synth_hits"]), 4)
        self.assertGreater(len(events["guitar_hits"]), 2)
        self.assertGreater(len(events["lead_vocal_entries"]), 1)
        self.assertGreater(len(events["background_vocal_entries"]), 0)
        self.assertGreater(len(events["section_changes"]), 0)
        self.assertGreater(len(report.beat_timestamps), 12)

        # Check at least one lead-vocal event lands near inserted phrases.
        lead_times = [event.time_seconds for event in events["lead_vocal_entries"]]
        self.assertTrue(
            any(min(abs(detected - expected_t) for expected_t in expected["lead_vocal"]) < 0.25 for detected in lead_times)
        )

    def test_song_analysis_serialization(self) -> None:
        wav_path, _ = self._build_test_song()
        try:
            report = analyze_song(wav_path)
        finally:
            os.unlink(wav_path)

        rendered = analysis_to_json(report)
        decoded = json.loads(rendered)
        self.assertIn("bpm", decoded)
        self.assertIn("events_by_type", decoded)
        pretty = analysis_to_pretty_text(report, max_timestamps_per_type=3)
        self.assertIn("Estimated BPM", pretty)
        self.assertIn("bass_hits", pretty)


if __name__ == "__main__":
    unittest.main()
