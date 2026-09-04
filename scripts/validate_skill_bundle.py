#!/usr/bin/env python3
"""Validate workspace skill packages and, optionally, their portable archives.

The repository intentionally keeps the package contract small and observable:
each package has a valid entrypoint, a risk-proportional fast path, discoverable
local references, and a matching archive when archive checks are requested.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_bundle import (  # noqa: E402
    DEFAULT_UPSTREAM,
    MANIFEST,
    build_stage,
    is_external,
    link_targets,
    split_target,
)


PACKAGE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
REQUIRED_HEADINGS = {
    "read": re.compile(r"^##\s+Read before acting\s*$", re.MULTILINE),
    "fast": re.compile(r"^##\s+Fast path\s*$", re.MULTILINE),
    "sources": re.compile(r"^##\s+Sources\s*$", re.MULTILINE),
    "output": re.compile(
        r"^##\s+(?:Required output|Required handoff|Deliverable|Completion evidence|Evidence report|Evidence report shape|Route deliverable|Handoff format|Output contract|Architecture and proof contract)\s*$",
        re.MULTILINE,
    ),
    "boundary": re.compile(
        r"^##\s+(?:Hard boundaries|Non-negotiable safety and evidence rules|Non-negotiable communication rules|Refuse to assume|Change boundary)\s*$",
        re.MULTILINE,
    ),
}
PLACEHOLDER = re.compile(
    r"(?:<skill-name>|<description>|TODO|FIXME|replace me|your description|your skill)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path("."),
        help="Repository root (default: current directory)",
    )
    parser.add_argument(
        "--check-archives",
        action="store_true",
        help="Also require dist/<package>.skill archives to match package contents",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON receipt")
    parser.add_argument(
        "--upstream",
        default=DEFAULT_UPSTREAM,
        help="Base URL used when packaging documents that are not vendored",
    )
    return parser.parse_args()


def read_frontmatter(text: str) -> dict[str, str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def validate_package(package_dir: Path, repo_root: Path) -> list[str]:
    errors: list[str] = []
    package_name = package_dir.name
    skill_path = package_dir / "SKILL.md"
    if not PACKAGE_NAME.fullmatch(package_name):
        errors.append(f"{package_name}: invalid package directory name")
    if not skill_path.is_file():
        return [f"{package_name}: missing SKILL.md"]

    text = skill_path.read_text(encoding="utf-8")
    frontmatter = read_frontmatter(text)
    if frontmatter is None:
        errors.append(f"{package_name}: missing or malformed YAML frontmatter")
    else:
        if frontmatter.get("name") != package_name:
            errors.append(
                f"{package_name}: frontmatter name is {frontmatter.get('name')!r}"
            )
        if not frontmatter.get("description"):
            errors.append(f"{package_name}: frontmatter description is empty")

    for label, pattern in REQUIRED_HEADINGS.items():
        if not pattern.search(text):
            errors.append(f"{package_name}: missing required {label} section")
    if text.count("```") % 2:
        errors.append(f"{package_name}: unbalanced fenced code blocks")
    if PLACEHOLDER.search(text):
        errors.append(f"{package_name}: unfinished scaffold placeholder")

    for raw_target in link_targets(text):
        target, _ = split_target(raw_target)
        if is_external(target):
            continue
        target_path = (skill_path.parent / target).resolve()
        if not target_path.exists():
            errors.append(f"{package_name}: broken local link {raw_target}")
        try:
            target_path.relative_to(repo_root.resolve())
        except ValueError:
            errors.append(f"{package_name}: local link escapes repository {raw_target}")

    return errors


def archive_link_errors(package_name: str, files: dict[str, bytes], known: set[str]) -> list[str]:
    """Every link in an installed archive must resolve without the repository.

    Allowed destinations are external URLs, paths inside the archive, and
    `../<sibling>/...` paths that resolve in an install tree where skills are
    installed as siblings.
    """
    errors: list[str] = []
    present = set(files)
    directories = {
        str(parent)
        for name in present
        for parent in PurePosixPath(name).parents
        if str(parent) != "."
    }
    for name, payload in sorted(files.items()):
        if not name.endswith(".md"):
            continue
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"{package_name}: {name} is not valid UTF-8")
            continue
        here = PurePosixPath(name).parent
        for raw_target in link_targets(text):
            target, _ = split_target(raw_target)
            if is_external(target):
                continue
            resolved = PurePosixPath(os.path.normpath(str(here / target)))
            parts = resolved.parts
            if parts and parts[0] == "..":
                if len(parts) >= 3 and parts[0] == ".." and parts[1] in known:
                    continue
                errors.append(f"{package_name}: {name} escapes the archive: {raw_target}")
                continue
            if str(resolved) in present or str(resolved) in directories:
                continue
            errors.append(f"{package_name}: {name} has dangling link {raw_target}")
    return errors


def validate_archive(
    package_dir: Path, archive_path: Path, repo_root: Path, known: set[str], upstream: str
) -> list[str]:
    package_name = package_dir.name
    if not archive_path.is_file():
        return [f"{package_name}: missing archive {archive_path}"]
    stage = build_stage(package_dir, repo_root, upstream)
    errors = list(stage.errors)
    try:
        with ZipFile(archive_path) as archive:
            names = archive.namelist()
            expected = {f"{package_name}/{relative}" for relative in stage.files}
            actual = set(names)
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            if missing:
                errors.append(f"{package_name}: archive missing {missing}")
            if extra:
                errors.append(f"{package_name}: archive has unexpected {extra}")
            for name in names:
                if name.startswith("/") or ".." in PurePosixPath(name).parts:
                    errors.append(f"{package_name}: unsafe archive path {name}")
            for relative, payload in stage.files.items():
                archive_name = f"{package_name}/{relative}"
                if archive_name in actual and archive.read(archive_name) != payload:
                    errors.append(f"{package_name}: archive content drift for {relative}")
    except (BadZipFile, OSError, ValueError) as exc:
        return errors + [f"{package_name}: invalid archive: {exc}"]
    errors.extend(archive_link_errors(package_name, stage.files, known))
    if MANIFEST not in stage.files:
        errors.append(f"{package_name}: archive is missing {MANIFEST}")
    for sibling in sorted(stage.siblings):
        if sibling not in known:
            errors.append(f"{package_name}: requires unknown skill {sibling}")
    return errors


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    packages_root = root / "knowledge-base" / "skills" / "packages"
    package_dirs = sorted(
        path for path in packages_root.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
    ) if packages_root.is_dir() else []

    errors: list[str] = []
    for package_dir in package_dirs:
        errors.extend(validate_package(package_dir, root))
    if args.check_archives:
        dist_root = root / "knowledge-base" / "skills" / "dist"
        known = {package_dir.name for package_dir in package_dirs}
        for package_dir in package_dirs:
            errors.extend(
                validate_archive(
                    package_dir,
                    dist_root / f"{package_dir.name}.skill",
                    root,
                    known,
                    args.upstream,
                )
            )
        if dist_root.is_dir():
            expected_archives = {f"{package_dir.name}.skill" for package_dir in package_dirs}
            for archive_path in sorted(dist_root.glob("*.skill")):
                if archive_path.name not in expected_archives:
                    errors.append(f"unexpected archive {archive_path}")

    receipt = {
        "packages": len(package_dirs),
        "archives_checked": args.check_archives,
        "errors": errors,
        "status": "ok" if not errors else "failed",
    }
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"ERROR {error}")
        print(f"SKILL_BUNDLE_FAILED packages={len(package_dirs)} errors={len(errors)}")
    else:
        archive_text = " archives=checked" if args.check_archives else ""
        print(f"SKILL_BUNDLE_OK packages={len(package_dirs)}{archive_text}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
