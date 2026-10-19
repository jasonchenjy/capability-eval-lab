# Capability Eval Lab

An independent experiment to test whether Petri Dish and Inspect AI can replace the Harbor runtime for capability-driven coding-agent evaluations while adding auditor capabilities. No superiority claim is made.

Phase 1 provides packaging, pinned research dependencies, source investigation, and an implementation plan. No runtime integration or model evaluation is implemented.

Target flow: repository + capability → eval creation → auditor seed → Dish + Inspect → coding agent → patch → independent hidden-test sandbox → scoring + validation.

## Setup

Use Python 3.12+ (locally validated with Python 3.13) and uv 0.13.2:

```sh
uv sync --locked --extra research
uv run --locked pytest
uv build
```

The framework dependencies are optional under `research`; the package itself has no runtime dependency or executable entry point. `uv.lock` pins transitive dependencies. The legacy pytest task requires its own Python 3.8.20 environment in a future isolated worker; it must not run in this controller environment.

## Reading

- [Framework investigation](docs/investigation.md)
- [Minimal proposed architecture](docs/architecture.md)
- [Phase acceptance criteria](docs/implementation-plan.md)
- [Creation Skill assessment](docs/creation-skill-assessment.md)
- [Reference inventory](docs/reference-inventory.md)
- [Attribution and reuse](docs/attribution.md)
- [Phase 1 status](docs/phase-1-status.md)

The `src/capability_eval/` subpackages reserve responsibilities only. The case directory is an inventory placeholder, not an executable benchmark. The original evaluation repository is read-only reference material. Changes and future curated artifacts belong here; credentials, private tests, raw transcripts, and sensitive data must not be committed.

Phase 2 requires explicit user approval after the Phase 1 findings are reviewed.
