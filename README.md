# Capability Eval Lab

An independent experiment to test whether Petri Dish and Inspect AI can replace the Harbor runtime for capability-driven coding-agent evaluations while adding auditor capabilities. No superiority claim is made.

Phase 2 validates real command execution and file edits through Dish passthrough and the Codex ACP scaffold, with deterministic controls and one live account-backed run. Phase 3 adds separate candidate/grader containers, private declarative tests and deterministic scoring for the same restricted fixture; see the [Phase 3 report](docs/phase-3-report.md). See the [Phase 2 report](docs/phase-2-report.md).

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

Most `src/capability_eval/` subpackages reserve future responsibilities; `runtime/phase2.py` and `validation/phase2_evidence.py` contain the bounded execution probe and offline evidence review. The Phase 3 modules add strict patch admission, isolated execution and trusted grading for the fixed fixture. The case directory is an inventory placeholder, not an executable benchmark. The original evaluation repository is read-only reference material. Changes and future curated artifacts belong here; credentials, private tests, raw transcripts, and sensitive data must not be committed.

Phase 4 was explicitly approved and executed. See the [Phase 4 report](docs/phase-4-report.md) for Skill/Bloom authoring, explicit review, frozen seeds and verifier locks. Stop here; Phase 5 requires explicit user approval.


Architecture v2 is approved with the Scenario Designer and extensible verifier amendments; see [approval history](docs/decisions/architecture-v2-approval.md). [Phase 5A](docs/phase-5a-report.md) qualifies a pinned real Boltons defect, narrow independent black-box verification and repository handoff. It makes no command-recovery or live-model claim. Phase 5B and later work require separate approval.


Phase 5A review repairs use `black-box-json-v2`: only the task's inert regex literal may change, and qualification validates the externally approved scenario and every control patch. This is an explicit narrowing of accepted repairs, not general hostile-Python API attestation. See the report's review-correction section.

Phase 5B is the separately authorized deterministic environment/evidence slice;
see the [Phase 5B report](docs/phase-5b-report.md). It uses real native commands in
pinned rg-absent/present environments, a passive auditor, and separate task and
recovery outcomes. The finite command classifier fails closed on unsupported or
missing evidence. No live models are called in 5B; Phase 5C remains unapproved.
