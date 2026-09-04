#!/usr/bin/env python3
"""Shared link classification and rewriting for portable skill packages.

A workspace package is authored against the repository: its `SKILL.md` links to
knowledge-base documents with paths such as `../../../00-foundations/03-x.md`.
Those paths only resolve inside this repository, so a naively zipped archive
ships broken references. This module defines the single link contract used by
the packager, the validator, and the installer.

Link routes, decided by the resolved repository-relative target:

- inside the package             -> keep the link untouched
- another package under packages -> `../<sibling>/...` (resolves in an install
                                    tree where sibling skills are siblings)
- under knowledge-base, not under knowledge-base/skills
                                 -> vendor into `references/kb/<kb-relative>`
- anything else in the repository -> absolute upstream URL

Vendoring is depth-1 on purpose: the knowledge base cross-links so densely that
the transitive closure of any single skill is the entire corpus.
"""

from __future__ import annotations

import json
import posixpath
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

KNOWLEDGE_BASE = "knowledge-base"
PACKAGES_ROOT = "knowledge-base/skills/packages"
VENDOR_ROOT = "references/kb"
DEFAULT_UPSTREAM = "https://github.com/shotcowboystyle/ios-ops-plugin/blob/main/"

# Markdown inline links and images: the capture group is the destination.
LINK = re.compile(r"(!?\[[^\]]*\]\()([^)\s]+)((?:\s+\"[^\"]*\")?\))")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)

KEEP = "keep"
SIBLING = "sibling"
VENDOR = "vendor"
UPSTREAM = "upstream"


@dataclass
class Rewrite:
    """Result of rewriting one file's links."""

    text: str
    vendored: set[str] = field(default_factory=set)  # knowledge-base-relative
    siblings: set[str] = field(default_factory=set)  # sibling package names


def split_target(raw: str) -> tuple[str, str]:
    """Split a link destination into its path and its `#fragment`/`?query` tail."""
    target = raw.strip().strip("<>")
    for marker in ("#", "?"):
        index = target.find(marker)
        if index >= 0:
            return target[:index], target[index:]
    return target, ""


def link_targets(text: str) -> list[str]:
    """Every markdown link and image destination in `text`, titles stripped.

    One parser is shared by the packager, the validator, and any caller, so a
    link can never be rewritten under one grammar and checked under another.
    """
    return [match.group(2) for match in LINK.finditer(text)]


def is_external(target: str) -> bool:
    return not target or bool(EXTERNAL.match(target)) or "\x00" in target


def classify(repo_relative: PurePosixPath, package_name: str) -> tuple[str, str]:
    """Route a repository-relative target. Returns `(route, detail)`.

    `detail` is the sibling package name for SIBLING, the knowledge-base-relative
    path for VENDOR, and the repository-relative path otherwise.
    """
    parts = repo_relative.parts
    package_parts = PurePosixPath(PACKAGES_ROOT).parts
    if parts[: len(package_parts)] == package_parts and len(parts) > len(package_parts):
        owner = parts[len(package_parts)]
        if owner == package_name:
            return KEEP, str(repo_relative)
        return SIBLING, owner
    if parts and parts[0] == KNOWLEDGE_BASE and not str(repo_relative).startswith(
        f"{KNOWLEDGE_BASE}/skills/"
    ):
        return VENDOR, str(PurePosixPath(*parts[1:]))
    return UPSTREAM, str(repo_relative)


def resolve(source: Path, target: str, repo_root: Path) -> PurePosixPath | None:
    """Resolve a link relative to `source`, returning a repository-relative path.

    Directory targets resolve too: packages link to asset folders as a unit.
    """
    try:
        resolved = (source.parent / target).resolve()
    except (OSError, ValueError):
        return None
    if not resolved.exists():
        return None
    try:
        return PurePosixPath(resolved.relative_to(repo_root.resolve()).as_posix())
    except ValueError:
        return None


def _relative(from_dir: PurePosixPath, to_path: PurePosixPath) -> str:
    """POSIX relative path from a package-relative directory to a target path."""
    return posixpath.relpath(str(to_path), str(from_dir) if from_dir.parts else ".")


def rewrite_package_file(
    source: Path,
    package_dir: Path,
    repo_root: Path,
    upstream: str,
    errors: list[str] | None = None,
) -> Rewrite:
    """Rewrite links in a file that ships inside the package itself."""
    package_name = package_dir.name
    package_relative = PurePosixPath(source.relative_to(package_dir).as_posix()).parent
    result = Rewrite(text="")

    def replace(match: re.Match[str]) -> str:
        raw = match.group(2)
        target, tail = split_target(raw)
        if is_external(target):
            return match.group(0)
        repo_relative = resolve(source, target, repo_root)
        if repo_relative is None:
            if errors is not None:
                errors.append(f"{package_name}: unresolvable link {raw} in {source.name}")
            return match.group(0)
        route, detail = classify(repo_relative, package_name)
        if route == KEEP:
            return match.group(0)
        if route == SIBLING:
            result.siblings.add(detail)
            inside = PurePosixPath(*repo_relative.parts[len(PurePosixPath(PACKAGES_ROOT).parts) + 1 :])
            new = _relative(package_relative, PurePosixPath("..") / detail / inside)
            return f"{match.group(1)}{new}{tail}{match.group(3)}"
        if route == VENDOR:
            result.vendored.add(detail)
            new = _relative(package_relative, PurePosixPath(VENDOR_ROOT) / detail)
            return f"{match.group(1)}{new}{tail}{match.group(3)}"
        return f"{match.group(1)}{upstream}{detail}{tail}{match.group(3)}"

    result.text = LINK.sub(replace, source.read_text(encoding="utf-8"))
    return result


def rewrite_vendored_file(
    kb_relative: str,
    text: str,
    origin: Path,
    repo_root: Path,
    vendored: set[str],
    upstream: str,
) -> str:
    """Rewrite links in a vendored knowledge-base document.

    Links are resolved against the document's original location. Targets that are
    also vendored become archive-relative; every other repository target becomes
    an upstream URL, because vendoring is deliberately depth-1.
    """
    here = PurePosixPath(VENDOR_ROOT, kb_relative).parent

    def replace(match: re.Match[str]) -> str:
        raw = match.group(2)
        target, tail = split_target(raw)
        if is_external(target):
            return match.group(0)
        repo_relative = resolve(origin, target, repo_root)
        if repo_relative is None:
            return match.group(0)
        route, detail = classify(repo_relative, package_name="")
        if route == VENDOR and detail in vendored:
            new = _relative(here, PurePosixPath(VENDOR_ROOT) / detail)
            return f"{match.group(1)}{new}{tail}{match.group(3)}"
        return f"{match.group(1)}{upstream}{repo_relative}{tail}{match.group(3)}"

    return LINK.sub(replace, text)


SKIP_NAMES = {".DS_Store"}
MANIFEST = "SKILL-MANIFEST.json"


@dataclass
class Stage:
    """A package rendered into the exact file set its archive ships."""

    name: str
    files: dict[str, bytes] = field(default_factory=dict)  # archive-relative -> bytes
    siblings: set[str] = field(default_factory=set)
    vendored: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)


def package_sources(package_dir: Path) -> list[Path]:
    """Authored files of a package, in deterministic order."""
    paths: list[Path] = []
    for path in sorted(package_dir.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symbolic link is not portable: {path}")
        if not path.is_file() or path.name in SKIP_NAMES or "__pycache__" in path.parts:
            continue
        if path.suffix == ".pyc":
            continue
        paths.append(path)
    return paths


def build_stage(package_dir: Path, repo_root: Path, upstream: str = DEFAULT_UPSTREAM) -> Stage:
    """Render a package into a self-contained file set.

    Markdown is rewritten through the link contract, every vendored
    knowledge-base document is copied under `references/kb/`, and a manifest
    records the sibling skills the package expects to be installed alongside it.
    """
    stage = Stage(name=package_dir.name)
    knowledge_root = repo_root / KNOWLEDGE_BASE
    rewritten: dict[str, str] = {}

    for source in package_sources(package_dir):
        relative = source.relative_to(package_dir).as_posix()
        if relative == MANIFEST:
            continue  # regenerated below; never carried over from a stale build
        if source.suffix != ".md":
            stage.files[relative] = source.read_bytes()
            continue
        result = rewrite_package_file(source, package_dir, repo_root, upstream, stage.errors)
        rewritten[relative] = result.text
        stage.vendored |= result.vendored
        stage.siblings |= result.siblings

    for kb_relative in sorted(stage.vendored):
        origin = knowledge_root / kb_relative
        archive_path = f"{VENDOR_ROOT}/{kb_relative}"
        if origin.is_dir():
            for member in sorted(origin.rglob("*")):
                if not member.is_file() or member.name in SKIP_NAMES:
                    continue
                inside = member.relative_to(origin).as_posix()
                stage.files[f"{archive_path}/{inside}"] = member.read_bytes()
            continue
        if origin.suffix == ".md":
            text = rewrite_vendored_file(
                kb_relative,
                origin.read_text(encoding="utf-8"),
                origin,
                repo_root,
                stage.vendored,
                upstream,
            )
            stage.files[archive_path] = text.encode("utf-8")
        else:
            stage.files[archive_path] = origin.read_bytes()

    for relative, text in rewritten.items():
        stage.files[relative] = text.encode("utf-8")

    manifest = {
        "name": stage.name,
        "requires_skills": sorted(stage.siblings),
        "vendored_documents": sorted(stage.vendored),
        "upstream": upstream,
    }
    stage.files[MANIFEST] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    stage.files = dict(sorted(stage.files.items()))
    return stage
