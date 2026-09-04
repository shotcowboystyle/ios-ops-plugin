#!/usr/bin/env python3
"""Install portable .skill archives into another repository for any agent.

One canonical copy is unpacked under `.agents/skills/<name>/`, an `AGENTS.md`
index makes the set discoverable to every agent that reads that convention, and
thin per-agent pointers are written for the agents that look elsewhere. Sibling
skills are installed as siblings, which is what the packaged `../<skill>/`
links resolve against.

Every write is confined to a managed block or to `.agents/skills`, so repeated
installs converge instead of accumulating.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_bundle import MANIFEST  # noqa: E402

CANONICAL = ".agents/skills"
BEGIN = "<!-- BEGIN ios-skills -->"
END = "<!-- END ios-skills -->"
AGENTS = ("claude", "cursor", "codex", "gemini", "copilot")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, nargs="?", help="Repository to install into")
    parser.add_argument("--dist", type=Path, help="Archive directory (default: repo dist)")
    parser.add_argument("--sets", help="Comma-separated set names from sets.json")
    parser.add_argument("--skills", help="Comma-separated skill names")
    parser.add_argument(
        "--agents",
        default="claude,codex",
        help=f"Comma-separated agent pointers to write from {','.join(AGENTS)} (default: claude,codex)",
    )
    parser.add_argument(
        "--no-symlink",
        action="store_true",
        help="Copy instead of symlinking the Claude Code skill directory",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove previously installed skills that are not in this selection",
    )
    parser.add_argument("--list", action="store_true", help="List available skills and sets, then exit")
    parser.add_argument("--dry-run", action="store_true", help="Report the plan without writing")
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def available(dist: Path) -> dict[str, Path]:
    return {path.stem: path for path in sorted(dist.glob("*.skill"))}


def load_sets(root: Path) -> dict[str, list[str]]:
    path = root / "knowledge-base" / "skills" / "sets.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def expand_set(members: list[str], names: set[str]) -> set[str]:
    selected: set[str] = set()
    for member in members:
        if member.startswith("prefix:"):
            prefix = member.split(":", 1)[1]
            selected |= {name for name in names if name.startswith(prefix)}
        else:
            selected.add(member)
    return selected


def requirements(archive_path: Path) -> list[str]:
    with ZipFile(archive_path) as archive:
        name = archive_path.stem
        try:
            payload = archive.read(f"{name}/{MANIFEST}")
        except KeyError:
            return []
    return json.loads(payload).get("requires_skills", [])


def close_over_requirements(selected: set[str], catalog: dict[str, Path]) -> tuple[set[str], list[str]]:
    """Pull in required sibling skills so packaged `../<skill>/` links resolve."""
    resolved: set[str] = set()
    missing: list[str] = []
    frontier = sorted(selected)
    while frontier:
        name = frontier.pop()
        if name in resolved:
            continue
        if name not in catalog:
            missing.append(name)
            continue
        resolved.add(name)
        frontier.extend(requirements(catalog[name]))
    return resolved, sorted(set(missing))


def unpack(archive_path: Path, destination: Path) -> None:
    name = archive_path.stem
    with ZipFile(archive_path) as archive:
        for member in archive.namelist():
            parts = Path(member).parts
            if member.startswith("/") or ".." in parts or parts[0] != name:
                raise ValueError(f"unsafe archive member {member} in {archive_path}")
    if destination.is_symlink() or destination.is_file():
        destination.unlink()
    elif destination.is_dir():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path) as archive:
        archive.extractall(destination.parent)


def describe(skill_dir: Path) -> tuple[str, str]:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = FRONTMATTER.search(text)
    name, description = skill_dir.name, ""
    if match:
        for line in match.group(1).splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip().strip("\"'")
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip("\"'")
    return name, description


def managed_block(body: str) -> str:
    return f"{BEGIN}\n{body.rstrip()}\n{END}\n"


def write_managed(path: Path, body: str, header: str) -> None:
    """Insert or replace this tool's block, leaving the rest of the file alone."""
    block = managed_block(body)
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if BEGIN in existing and END in existing:
            start = existing.index(BEGIN)
            end = existing.index(END) + len(END) + 1
            updated = existing[:start] + block + existing[end:]
        else:
            updated = existing.rstrip() + "\n\n" + block
    else:
        updated = header.rstrip() + "\n\n" + block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding="utf-8")


def index_body(entries: list[tuple[str, str]]) -> str:
    lines = [
        "## Agent skills",
        "",
        "Read the linked `SKILL.md` before acting on a matching task. Each skill is",
        "self-contained: its references live beside it under `references/`.",
        "",
        "| Skill | Use it when | Path |",
        "| --- | --- | --- |",
    ]
    for name, description in entries:
        lines.append(f"| `{name}` | {description} | `{CANONICAL}/{name}/SKILL.md` |")
    return "\n".join(lines)


def link_claude(target: Path, names: list[str], use_symlink: bool) -> None:
    root = target / ".claude" / "skills"
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        destination = root / name
        source = target / CANONICAL / name
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        elif destination.is_dir():
            shutil.rmtree(destination)
        if use_symlink:
            destination.symlink_to(Path(os.path.relpath(source, root)), target_is_directory=True)
        else:
            shutil.copytree(source, destination)


def remove_skill(target: Path, name: str) -> None:
    """Drop one installed skill and every pointer written for it."""
    for path in (
        target / CANONICAL / name,
        target / ".claude" / "skills" / name,
        target / ".cursor" / "rules" / f"{name}.mdc",
    ):
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)


def link_cursor(target: Path, entries: list[tuple[str, str]]) -> None:
    root = target / ".cursor" / "rules"
    root.mkdir(parents=True, exist_ok=True)
    for name, description in entries:
        body = (
            "---\n"
            f"description: {description}\n"
            "alwaysApply: false\n"
            "---\n\n"
            f"Follow @{CANONICAL}/{name}/SKILL.md for this work.\n"
        )
        (root / f"{name}.mdc").write_text(body, encoding="utf-8")


def main() -> int:
    args = parse_args()
    root = repo_root()
    dist = (args.dist or root / "knowledge-base" / "skills" / "dist").resolve()
    catalog = available(dist)
    sets = load_sets(root)

    if args.list:
        print("sets:")
        for name, members in sorted(sets.items()):
            print(f"  {name}: {len(expand_set(members, set(catalog)))} skills")
        print("skills:")
        for name in sorted(catalog):
            print(f"  {name}")
        return 0

    if args.target is None:
        print("ERROR target repository is required unless --list is used")
        return 2
    if not catalog:
        print(f"ERROR no .skill archives in {dist}; run scripts/package_skills.py first")
        return 1

    selected: set[str] = set()
    for name in filter(None, (args.sets or "").split(",")):
        if name not in sets:
            print(f"ERROR unknown set {name}")
            return 2
        selected |= expand_set(sets[name], set(catalog))
    selected |= {name for name in filter(None, (args.skills or "").split(","))}
    if not selected:
        print("ERROR select skills with --sets and/or --skills (see --list)")
        return 2

    names_set, missing = close_over_requirements(selected, catalog)
    if missing:
        for name in missing:
            print(f"ERROR unknown skill {name}")
        return 2
    names = sorted(names_set)
    agents = [name.strip() for name in args.agents.split(",") if name.strip()]
    unknown_agents = [name for name in agents if name not in AGENTS]
    if unknown_agents:
        print(f"ERROR unknown agent(s) {unknown_agents}; choose from {list(AGENTS)}")
        return 2

    target = args.target.resolve()
    pulled = sorted(names_set - selected)
    if pulled:
        print(f"REQUIRED_SIBLINGS added={','.join(pulled)}")
    if args.dry_run:
        print(f"PLAN target={target} skills={len(names)} agents={','.join(agents)}")
        for name in names:
            print(f"  install {CANONICAL}/{name}")
        return 0

    if not target.is_dir():
        print(f"ERROR target {target} is not a directory")
        return 1

    if args.prune:
        installed = target / CANONICAL
        stale = sorted(
            path.name
            for path in (installed.iterdir() if installed.is_dir() else [])
            if path.is_dir() and path.name not in names_set
        )
        for name in stale:
            remove_skill(target, name)
        if stale:
            print(f"PRUNED skills={','.join(stale)}")

    for name in names:
        unpack(catalog[name], target / CANONICAL / name)
    entries = [describe(target / CANONICAL / name) for name in names]

    write_managed(
        target / "AGENTS.md",
        index_body(entries),
        "# Agent instructions\n",
    )
    if "claude" in agents:
        link_claude(target, names, use_symlink=not args.no_symlink)
    if "cursor" in agents:
        link_cursor(target, entries)
    if "gemini" in agents:
        write_managed(
            target / "GEMINI.md",
            f"Agent skills for this repository are indexed in `AGENTS.md` and stored under `{CANONICAL}/`.",
            "# Gemini instructions\n",
        )
    if "copilot" in agents:
        write_managed(
            target / ".github" / "copilot-instructions.md",
            f"Agent skills for this repository are indexed in `AGENTS.md` and stored under `{CANONICAL}/`.",
            "# Copilot instructions\n",
        )

    print(f"INSTALL_OK target={target} skills={len(names)} agents={','.join(agents)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
