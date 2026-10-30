"""Build an uploadable skill ZIP containing only the distributed MIT files."""

import argparse
import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ENTRIES = ("SKILL.md", "LICENSE", "agents", "references", "scripts")
FILE_SUFFIXES = {".md", ".json", ".yaml", ".py"}


def build_release(skill, output, version):
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"{skill.name}-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for entry in SKILL_ENTRIES:
            path = skill / entry
            files = [path] if path.is_file() else sorted(path.rglob("*"))
            for file in files:
                if file.is_symlink():
                    raise ValueError(f"Refusing to package symlink: {file}")
                if not file.is_file() or "__pycache__" in file.parts:
                    continue
                if file.name == "LICENSE" or file.suffix in FILE_SUFFIXES:
                    bundle.write(file, file.relative_to(skill.parent))
    return archive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "dist")
    args = parser.parse_args(argv)
    manifest = json.loads((REPO_ROOT / ".claude-plugin/plugin.json").read_text())
    skill = REPO_ROOT / "skills" / manifest["name"]
    print(build_release(skill, args.output_dir, manifest["version"]))


if __name__ == "__main__":
    main()
