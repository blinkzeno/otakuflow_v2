"""Smoke test: the bundled FFmpeg binary resolves and runs."""

import subprocess
from pathlib import Path

import imageio_ffmpeg


def test_ffmpeg_binary_exists_and_runs():
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    assert Path(exe).exists()
    completed = subprocess.run(
        [exe, "-version"], capture_output=True, text=True, timeout=30
    )
    assert completed.returncode == 0
    assert "ffmpeg version" in completed.stdout
