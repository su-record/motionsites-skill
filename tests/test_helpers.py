import contextlib
import functools
import http.server
import importlib.util
import io
import json
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "motionsites-web-builder"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shoot = load_script("shoot")
resources = load_script("fetch_resources")


class ScreenshotArguments(unittest.TestCase):
    def test_flags_do_not_replace_optional_output_directory(self):
        args = shoot.parse_args(["page.html", "--wait", "0.25", "--full"])
        self.assertEqual(args.out_dir, Path("shots"))
        self.assertEqual(args.wait, 0.25)
        self.assertTrue(args.full)
        args = shoot.parse_args(["page.html", "output with spaces", "--wait", "0"])
        self.assertEqual(args.out_dir, Path("output with spaces"))

    def test_invalid_wait_is_rejected(self):
        for value in ["-1", "nan", "inf", "not-a-number"]:
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    shoot.parse_args(["page.html", "--wait", value])

    def test_missing_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "shots"
            with contextlib.redirect_stderr(io.StringIO()):
                result = shoot.main([str(Path(temporary) / "missing.html"), str(output)])
            self.assertEqual(result, 1)
            self.assertFalse(output.exists())


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class ScreenshotBehavior(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="motionsites browser ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_file_with_spaces_and_changed_input(self):
        page = self.root / "page with spaces.html"
        page.write_text('''<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Local fixture</title><style>html,body{margin:0;background:#153020;color:white}
main{min-height:1600px;padding:24px;box-sizing:border-box}</style>
</head><body><main><h1>First input</h1></main></body></html>''')
        output = self.root / "shots with spaces"
        result = subprocess.run(
            [sys.executable, str(SKILL / "scripts/shoot.py"), str(page), str(output),
             "--wait", "0", "--full"], capture_output=True, text=True, cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((output / "qa.json").read_text())
        self.assertEqual(report["desktop"]["h1"]["text"], "First input")
        self.assertFalse(report["mobile"]["horizontalOverflow"])
        self.assertEqual(report["desktop"]["consoleErrors"], [])
        expected = {"desktop.png": (1440, 1600), "mobile.png": (390, 1600),
                    "desktop-early.png": (1440, 900)}
        for filename, dimensions in expected.items():
            header = (output / filename).read_bytes()[:24]
            self.assertEqual(header[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", header[16:24]), dimensions)
        page.write_text("<!doctype html><title>Changed</title><h1>Second input</h1>")
        changed = shoot.shoot(shoot.target_url(str(page)), output, wait=0)
        self.assertEqual(changed["desktop"]["h1"]["text"], "Second input")
        self.assertEqual(json.loads((output / "qa.json").read_text()), changed)

    def test_http_broken_assets_console_error_overflow_and_failed_navigation(self):
        (self.root / "broken.html").write_text('''<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Broken</title>
<style>main{width:2200px}</style></head><body><main><h1>Broken fixture</h1>
<img src="/missing.svg" alt="missing"><video src="/missing.mp4"></video></main>
<script>console.error('fixture error')</script></body></html>''')
        handler = functools.partial(QuietHandler, directory=str(self.root))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        report = shoot.shoot(base + "/broken.html", self.root / "broken shots", wait=0)
        self.assertTrue(report["mobile"]["horizontalOverflow"])
        self.assertIn(base + "/missing.svg", report["desktop"]["brokenImages"])
        self.assertIn("fixture error", report["desktop"]["consoleErrors"])
        self.assertTrue(any("HTTP 404" in item for item in report["desktop"]["failedRequests"]))
        self.assertEqual(len(report["desktop"]["videos"]), 1)
        output = self.root / "broken shots"
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            shoot.shoot(base + "/nonexistent.html", output, wait=0)
        self.assertFalse((output / "qa.json").exists())
        self.assertFalse((output / "desktop.png").exists())


class ResourceFetch(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="motionsites resources ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        resources.git(self.upstream, "init", "--quiet")
        resources.git(self.upstream, "config", "user.email", "fixture@example.invalid")
        resources.git(self.upstream, "config", "user.name", "Fixture")
        skill = self.upstream / "skills" / "fixture"
        for folder, filename in [("examples", "INDEX.md"), ("media", "MEDIA.md")]:
            (skill / folder).mkdir(parents=True)
            (skill / folder / filename).write_text(f"original {folder}\n")
        (self.upstream / "LICENSE").write_text("Fixture restricted resource terms\n")
        (self.upstream / "not-for-copying.py").write_text("raise RuntimeError('not executed')")
        resources.git(self.upstream, "add", ".")
        resources.git(self.upstream, "commit", "--quiet", "-m", "fixture")
        self.source = {"repository": self.upstream.as_uri(),
                       "commit": resources.git(self.upstream, "rev-parse", "HEAD"),
                       "skill_path": "skills/fixture"}

    def test_pinned_download_retry_and_source_preservation(self):
        destination = self.root / "cache"
        result = resources.fetch_resources(destination, self.source)
        self.assertEqual((result / "examples/INDEX.md").read_text(), "original examples\n")
        self.assertEqual((result / "UPSTREAM_LICENSE").read_text(),
                         "Fixture restricted resource terms\n")
        self.assertFalse((result / "not-for-copying.py").exists())
        self.assertTrue((self.upstream / "not-for-copying.py").is_file())
        (self.upstream / "skills/fixture/examples/INDEX.md").write_text("new upstream")
        resources.git(self.upstream, "add", ".")
        resources.git(self.upstream, "commit", "--quiet", "-m", "new upstream")
        fresh = resources.fetch_resources(self.root / "fresh", self.source)
        self.assertEqual((fresh / "examples/INDEX.md").read_text(), "original examples\n")
        self.assertEqual(resources.fetch_resources(destination, self.source), destination)

    def test_failure_has_no_partial_destination_and_retry_succeeds(self):
        destination = self.root / "retry"
        invalid = dict(self.source, commit="0" * 40)
        with self.assertRaises(RuntimeError):
            resources.fetch_resources(destination, invalid)
        self.assertFalse(destination.exists())
        self.assertEqual(list(self.root.glob(".motionsites-fetch-*")), [])
        resources.fetch_resources(destination, self.source)
        self.assertTrue((destination / "media/MEDIA.md").is_file())

    def test_existing_user_data_and_incomplete_cache_are_preserved(self):
        destination = self.root / "existing"
        destination.mkdir()
        personal = destination / "my-file.txt"
        personal.write_text("keep me")
        with self.assertRaisesRegex(RuntimeError, "Preserving existing"):
            resources.fetch_resources(destination, self.source)
        self.assertEqual(personal.read_text(), "keep me")
        cached = resources.fetch_resources(self.root / "cached", self.source)
        (cached / "examples/INDEX.md").unlink()
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            resources.fetch_resources(cached, self.source)
        self.assertTrue((cached / "media/MEDIA.md").exists())


if __name__ == "__main__":
    unittest.main()
