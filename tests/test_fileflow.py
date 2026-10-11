"""FileFlow checks using temporary folders and a local HTTP server."""

import io
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from features import analyzer
from features.downloader import download_file
from main import main


class FileFlowTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name).resolve()

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, name, content=b"data"):
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def invoke(self, *arguments, answer=""):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            with patch("builtins.input", return_value=answer):
                try:
                    code = main(list(arguments))
                except SystemExit as error:
                    code = error.code
        return code, stdout.getvalue(), stderr.getvalue()


class FeatureTests(FileFlowTestCase):
    def test_help_and_version(self):
        code, output, error = self.invoke("--help")
        self.assertEqual(code, 0)
        for command in ("download", "organize", "analyze"):
            self.assertIn(command, output)
            self.assertEqual(self.invoke(command, "--help")[0], 0)
        self.assertEqual(error, "")
        self.assertEqual(self.invoke("--version")[:2], (0, "FileFlow 0.1.0\n"))

    def test_invalid_arguments(self):
        cases = [
            (),
            ("analyze", str(self.folder / "missing")),
            ("analyze", str(self.folder), "--largest", "0"),
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(self.invoke(*arguments)[0], 2)

    def test_organize_preview_and_apply(self):
        image = self.write("photo.JPG", b"new image")
        original = self.write("Images/photo.JPG", b"existing image")
        self.write("clip.mp4")
        self.write("notes.pdf")
        self.write("song.mp3")
        self.write("unknown.bin")
        nested = self.write("nested/leave.txt")
        self.assertEqual(self.invoke("organize", str(self.folder))[0], 0)
        self.assertTrue(image.exists())
        self.assertEqual(self.invoke("organize", str(self.folder), "--apply")[0], 0)
        self.assertFalse(image.exists())
        self.assertEqual(original.read_bytes(), b"existing image")
        self.assertEqual(
            (self.folder / "Images/photo (2).JPG").read_bytes(), b"new image"
        )
        for name in (
            "Videos/clip.mp4",
            "Documents/notes.pdf",
            "Audio/song.mp3",
            "Other/unknown.bin",
        ):
            self.assertTrue((self.folder / name).is_file())
        self.assertTrue(nested.exists())

    def test_organize_category_conflict_changes_nothing(self):
        image = self.write("picture.png")
        self.write("Images", b"a file, not a folder")
        self.assertEqual(self.invoke("organize", str(self.folder), "--apply")[0], 1)
        self.assertTrue(image.exists())

    def test_analyzer_is_recursive_and_sorts_by_size(self):
        self.write("small.TXT", b"a")
        large = self.write("nested/large.txt", b"x" * 100)
        self.write("without_extension", b"abc")
        counts, sizes = analyzer.analyze(self.folder)
        self.assertEqual(counts, {".txt": 2, "[no extension]": 1})
        self.assertEqual(sizes[0], (large, 100))
        code, output, error = self.invoke("analyze", str(self.folder), "--largest", "1")
        self.assertEqual(code, 0)
        self.assertIn("Files: 3", output)
        self.assertIn("large.txt", output)
        self.assertEqual(error, "")


class DownloadHandler(BaseHTTPRequestHandler):
    active = 0
    maximum = 0
    lock = threading.Lock()

    def do_GET(self):
        with self.lock:
            DownloadHandler.active += 1
            DownloadHandler.maximum = max(self.active, self.maximum)
        try:
            time.sleep(0.1)
            if self.path == "/missing":
                self.send_error(404)
                return
            content = b"payload:" + self.path.encode()
            self.send_response(200)
            length = len(content) + (20 if self.path == "/partial" else 0)
            self.send_header("Content-Length", str(length))
            self.end_headers()
            self.wfile.write(content)
        finally:
            with self.lock:
                DownloadHandler.active -= 1

    def log_message(self, format, *args):
        pass


class DownloadTests(FileFlowTestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
        cls.server_thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True
        )
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join()

    def test_single_download_keeps_existing_file(self):
        existing = self.write("file.bin", b"keep")
        saved = download_file(self.base_url + "/file.bin", self.folder)
        self.assertEqual(existing.read_bytes(), b"keep")
        self.assertEqual(saved.name, "file (2).bin")
        self.assertEqual(saved.read_bytes(), b"payload:/file.bin")


if __name__ == "__main__":
    unittest.main()
