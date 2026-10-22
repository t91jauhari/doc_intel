"""Offline verification of backup integrity; no Docker/storage access."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from app.configuration.backup_objects import verify


class ObjectBackupTests(unittest.TestCase):
    def archive(self, path, *, data=b"synthetic", expected=None, extra=False):
        manifest = {"format": 1, "objects": [{"key": "synthetic.pdf", "member": "objects/0",
            "size": len(data), "sha256": expected or hashlib.sha256(data).hexdigest()}]}
        with tarfile.open(path, "w:gz") as archive:
            for name, content in [("objects/0", data), ("manifest.json", json.dumps(manifest).encode())]:
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            if extra:
                archive.addfile(tarfile.TarInfo("unexpected"), io.BytesIO())

    def test_valid_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.tar.gz"
            self.archive(path)
            result = verify(path)
            self.assertTrue(result["verified"])
            self.assertEqual(result["objects"], 1)
            self.assertFalse(result["live_storage_modified"])

    def test_corrupted_object_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.tar.gz"
            self.archive(path, expected="0" * 64)
            with self.assertRaisesRegex(ValueError, "checksum"):
                verify(path)

    def test_unexpected_member_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "backup.tar.gz"
            self.archive(path, extra=True)
            with self.assertRaisesRegex(ValueError, "inventory"):
                verify(path)
