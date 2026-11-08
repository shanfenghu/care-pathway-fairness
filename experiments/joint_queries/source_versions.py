"""Validate source identities, allowing only explicitly documented version pairs.

Retained generation records are immutable. Amendments pin both the exact older
source bytes and the active version; an unlisted source change remains an error.
"""
import hashlib
import json
from pathlib import Path
from paths import ROOT

APPLIED = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rooted(root, name):
    """Resolve a regular input without accepting absolute, escaping or symlink paths."""
    name = Path(name)
    if name.is_absolute() or '..' in name.parts:
        raise ValueError('Source path escapes its root')
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Source resolves outside its root')
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError('Source symlinks are not accepted')
    if not path.is_file():
        raise ValueError('Missing source input: ' + str(name))
    return path


def verify_sources(records, root=ROOT):
    """Check every generation pin; accept only a declared old-to-active amendment."""
    root = Path(root).resolve()
    config = json.loads((root/'configs/source-amendments.json').read_text())
    amendments = {row['path']: row for row in config['amendments']}
    if len(amendments) != len(config['amendments']):
        raise ValueError('Duplicate source amendment')
    for row in amendments.values():
        if digest(rooted(root, row['generation_source'])) != row['generation_sha256']:
            raise ValueError('Frozen generation source changed: ' + row['path'])
        if digest(rooted(root, row['path'])) != row['active_sha256']:
            raise ValueError('Active amended source changed: ' + row['path'])
    for record in records:
        current = digest(rooted(root, record['path']))
        if current == record['sha256']:
            continue
        row = amendments.get(record['path'])
        if row is None or record['sha256'] != row['generation_sha256'] or current != row['active_sha256']:
            raise ValueError('Unrecorded source version: ' + record['path'])
        if row not in APPLIED:
            APPLIED.append(row)


def load_bundle(output, protocol, root=ROOT):
    """Load cases only after checking the unchanged protocol and all source pins."""
    bundle = json.loads((output/'cases.json').read_text())
    if digest(protocol) != bundle['protocol_sha256']:
        raise ValueError('Generation protocol changed')
    verify_sources(bundle['sources'], root)
    return bundle
