"""AI stem separation helpers using Demucs."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


class StemSeparationError(RuntimeError):
    """Raised when Demucs stem separation fails."""


@dataclass
class StemSeparationResult:
    stems: dict[str, str]
    output_root: str
    model: str


DEFAULT_DEMUCS_MODEL = "htdemucs"
PREFERRED_STEM_ORDER = ("drums", "bass", "vocals", "other", "guitar", "piano")


def _discover_track_dir(output_root: Path, model: str, audio_path: Path) -> Path:
    base_dir = output_root / model
    direct_path = base_dir / audio_path.stem
    if direct_path.exists():
        return direct_path
    candidates = sorted([candidate for candidate in base_dir.glob("*") if candidate.is_dir()])
    if not candidates:
        raise StemSeparationError("Demucs did not produce any output track directory.")
    return candidates[0]


def separate_stems_with_demucs(
    audio_file_path: str,
    model: str = DEFAULT_DEMUCS_MODEL,
    device: str = "cpu",
) -> StemSeparationResult:
    """Run Demucs and return discovered stem file paths."""
    audio_path = Path(audio_file_path).expanduser().resolve()
    if not audio_path.exists():
        raise StemSeparationError(f"Audio file does not exist: {audio_path}")

    output_root = Path(tempfile.mkdtemp(prefix="demucs_sep_"))
    command = [
        sys.executable,
        "-m",
        "demucs.separate",
        "--name",
        model,
        "--device",
        device,
        "--float32",
        "--out",
        str(output_root),
        str(audio_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        shutil.rmtree(output_root, ignore_errors=True)
        raise StemSeparationError(
            "Demucs separation failed. "
            f"stdout={stdout[:500]} stderr={stderr[:500]}"
        )

    track_dir = _discover_track_dir(output_root=output_root, model=model, audio_path=audio_path)
    stems: dict[str, str] = {}
    for stem_name in PREFERRED_STEM_ORDER:
        stem_path = track_dir / f"{stem_name}.wav"
        if stem_path.exists():
            stems[stem_name] = str(stem_path)

    if not stems:
        shutil.rmtree(output_root, ignore_errors=True)
        raise StemSeparationError("Demucs completed but no expected stem WAV files were found.")

    return StemSeparationResult(stems=stems, output_root=str(output_root), model=model)


def cleanup_stem_output(output_root: str) -> None:
    """Remove temporary stem output directory."""
    shutil.rmtree(output_root, ignore_errors=True)
