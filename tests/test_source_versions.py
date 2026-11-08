"""Regressions for explicit source amendments and preserved generation identities."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'experiments/joint_queries'))
from source_versions import load_bundle, verify_sources


def digest(data):
    return hashlib.sha256(data).hexdigest()


class SourceVersions(unittest.TestCase):
    def fixture(self, root):
        (root/'configs').mkdir()
        (root/'active.py').write_bytes(b'new validation')
        (root/'generation.txt').write_bytes(b'old validation')
        (root/'unchanged.py').write_bytes(b'unchanged')
        row = dict(path='active.py', generation_source='generation.txt',
                   generation_sha256=digest(b'old validation'), active_sha256=digest(b'new validation'))
        (root/'configs/source-amendments.json').write_text(json.dumps({'amendments':[row]}))
        return [dict(path='active.py',sha256=digest(b'old validation')),
                dict(path='unchanged.py',sha256=digest(b'unchanged'))]

    def test_only_declared_pair_and_current_pins_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); records=self.fixture(root)
            verify_sources(records,root)
            verify_sources([dict(path='active.py',sha256=digest(b'new validation'))],root)
            records[0]['sha256']=digest(b'unknown intermediate version')
            with self.assertRaises(ValueError): verify_sources(records,root)

    def test_unlisted_and_declared_active_drift_are_rejected(self):
        for changed in ['active.py','unchanged.py']:
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);records=self.fixture(root);(root/changed).write_bytes(b'drift')
                with self.assertRaises(ValueError): verify_sources(records,root)

    def test_generation_backup_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);records=self.fixture(root);(root/'generation.txt').write_bytes(b'other old code')
            with self.assertRaises(ValueError): verify_sources(records,root)

    def test_source_escape_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root);(root/'alias.py').symlink_to(root/'unchanged.py')
            for name in ['../outside','/absolute','alias.py']:
                with self.subTest(name=name),self.assertRaises(ValueError):
                    verify_sources([dict(path=name,sha256='0'*64)],root)

    def test_protocol_drift_remains_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);records=self.fixture(root);protocol=root/'protocol.json';protocol.write_bytes(b'fixed choices')
            output=root/'records';output.mkdir();(output/'cases.json').write_text(json.dumps(
                dict(protocol_sha256=digest(b'fixed choices'),sources=records)))
            self.assertEqual(load_bundle(output,protocol,root)['sources'],records)
            protocol.write_bytes(b'changed choices')
            with self.assertRaises(ValueError): load_bundle(output,protocol,root)
