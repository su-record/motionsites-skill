import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/motionsites-web-builder"
spec = importlib.util.spec_from_file_location("build_release", ROOT / "scripts/build_release.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class Distribution(unittest.TestCase):
    def test_shared_skill_and_plugin_reference_the_same_name(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        entry = marketplace["plugins"][0]
        plugin_root = (ROOT / entry["source"]).resolve()
        self.assertEqual(plugin_root, ROOT)
        self.assertEqual(entry["name"], plugin["name"])
        self.assertTrue((plugin_root / "skills" / plugin["name"] / "SKILL.md").is_file())

    def test_document_links_resolve_inside_distributed_skill(self):
        for document in SKILL.rglob("*.md"):
            for target in re.findall(r"\]\(([^\s)]+)\)", document.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                path = (document.parent / target.split("#", 1)[0]).resolve()
                with self.subTest(document=document.name, target=target):
                    self.assertTrue(path.is_relative_to(SKILL))
                    self.assertTrue(path.exists(), str(path))

    def test_zip_extracts_with_license_scripts_and_references_without_collections(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            manifest = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
            archive = builder.build_release(SKILL, output, manifest["version"])
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertIn(f"{SKILL.name}/SKILL.md", names)
                self.assertIn(f"{SKILL.name}/LICENSE", names)
                self.assertIn(f"{SKILL.name}/references/upstream.json", names)
                for name in names:
                    parts = Path(name).parts
                    self.assertNotIn("examples", parts)
                    self.assertNotIn("media", parts)
                    self.assertNotIn(".resources", parts)
                    self.assertNotIn("__pycache__", parts)
                    self.assertEqual(parts[0], SKILL.name)
                bundle.extractall(output / "extracted")
            extracted = output / "extracted" / SKILL.name
            for filename in ["shoot.py", "fetch_resources.py"]:
                result = subprocess.run(
                    [sys.executable, str(extracted / "scripts" / filename), "--help"],
                    capture_output=True, text=True, cwd=output,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((extracted / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())


if __name__ == "__main__":
    unittest.main()
