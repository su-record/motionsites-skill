# MotionSites Web Builder for Claude Code and Codex

A shared Agent Skill for cinematic landing pages, hero sections, and visual
website improvements. It combines MotionSites' MIT-licensed design references
with a precise build spec and a screenshot-and-fix workflow.

**One skill, both tools.** Claude Code and Codex read the same `SKILL.md`,
references, and Python helpers. This is a community adaptation of
[Motionsites-AI/claude-skill](https://github.com/Motionsites-AI/claude-skill),
with no mandatory advertising.

## Install in Codex

Ask Codex:

```text
$skill-installer install the skill from https://github.com/su-record/motionsites-skill/tree/main/skills/motionsites-web-builder
```

Or clone this repository and copy `skills/motionsites-web-builder` into your
project's `.agents/skills/` or your personal `~/.agents/skills/` directory.
Keep the entire skill folder, including its license and supporting files.
Avoid overwriting an existing skill with the same name. If it does not appear,
restart Codex.

Invoke it with:

```text
$motionsites-web-builder Build a calm, cinematic landing page for my architecture studio.
```

## Install in Claude Code

Add this repository as a plugin marketplace and install its plugin:

```text
/plugin marketplace add su-record/motionsites-skill
/plugin install motionsites-web-builder@su-record-motionsites
```

The plugin command is namespaced:

```text
/motionsites-web-builder:motionsites-web-builder Build a cinematic landing page for my architecture studio.
```

For a manual installation, copy `skills/motionsites-web-builder` into your
project's `.claude/skills/` or your personal `~/.claude/skills/` directory.
Then use `/motionsites-web-builder`. Both hosts can also select the skill
automatically when the request matches its description.

For local plugin testing, run `claude --plugin-dir /absolute/path/to/motionsites-skill`.

## What it does

- Establish an audience, mood, and one visual signature.
- Select relevant composition, typography, motion, and interaction recipes.
- Write a concrete spec and build in the user's existing stack.
- Inspect desktop and mobile screenshots, fix defects, and report actual checks.
- Write a builder prompt without creating a page when that is the requested output.

Try requests such as:

```text
Improve this page's typography and mobile layout while preserving its design system.
Build a standalone hero for a luxury sleep-tracking ring using my product photo.
Write a v0 prompt for a restrained editorial portfolio. Do not build the page.
```

## Screenshots

Prefer the browser and screenshot tools already available in your host. The
bundled helper requires Python 3.10+ and Playwright; it has no model/API cost.
Set up an environment if you need it:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install chromium
```

Set `SKILL_DIR` to the installed folder containing `SKILL.md`, then run this
from the website project directory:

```bash
.venv/bin/python "$SKILL_DIR/scripts/shoot.py" index.html shots/ --wait 2.5 --full
# A running app is also supported:
.venv/bin/python "$SKILL_DIR/scripts/shoot.py" http://localhost:5173 shots/
```

On Windows, use `.venv\Scripts\python.exe`. If the browser reports missing system
libraries, use Playwright's documented browser dependency setup for your OS.
The helper tries installed Google Chrome before Playwright Chromium. Video
codec support depends on the selected browser and OS; inspect the report.

Outputs are `desktop.png`, `mobile.png`, `desktop-early.png`, and `qa.json`.
The report includes failed assets, console errors, horizontal overflow, fonts,
and video state. Inspect the images; producing a report does not certify a design.

## Optional original examples and media

The original prompt/media collections are **not included** because their
license prohibits redistribution as collections. The bundled references are
enough to use the skill with your own assets.

For local use of the original library, run:

```bash
python3 "$SKILL_DIR/scripts/fetch_resources.py"
```

This requires Git and network access. It fetches the pinned upstream commit into
a temporary checkout and copies the resource folders into a user cache, whose
absolute path it prints. It does not execute upstream code. Read the included
`UPSTREAM_LICENSE` before use. Keep that cache out of published repositories
and ZIPs. Details: [resources.md](skills/motionsites-web-builder/references/resources.md).

## Development and verification

Install Playwright and its Chromium browser as above, then run:

```bash
python3 -m unittest discover -s tests -v
claude plugin validate .
python3 scripts/build_release.py
```

Use your environment's Python for the test command. Browser tests require
Playwright and a working browser and fail if they are unavailable. The tests
exercise CLI parsing, paths containing spaces, good/broken pages, resource
fetch failure and retry, and ZIP contents. They do not evaluate an AI model's
design quality or guarantee that every host UI will install the package.

The release ZIP is suitable for hosts accepting uploaded Agent Skills. Actual
Claude web/desktop upload behavior is not covered by the local checks.

## License and provenance

The included instructions, references, and scripts are MIT-licensed. Preserve
the MotionSites and su-record copyright notices when redistributing them.
Original examples and media have separate terms and remain excluded.
See [LICENSE](LICENSE), [NOTICE.md](NOTICE.md), and [UPSTREAM_LICENSE](UPSTREAM_LICENSE).

Host documentation: [Codex skills](https://learn.chatgpt.com/docs/build-skills)
and [Claude Code skills](https://code.claude.com/docs/en/skills).
