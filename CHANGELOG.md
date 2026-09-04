# Changelog

All notable changes to this repository will be documented here.

## Unreleased

### Removed

- `docs/x-launch-kit.md` and its README entry points;
- six knowledge-base documents that no index, route, or skill referenced:
  four `60-verification` proof matrices (rich text and text renderer, media capture and audio,
  camera control and lock screen, screen capture and broadcast),
  `70-code-recipes/56-network-extension-and-connectivity-recipes.md`, and
  `sources/source-freshness-log.md`.

### Fixed

- archive validation now checks that every link resolves inside the installed archive;
  packaged archives previously shipped 773 repository-relative links that broke on install.

### Added

- self-contained skill archives: knowledge-base documents a package links to are vendored
  into `references/kb/`, cross-skill links resolve as siblings, and everything else becomes
  an upstream URL, so an installed archive never resolves back into this repository;
- `scripts/skill_bundle.py`, the single link contract shared by packaging, validation, and installation;
- `scripts/install_skills.py`, which installs selected skills or named sets into another
  repository for Claude Code, Cursor, Codex, Gemini, and Copilot from one canonical copy;
- `knowledge-base/skills/sets.json` defining the `ios-core`, `ios-all`, `meta-wearables`, and `all` sets;
- route-specific Fast paths across all 42 workspace skill packages;
- deterministic skill archive packaging and repository-wide package-contract validation;
- a second-pass ledger documenting the efficiency and quality improvement for every role;
- public repository README and launch positioning;
- complete role-by-role skill catalog;
- contributor, security, code-of-conduct, and licensing guidance;
- X launch kit with short posts, a technical post, and a seven-part thread;
- nineteen validated Apple-lane skill packages and portable artifacts;
- testing and release-assurance and source-refresh and availability-maintenance roles.

### Status

This is an active research and engineering seed. The package set is useful for evaluation and collaboration, but final publication quality still depends on continued route coverage, real-task evaluation, and appropriate device, account, signed-release, App Store, and production evidence.
