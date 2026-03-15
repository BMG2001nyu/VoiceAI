"""Shared test configuration for backend tests.

Ensures the project root (parent of backend/) is on sys.path so that
the ``agents`` package (which lives at the repo root) is importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Project root = parent of backend/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_ROOT = Path(__file__).resolve().parent.parent

for p in (_PROJECT_ROOT, _BACKEND_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
