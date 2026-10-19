# Reviewed native-file-edit fixture

This Phase 4 pilot authors an evaluation of precise native file editing. The public task is in [instruction.md](instruction.md); the curated baseline is in `spec.json`. It is derived from the Phase 2 fixture, not the missing historical pytest/rg recovery case and not an automatically discovered GitHub issue.

The schema preserves repository/capability identity and frozen revision. Bloom's live proposal and explicit assistant review are in `docs/evidence/phase4/`. `frozen-seed.json` contains only the reviewed instruction, public identity and approval digests; generated scoring dimensions are not used.

Runtime uses the pinned Phase 2 Codex ACP/Dish environment, native passthrough and no network. The trusted verifier runs independently with the existing Phase 3 image and restricted VALUE-expression contract. Correctness is all-or-nothing; invalid runs have null scores. Private tests are not included here. The smoke run uses deterministic target inference and real execution, separate from the live Bloom authoring calls.

Run and review instructions, resource constraints, source provenance and approval boundaries are documented in [the Phase 4 report](../../docs/phase-4-report.md). Phase 5 has not started.
