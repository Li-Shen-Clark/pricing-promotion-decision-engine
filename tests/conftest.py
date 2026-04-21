"""Make `src/` importable from anywhere `pytest` is invoked.

Tests rely on the same `src.*` layout the Streamlit pages use; rather than turning
the repo into an installable package for the MVP, we extend `sys.path` once here.
"""
from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
