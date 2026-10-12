"""FileFlow checks using temporary folders and a local HTTP server."""

import io
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from features import analyzer, duplicates, empty
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
        for command in ("download", "organize", "analyze", "duplicates", "empty"):
            self.assertIn(command, output)
            self.assertEqual(self.invoke(command, "--help")[0], 0)
        self.assertEqual(error, "")
        self.assertEqual(self.invoke("--version")[:2], (0, "FileFlow 0.1.0\n"))

    def test_invalid_arguments(self):
        cases = [
            (),
            ("analyze", str(self.folder / "missing")),
            ("analyze", str(self.folder), "--largest", "0"),
            ("download", "https://example.com/file", "--workers", "0"),
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(self.invoke(*arguments)[0], 2)

    def test_download_needs_urls(self):
        code, output, error = self.invoke("download", "--output", str(self.folder))
        self.assertEqual(code, 1)
        self.assertIn("Provide a URL", error)

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

    def test_duplicates_use_content_not_name_or_only_size(self):
        first = self.write("a.txt", b"same")
        second = self.write("nested/different-name.bin", b"same")
        distinct = self.write("different.txt", b"else")
        self.assertEqual(duplicates.find_duplicates(self.folder), [[first, second]])
        self.assertEqual(self.invoke("duplicates", str(self.folder), "--delete")[0], 0)
        self.assertTrue(second.exists())
        self.assertEqual(
            self.invoke("duplicates", str(self.folder), "--delete", answer="yes")[0], 0
        )
        self.assertTrue(first.exists())
        self.assertFalse(second.exists())
        self.assertTrue(distinct.exists())

    def test_duplicate_changed_during_confirmation_is_kept(self):
        first = self.write("a.txt", b"same")
        second = self.write("b.txt", b"same")

        def change_file(message):
            first.write_bytes(b"changed")
            return "yes"

        with patch("builtins.input", side_effect=change_file):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(OSError):
                    args = SimpleNamespace(folder=self.folder, delete=True)
                    duplicates.run(args)
        self.assertTrue(second.exists())

    def test_empty_files_cancel_and_delete(self):
        blank = self.write("nested/blank.txt", b"")
        full = self.write("full.txt", b"content")
        self.assertEqual(empty.find_empty(self.folder), [blank])
        self.assertEqual(self.invoke("empty", str(self.folder), "--delete")[0], 0)
        self.assertTrue(blank.exists())
        self.assertEqual(
            self.invoke("empty", str(self.folder), "--delete", answer="yes")[0], 0
        )
        self.assertFalse(blank.exists())
        self.assertTrue(full.exists())

    def test_file_filled_during_confirmation_is_kept(self):
        blank = self.write("blank.txt", b"")

        def fill_file(message):
            blank.write_bytes(b"new content")
            return "yes"

        with patch("builtins.input", side_effect=fill_file):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(OSError):
                    args = SimpleNamespace(folder=self.folder, delete=True)
                    empty.run(args)
        self.assertEqual(blank.read_bytes(), b"new content")


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

    def test_batch_download_respects_worker_limit_and_unique_names(self):
        urls = self.folder / "urls.txt"
        urls.write_text(
            "\n# A batch\n"
            + "\n".join(f"{self.base_url}/{number}/file.bin" for number in range(6)),
            encoding="utf-8",
        )
        with DownloadHandler.lock:
            DownloadHandler.maximum = 0
        output = self.folder / "downloads"
        code, text, error = self.invoke(
            "download",
            "--from-file",
            str(urls),
            "--output",
            str(output),
            "--workers",
            "3",
        )
        self.assertEqual(code, 0, error)
        self.assertEqual(len(list(output.iterdir())), 6)
        self.assertLessEqual(DownloadHandler.maximum, 3)
        self.assertGreaterEqual(DownloadHandler.maximum, 2)
        self.assertEqual(len({path.read_bytes() for path in output.iterdir()}), 6)

    def test_failed_download_cleans_partial_file_and_other_jobs_continue(self):
        code, output, error = self.invoke(
            "download",
            self.base_url + "/partial",
            self.base_url + "/good.bin",
            "--output",
            str(self.folder),
        )
        self.assertEqual(code, 1)
        self.assertIn("Failed:", error)
        self.assertFalse((self.folder / "partial").exists())
        self.assertTrue((self.folder / "good.bin").exists())

    def test_http_error_and_unsupported_url(self):
        self.assertEqual(
            self.invoke(
                "download", self.base_url + "/missing", "--output", str(self.folder)
            )[0],
            1,
        )
        self.assertEqual(
            self.invoke(
                "download", "file:///example.txt", "--output", str(self.folder)
            )[0],
            1,
        )
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_http_error_response_is_closed(self):
        with self.assertRaises(HTTPError) as result:
            download_file(self.base_url + "/missing", self.folder)
        self.assertTrue(result.exception.fp.closed)


if __name__ == "__main__":
    unittest.main()
