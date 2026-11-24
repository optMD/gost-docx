import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import apply_gost


class AtomicDocxTests(unittest.TestCase):
    def test_archive_and_replace_failures_preserve_destination(self):
        for failure in ("write", "replace"):
            with self.subTest(failure=failure), TemporaryDirectory() as tmp:
                destination = Path(tmp) / "out.docx"
                destination.write_bytes(b"previous")
                target = "apply_gost.zipfile.ZipFile.writestr" if failure == "write" else "apply_gost.os.replace"
                with patch(target, side_effect=OSError("disk unavailable")):
                    with self.assertRaises(OSError):
                        apply_gost.save_docx(destination, {"part": b"new"}, ["part"])
                self.assertEqual(destination.read_bytes(), b"previous")
                self.assertEqual(list(Path(tmp).iterdir()), [destination])

    def test_archive_contents_survive_successful_replace(self):
        with TemporaryDirectory() as tmp:
            destination = Path(tmp) / "out.docx"
            parts = {"word/document.xml": b"<xml/>", "word/media/image.png": bytes(range(256))}
            apply_gost.save_docx(destination, parts, list(parts))
            with zipfile.ZipFile(destination) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual({name: archive.read(name) for name in archive.namelist()}, parts)
            self.assertEqual(list(Path(tmp).iterdir()), [destination])
