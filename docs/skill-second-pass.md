# Skill second-pass ledger


> **Structure note (2026-09-06).** This repository was split. The 19 Apple/iOS skill
> packages now live at `.agent/skills/<name>/` and generate into `skills/<name>/`; the
> 23 Meta Wearables packages moved to
> [meta-wearables-ops-plugin](https://github.com/shotcowboystyle/meta-wearables-ops-plugin).
> The `.skill` archive pipeline (`package_skills.py`, `install_skills.py`, `sets.json`)
> was retired in favour of `scripts/build.py`. Passages below that describe the old
> single-repo layout are kept as a record of how it was, not as current instructions.

This pass covers all 42 package entrypoints under
`.agent/skills/`: the 19 Apple/iOS roles and the 23 Meta
Wearables extension roles.

## Shared improvement

Every package now has a `## Fast path` section. It is intentionally
route-specific, and answers three questions before the longer workflow runs:

1. What must be frozen or inspected first?
2. What is the smallest useful slice or evidence gate?
3. When should the agent stop, report the missing boundary, or escalate?

This makes ordinary builds cheaper to explore while preserving the repository’s
source, target, lifecycle, privacy, and evidence boundaries. The fast path is a
routing aid, not permission to skip a gate required by the selected claim.

## Apple lane

| Package | Second-pass focus |
| --- | --- |
| [apple-sdk-route](../.agent/skills/apple-sdk-route/SKILL.md) | One-page outcome/input/transformation route record and a single vertical slice before broad framework research. |
| [ios-agentic-apple-engineering-team](../.agent/skills/ios-agentic-apple-engineering-team/SKILL.md) | Risk-proportional role selection so simple local changes do not run the full team. |
| [ios-capability-route-planner](../.agent/skills/ios-capability-route-planner/SKILL.md) | Compare only plausible capability lanes and defer irreversible target setup until the route wins. |
| [ios-commerce-identity-and-security](../.agent/skills/ios-commerce-identity-and-security/SKILL.md) | Trust-and-authority ledger plus denial, replay, cancellation, and offline gates before provider expansion. |
| [ios-companion-communications](../.agent/skills/ios-companion-communications/SKILL.md) | One message/call/notification lifecycle with duplicate, delay, background, revocation, and disconnect cases. |
| [ios-data-and-device-services](../.agent/skills/ios-data-and-device-services/SKILL.md) | Truth-ownership table and one persistence/observation slice before adding a sync or protected-data service. |
| [ios-device-release-proof](../.agent/skills/ios-device-release-proof/SKILL.md) | Claim-first evidence selection and first-unmet-gate execution with explicit non-proof. |
| [ios-media-ml-and-inputs](../.agent/skills/ios-media-ml-and-inputs/SKILL.md) | Fixture-backed bounded input/output/cancellation loop before live capture and physical work. |
| [ios-native-design-verification](../.agent/skills/ios-native-design-verification/SKILL.md) | Small state-by-environment review matrix with concrete defect ownership before screenshot breadth. |
| [ios-on-device-intelligence-evaluation](../.agent/skills/ios-on-device-intelligence-evaluation/SKILL.md) | Deterministic baseline and representative failure/refusal fixtures before model tuning. |
| [ios-privacy-performance-release-proof](../.agent/skills/ios-privacy-performance-release-proof/SKILL.md) | Change-impact triage so only affected privacy, performance, accessibility, artifact, or distribution lanes run. |
| [ios-project-target-architect](../.agent/skills/ios-project-target-architect/SKILL.md) | Compile-critical target graph before feature code or new extension creation. |
| [ios-source-refresh-and-availability](../.agent/skills/ios-source-refresh-and-availability/SKILL.md) | Source-to-package impact graph and a no-change receipt when the installed interface is still aligned. |
| [ios-spatial-graphics-and-games](../.agent/skills/ios-spatial-graphics-and-games/SKILL.md) | One frame-budgeted renderer slice with capability gate and fallback before scene or multiplayer expansion. |
| [ios-system-surfaces-and-background](../.agent/skills/ios-system-surfaces-and-background/SKILL.md) | One system-owned entry point, deep link, return path, and invocation test before more surfaces. |
| [ios-testing-and-release-assurance](../.agent/skills/ios-testing-and-release-assurance/SKILL.md) | Lowest-cost claim-to-test mapping with deterministic-first escalation. |
| [liquid-glass-design](../.agent/skills/liquid-glass-design/SKILL.md) | System-managed bars and functional hierarchy audited before custom glass effects. |
| [on-device-ai-feature](../.agent/skills/on-device-ai-feature/SKILL.md) | Deterministic input/schema/validation/approval/commit contract before prompt or model expansion. |
| [swiftui-native-design](../.agent/skills/swiftui-native-design/SKILL.md) | One observable state-driven screen slice before breakpoint, input-mode, and secondary-flow expansion. |

## Meta Wearables lane

| Package | Second-pass focus |
| --- | --- |
| [meta-dat-android-api-atlas](../.agent/skills/meta-dat-android-api-atlas/SKILL.md) | One manifest-filtered capability row resolved against the actual artifact before whole-surface traversal. |
| [meta-dat-android-integration](../.agent/skills/meta-dat-android-integration/SKILL.md) | Android artifact-to-initialize-to-capability-to-stop compile path before parity or physical cases. |
| [meta-dat-api-atlas](../.agent/skills/meta-dat-api-atlas/SKILL.md) | One normalized exact-symbol row unless the request is explicitly full-SDK or parity. |
| [meta-dat-camera-audio](../.agent/skills/meta-dat-camera-audio/SKILL.md) | Independent bounded camera/photo and explicit audio slices with separate ownership and evidence. |
| [meta-dat-display](../.agent/skills/meta-dat-display/SKILL.md) | One capability-gated Display state, input event, teardown, and phone fallback before rich UI. |
| [meta-dat-ios-integration](../.agent/skills/meta-dat-ios-integration/SKILL.md) | Target preflight and one registration-to-started-session-to-stop lifecycle before capability breadth. |
| [meta-wearables-agentic-team](../.agent/skills/meta-wearables-agentic-team/SKILL.md) | Preflight-first, playbook-scoped role routing with bootstrap stop behavior when no target exists. |
| [meta-wearables-app-architecture](../.agent/skills/meta-wearables-app-architecture/SKILL.md) | Shared-domain/adapter/surface/fake boxes and one typed adapter seam before cross-platform parity. |
| [meta-wearables-debugging-observability](../.agent/skills/meta-wearables-debugging-observability/SKILL.md) | First-failure timeline and redacted structured capture instead of an indiscriminate diagnostic dump. |
| [meta-wearables-developer-operations](../.agent/skills/meta-wearables-developer-operations/SKILL.md) | Read-only, reversible, and release-affecting action classification with pre/post receipts for mutations. |
| [meta-wearables-device-compatibility](../.agent/skills/meta-wearables-device-compatibility/SKILL.md) | One normalized product/runtime/firmware/SDK/capability tuple before implementation. |
| [meta-wearables-device-proof](../.agent/skills/meta-wearables-device-proof/SKILL.md) | Target preflight and lowest unmet `PRE-*` gate before evidence promotion. |
| [meta-wearables-full-sdk-audit](../.agent/skills/meta-wearables-full-sdk-audit/SKILL.md) | Terminology-first row filtering and coverage counting, with full traversal reserved for full/parity requests. |
| [meta-wearables-implementation-recipes](../.agent/skills/meta-wearables-implementation-recipes/SKILL.md) | One playbook/tuple/starter and adapter compile seam before target-specific glue. |
| [meta-wearables-input-sensors](../.agent/skills/meta-wearables-input-sensors/SKILL.md) | Signal source/host routing and epoch-aware reducer event before physical-input proof. |
| [meta-wearables-on-device-compliance](../.agent/skills/meta-wearables-on-device-compliance/SKILL.md) | One-data-item processing ledger and earliest-boundary test before unrelated capability auditing. |
| [meta-wearables-operational-readiness](../.agent/skills/meta-wearables-operational-readiness/SKILL.md) | Ordered first-failure decision tree with one post-repair verification instead of repeated resets. |
| [meta-wearables-privacy-publishing](../.agent/skills/meta-wearables-privacy-publishing/SKILL.md) | One consent-to-disclosure data path and earliest release-gate correction. |
| [meta-wearables-route-planner](../.agent/skills/meta-wearables-route-planner/SKILL.md) | Surface/capability/runtime/fallback/evidence resolution with an explicit ambiguity stop. |
| [meta-wearables-security-attestation](../.agent/skills/meta-wearables-security-attestation/SKILL.md) | Identity tuple, secret classification, evidence-level mapping, and first missing authority. |
| [meta-wearables-source-refresh](../.agent/skills/meta-wearables-source-refresh/SKILL.md) | Revision/tree checks first, then impacted-row updates and archive parity only when drift exists. |
| [meta-wearables-transport-reliability](../.agent/skills/meta-wearables-transport-reliability/SKILL.md) | One bounded transport operation with explicit degraded/reconnect/stop states and budgets. |
| [meta-wearables-web-apps](../.agent/skills/meta-wearables-web-apps/SKILL.md) | Entrypoint/origin preflight and one 600x600 interaction before simulator or physical Display breadth. |

## Reproducible package checks

Run these from the repository root:

```bash
python3 scripts/validate_skill_bundle.py .
python3 scripts/package_skills.py .
python3 scripts/validate_skill_bundle.py . --check-archives
```

The packager includes each package’s `SKILL.md`, references, scripts, and
assets, uses stable archive timestamps and ordering, and replaces artifacts
atomically. Use `--prune` only when intentionally removing stale archives.
