"""Run shortlisted Excel export in a child process (avoids stale in-memory code)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _backend_python() -> str:
    """Always use project venv so export code matches the repo on disk."""
    for rel in ("venv/Scripts/python.exe", "venv/bin/python"):
        candidate = _BACKEND_ROOT / rel
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def export_batch_in_subprocess(
    batch_id: str,
    *,
    total_cvs: int | None = None,
    position: str | None = None,
) -> dict | None:
    cmd = [
        _backend_python(),
        "-m",
        "app.export_runner_main",
        batch_id,
    ]
    if total_cvs is not None:
        cmd.extend(["--total-cvs", str(int(total_cvs))])
    if position:
        cmd.extend(["--position", position])

    env = os.environ.copy()
    proc = subprocess.run(
        cmd,
        cwd=str(_BACKEND_ROOT),
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )

    if proc.returncode != 0:
        print("Excel subprocess failed:", proc.stderr or proc.stdout)
        return None

    line = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else ""
    if not line or line == "null":
        return None

    data = json.loads(line)
    generated_at = data.get("generated_at")
    if isinstance(generated_at, str):
        generated_at = datetime.fromisoformat(generated_at)

    return {
        "file_path": data["file_path"],
        "file_name": data["file_name"],
        "generated_at": generated_at,
        "generated_at_sl": data.get("generated_at_sl"),
        "batch_no": data.get("batch_no"),
        "cv_count": data.get("cv_count"),
        "shortlisted_count": data.get("shortlisted_count"),
    }
