#!/usr/bin/env python3
"""Build deterministic, self-contained .skill archives from workspace packages.

Packages are authored against this repository and link out into the knowledge
base. Packaging rewrites those links and vendors the referenced documents so an
installed archive resolves every reference on its own. See `skill_bundle` for
the link contract.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from skill_bundle import DEFAULT_UPSTREAM, Stage, build_stage  # noqa: E402


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
        "--output",
        type=Path,
        help="Archive directory (default: knowledge-base/skills/dist)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove stale .skill files from the output directory",
    )
    parser.add_argument(
        "--upstream",
        default=DEFAULT_UPSTREAM,
        help="Base URL for repository documents that are not vendored",
    )
    return parser.parse_args()


def write_archive(stage: Stage, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{stage.name}.", suffix=".tmp", dir=output_path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for relative, payload in stage.files.items():
                info = ZipInfo(f"{stage.name}/{relative}", date_time=(2020, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o644 << 16
                archive.writestr(info, payload)
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return len(stage.files)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    packages_root = root / "knowledge-base" / "skills" / "packages"
    output = (args.output or root / "knowledge-base" / "skills" / "dist").resolve()
    package_dirs = sorted(
        path for path in packages_root.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()
    ) if packages_root.is_dir() else []
    output.mkdir(parents=True, exist_ok=True)

    expected = {f"{path.name}.skill" for path in package_dirs}
    if args.prune:
        for stale in sorted(output.glob("*.skill")):
            if stale.name not in expected:
                stale.unlink()

    total_files = 0
    total_vendored = 0
    errors: list[str] = []
    for package_dir in package_dirs:
        stage = build_stage(package_dir, root, args.upstream)
        errors.extend(stage.errors)
        count = write_archive(stage, output / f"{package_dir.name}.skill")
        total_files += count
        total_vendored += len(stage.vendored)
        print(
            f"PACKAGED {stage.name} files={count} vendored={len(stage.vendored)} "
            f"requires={len(stage.siblings)}"
        )
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        print(f"PACKAGE_BUILD_FAILED packages={len(package_dirs)} errors={len(errors)}")
        return 1
    print(
        f"PACKAGE_BUILD_OK packages={len(package_dirs)} files={total_files} "
        f"vendored={total_vendored} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
