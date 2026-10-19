# Phase 4 — capability authoring, Bloom and reviewed frozen seeds

Phase 4 implements a bounded authoring pipeline and stops before Phase 5. It reuses the verified Harbor create-task Skill and public Petri Bloom 0.2.6 understanding/ideation APIs. Repository/capability identity, explicit review, immutable seed hashes and separately pinned verification are now executable contracts rather than only a design document.

## Executed results

- Live Bloom generation used the existing Codex account-backed `openai/gpt-6-luna` connection: three model requests (understanding, scenarios, dimensions), 11.615 seconds, 13,054 input tokens and 925 output tokens (13,979 total). Per-call configuration and usage are in `evidence/phase4/live-draft.json`. Monetary billing data was unavailable; it is not reported as zero.
- The generated scenario included incompatible conversation-only/no-tools/deferred-execution wording. An explicit **assistant review**, recorded as such, removed it and retained a precise native-edit instruction. This is not represented as human approval or as an automatically safe conversion of raw Bloom prose.
- The reviewed seed was executed through public Petri/Dish APIs and the real pinned Codex ACP scaffold. This target smoke test used **deterministic inference**, not a new live coding-model capability trial. A real native command edited the fixture, and a separate controller read and Git diff established the artifact.
- The locked Phase 3 verifier scored the exported patch 1, and wrong/no-op controls 0. The hidden-suite bytes and verifier implementation remained unchanged. There was no Bloom judge-based grading.
- 56 tests pass, including native Bloom stages with deterministic model responses, private-data canaries, review/draft identity binding, seed tampering, generated tool rejection, changed verifier/test detection, and the fixed auditor policy. Existing Phase 2/3 regression tests also pass.

## What is reused

The exact upstream [Harbor create-task Skill](https://github.com/harbor-framework/harbor/blob/346d04c545ddad5d171606ee9f2a3db3e5838f18/skills/create-task/SKILL.md) is packaged with its Apache-2.0 license and verified SHA-256. It is supplied as authoring guidance to Bloom. No full Harbor repository/runtime is copied. It remains uncertain whether this was the exact historical skill used in the previous evaluation project; it is the verified relevant reference identified during Phase 1.

Its responsibilities map as follows: task scaffolding becomes a strict public TaskSpec; prompt authoring becomes a reviewed instruction; environment selection reuses the qualified image; verifier selection binds the existing Phase 3 verifier; oracle/negative qualification reuses the known controls; the task README documents the resulting case. The skill's grading and environment questions are already answered by the approved independent-verifier design. Skill examples do not override its network or scoring policy.

Bloom's public `Behavior`, `Instructions`, `run_understanding_async` and `run_ideation_async` are used in memory. The async public APIs avoid directory-based overwrite behavior and dotenv loading. Only structured submission tools are provided during generation; generated code is not executed. The conversation modality avoids requesting simulated agent-tool definitions, but still produced unsuitable conversation framing, hence review remains essential. Native Bloom dimensions (including default diagnostic dimensions) are retained for inspection and never installed as deterministic scoring rules.

## Artifact and approval boundary

The flow is:

`TaskSpec → Bloom draft → explicit Review → FrozenSeed → fixed auditor → native patch → locked verifier`

`evals/phase4_fixture/spec.json` records capability, GitHub repository, full revision, selected specification, source provenance, public constraints and the public fixture. This release accepts only the existing curated single-file fixture. It does not discover GitHub issues, extract arbitrary repositories, author new hidden tests, or implement the Phase 5 pytest/rg scenario. A curator must provide the selected specification. The repository revision is provenance; this fixture is materialized from the documented baseline, not claimed to be a full checkout.

A review binds the entire draft and one exact proposal by hash, records reviewer kind/rationale and four mandatory checks, and supplies the reviewed public instruction. Raw generated seeds and diagnostic dimensions are not executable auditor policy. Proposals with simulated tool definitions cannot be exported. The fixed auditor can send once and resume; it cannot call a tool-result fabrication, rollback or injection-rewrite tool. Unexpected intercepted calls fail rather than being simulated.

Canonical UTF-8 JSON provides deterministic hashes: re-exporting the same reviewed artifacts yields identical frozen bytes. This does **not** promise deterministic model regeneration; generation times and model output can vary. All output paths are chosen by the trusted caller, never from generated names, and writes reject existing files.

`configs/phase4/approved-roots.json` is the separately controlled approval anchor. Runtime consumers must supply its expected seed and verifier digests rather than trusting hashes supplied by an untrusted bundle. Review metadata and hashes do not cryptographically authenticate a human reviewer; the operator/checked-out approval configuration is trusted. Anyone authorized to replace both the implementation and approval roots is outside this threat model.

## Hidden tests and score immutability

The authoring model receives only the public specification, selected authoring Skill and its own intermediate proposals. It receives no hidden-test bytes, private file paths, reference solution or verifier manifest. The coding agent receives only the reviewed public task and materialized public fixture.

A separately created `VerifierLock` pins the exact hidden-suite hash, baseline hash, image identity, four verifier/patch/scoring implementation files and the literal policy `all-pass=1;fail=0;invalid=null`. `verify_frozen` checks the external root, bundle binding, current implementation and supplied private test bytes before and after evaluation. It forwards only the pinned verifier parameters to Phase 3; seed instructions and generated rubrics cannot supply a different test suite, scoring function or image. Changes fail closed and require a new trusted qualification/review cycle.

Tests show that changed seeds, review inputs, private tests and scoring implementation are rejected; even a deliberately malicious reviewed instruction has no API route to replace the verifier parameters. This protects the grading boundary, not the semantic quality of an instruction. A reviewer must still reject a public instruction that contradicts the selected task.

The existing Phase 3 isolation and restricted AST contract remain in effect. No new general Python/pytest verifier is claimed. Raw Inspect logs and account auth remain outside published artifacts. Token values and account identifiers are not recorded in provenance.

## Reproduction

From the repository root, use the existing pinned research environment. New outputs must have existing parent directories and unused filenames.

```sh
# Trusted operator creates the verifier lock independently of Bloom.
.venv/bin/python -m capability_eval.creation.phase4 lock \
  --hidden-tests /secure/path/hidden-tests.json --output work/phase4/new-lock.json

# Live authoring: existing Codex account auth stays on the controller.
.venv/bin/python -m capability_eval.creation.phase4 draft \
  --spec evals/phase4_fixture/spec.json --codex-auth /path/to/codex/auth.json \
  --output work/phase4/new-draft.json

# Review the complete draft, write a Review JSON, then explicitly freeze it.
.venv/bin/python -m capability_eval.creation.phase4 freeze \
  --draft work/phase4/new-draft.json --review work/phase4/new-review.json \
  --verifier-lock work/phase4/new-lock.json --expected-lock-sha256 TRUSTED_LOCK_DIGEST \
  --output work/phase4/new-seed.json

# Qualify the checked-in reviewed seed with your separately provisioned suite.
export DOCKER_HOST=unix:///Users/junyu/.colima/default/docker.sock
.venv/bin/python -m capability_eval.validation.phase4 \
  --bundle evals/phase4_fixture/frozen-seed.json \
  --roots configs/phase4/approved-roots.json \
  --verifier-lock configs/phase4/verifier-lock.json \
  --hidden-tests /secure/path/hidden-tests.json \
  --compose "$PWD/configs/phase2/compose.yaml" --output work/phase4/qualification-NEW
```

Configure Docker Compose on the controller as in Phase 2; this machine uses its repository-local ignored `work/docker` tooling. No upstream project was modified. The same previously observed AnyIO interpreter-shutdown warnings occurred after successful collection; they remain an upstream cleanup concern rather than a passing/failing score input.

`executed-source.json` records the sources used for the initial live generation/native run, retained locally under ignored `work/phase4/executed-source`. Subsequent formatting changed layout only; the final sources, frozen artifacts and curated execution evidence are hashed in the manifest. Model generation is not rerun merely to obtain different output from an unchanged prompt.

## Decision and scope

Bloom contributes authoring drafts and diagnostic ideas, but its default conversational/simulation assumptions require explicit adaptation. The useful integration here is reviewed authoring plus a fixed native auditor, not unrestricted Bloom evaluation or a new source of correctness ground truth. Manual review and custom contract/lock code are maintenance costs to include in the future comparison. No claim is made that this replaces or improves upon Harbor.

Phase 4 was explicitly authorized. Stop after committing/publishing and reporting. Do not begin Phase 5 without user approval.
