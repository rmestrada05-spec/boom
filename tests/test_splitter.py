import json
import math
import os
import tempfile
import unittest
import wave

import numpy as np

from garageband_agent.splitter import (
    cached_clips_to_json,
    list_cached_clips,
    split_song_to_cache,
    splitter_report_to_json,
)


def _write_wav(path: str, signal: np.ndarray, sample_rate: int) -> None:
    clipped = np.clip(signal, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())


def _build_split_test_song() -> str:
    sample_rate = 22050
    duration = 10.0
    signal = np.zeros(int(duration * sample_rate), dtype=np.float32)
    beat_times = np.arange(0.5, duration - 0.1, 0.5)

    for beat_time in beat_times:
        start = int(beat_time * sample_rate)
        length = int(0.09 * sample_rate)
        t = np.arange(length) / float(sample_rate)
        env = np.exp(-18.0 * t)
        bass = 0.90 * env * np.sin(2.0 * math.pi * 58.0 * t)
        click = 0.18 * np.exp(-40.0 * t) * np.sin(2.0 * math.pi * 2200.0 * t)
        end = min(signal.size, start + length)
        signal[start:end] += bass[: end - start] + click[: end - start]

    for synth_time in [0.75, 1.75, 2.75, 4.75, 6.75, 8.75]:
        start = int(synth_time * sample_rate)
        length = int(0.20 * sample_rate)
        t = np.arange(length) / float(sample_rate)
        env = np.exp(-8.0 * t)
        synth = 0.44 * env * (
            np.sin(2.0 * math.pi * 740.0 * t)
            + 0.28 * np.sin(2.0 * math.pi * 1480.0 * t)
            + 0.18 * np.sin(2.0 * math.pi * 2220.0 * t)
        )
        end = min(signal.size, start + length)
        signal[start:end] += synth[: end - start]

    rng = np.random.default_rng(99)
    signal += 0.01 * rng.standard_normal(signal.size).astype(np.float32)
    signal /= np.max(np.abs(signal)) + 1e-8

    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.close()
    _write_wav(temp_file.name, signal, sample_rate)
    return temp_file.name


class SplitterTests(unittest.TestCase):
    def test_splitter_creates_cache_and_manifest(self) -> None:
        wav_path = _build_split_test_song()
        with tempfile.TemporaryDirectory() as cache_dir:
            try:
                report = split_song_to_cache(
                    file_path=wav_path,
                    cache_dir=cache_dir,
                    event_types=("bass_hits", "synth_hits"),
                    max_events_per_type=3,
                    min_confidence=0.20,
                    pre_roll_seconds=0.06,
                    post_roll_seconds=0.45,
                )
            finally:
                os.unlink(wav_path)

            self.assertGreater(report.clip_count, 0)
            self.assertTrue(os.path.exists(report.manifest_path))
            self.assertIn("bass_hits", report.clips_by_type)
            self.assertIn("synth_hits", report.clips_by_type)
            first_clip = next(
                clip
                for clips in report.clips_by_type.values()
                for clip in clips
            )
            self.assertTrue(os.path.exists(first_clip.clip_path))
            with wave.open(first_clip.clip_path, "rb") as clip_wav:
                self.assertEqual(clip_wav.getframerate(), 48000)
                self.assertEqual(clip_wav.getsampwidth(), 3)
                self.assertEqual(clip_wav.getnchannels(), 1)

            rendered = splitter_report_to_json(report)
            decoded = json.loads(rendered)
            self.assertIn("clip_count", decoded)
            self.assertIn("clips_by_type", decoded)

    def test_cache_listing_and_filtering(self) -> None:
        wav_path = _build_split_test_song()
        with tempfile.TemporaryDirectory() as cache_dir:
            try:
                split_song_to_cache(
                    file_path=wav_path,
                    cache_dir=cache_dir,
                    event_types=("bass_hits", "synth_hits"),
                    max_events_per_type=2,
                    min_confidence=0.15,
                )
            finally:
                os.unlink(wav_path)

            all_clips = list_cached_clips(cache_dir=cache_dir)
            self.assertGreater(len(all_clips), 0)
            bass_only = list_cached_clips(cache_dir=cache_dir, event_type="bass_hits")
            self.assertGreater(len(bass_only), 0)
            self.assertTrue(all(clip.event_type == "bass_hits" for clip in bass_only))

            rendered = cached_clips_to_json(bass_only)
            decoded = json.loads(rendered)
            self.assertIsInstance(decoded, list)
            self.assertGreater(len(decoded), 0)


if __name__ == "__main__":
    unittest.main()
