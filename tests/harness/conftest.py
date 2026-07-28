from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def fake_provider_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = """#!/bin/sh
name=$(basename "$0")
if [ "${1:-}" = "--version" ]; then
  echo "$name 1.0.0"
  exit 0
fi
for arg in "$@"; do
  if [ "$arg" = "--help" ]; then
    echo "$name fake help"
    exit 0
  fi
done
output=""
for arg in "$@"; do
  if [ "${previous:-}" = "-o" ]; then
    output="$arg"
  fi
  previous="$arg"
done
if [ -n "${FAKE_PROVIDER_SLEEP:-}" ]; then
  sleep "$FAKE_PROVIDER_SLEEP"
fi
printf '{"type":"thread.started","thread_id":"session-123"}\n'
printf '{"type":"turn.completed"}\n'
if [ -n "$output" ]; then
  mkdir -p "$(dirname "$output")"
  printf '# verified result\nprovider=%s\n' "$name" > "$output"
fi
exit "${FAKE_PROVIDER_EXIT_CODE:-0}"
"""
    for binary_name in ("codex", "omx"):
        binary_path = bin_dir / binary_name
        binary_path.write_text(script, encoding="utf-8")
        binary_path.chmod(0o755)
    current_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{current_path}")
    return bin_dir
