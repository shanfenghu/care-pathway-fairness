"""Explicit input/output locations, independent of the caller's directory."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = Path(os.environ.get('LINKAGE_RAW_ROOT', ROOT/'data/raw')).resolve()
PROCESSED = Path(os.environ.get('LINKAGE_PROCESSED_ROOT', ROOT/'data/processed/link-change')).resolve()
DEFAULT = ROOT/'results/reproduced'
