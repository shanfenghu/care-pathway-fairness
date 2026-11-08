"""Fetch or verify only the pinned public tables needed by these experiments.

Existing mismatched files are rejected. Downloads use a temporary file and are
installed only after size and SHA-256 checks. No credentials are requested.
"""
import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path
from paths import ROOT, RAW


def records():
    return json.loads((ROOT/'data/input-manifest.json').read_text())['files']


def target(root, record):
    name = Path(record['path'])
    if name.is_absolute() or '..' in name.parts:
        raise ValueError('Input path escapes its root')
    destination = root/name
    if not destination.resolve().is_relative_to(root.resolve()):
        raise ValueError('Input symlink escapes its root')
    return destination


def matches(path, record):
    return (path.is_file() and path.stat().st_size == record['bytes'] and
            hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256'])


def verify(root):
    for record in records():
        if not matches(target(root, record), record):
            raise ValueError('Missing or changed public input: '+record['path'])
    print('All pinned public input sizes and hashes match.')


def fetch(root):
    for record in records():
        path = target(root, record)
        if path.exists():
            if not matches(path, record):
                raise ValueError('Preserve mismatched existing input: '+record['path'])
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.download-')
        os.close(fd)
        try:
            with urllib.request.urlopen(record['url'], timeout=120) as source, open(temporary, 'wb') as out:
                while chunk := source.read(1024*1024):
                    out.write(chunk)
            if not matches(Path(temporary), record):
                raise ValueError('Provider input differs from pinned version: '+record['path'])
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    verify(root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['fetch', 'verify'])
    parser.add_argument('--raw-root', type=Path, default=RAW)
    args = parser.parse_args()
    globals()[args.action](args.raw_root.resolve())
