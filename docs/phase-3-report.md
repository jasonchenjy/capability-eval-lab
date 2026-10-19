# Phase 3 — independent verification and deterministic scoring

Phase 3 implements and qualifies a bounded verifier for the existing Phase 2 `fixture.py` task. The Phase 2 live Codex/Dish patch is consumed unchanged. No new live-model run, capability generation, pytest repository benchmark, or Phase 4 work was performed.

## Result and acceptance boundary

The qualification matrix contains 16 controls, including an independent two-role isolation probe. The Phase 2 live patch, a correct patch and an equivalent string-join implementation pass with score 1. Wrong value, wrong type, no-op and syntax-error candidates fail with score 0. Timeout, missing observation, forged score, forged observation, excess output, malformed patch, path traversal and missing-image infrastructure failure are invalid with score null. Invalid runs must not be included as ordinary failures in an accuracy denominator.

The hidden suite is two frozen declarative assertions over the exported type and value. The oracle file is private controller input, not committed and never supplied to the candidate/agent. It is not a general pytest suite or the planned rg-recovery benchmark. The expected target value is already public in the Phase 2 task; this phase establishes separation of test materials and trusted scoring, not secrecy of that public task requirement.

## Data flow and trust boundary

1. The controller checks the hidden-suite SHA-256 and its schema. It checks the declared base SHA-256 against the exact Phase 2 baseline.
2. A bounded parser reconstructs only `fixture.py`, in memory, from one full-file unified diff hunk. An empty patch is the no-op. Wrong paths, mismatched base lines, modes, renames, symlinks, extra hunks/files, NUL, invalid UTF-8, absent final newline and oversized patches are rejected. Git hooks, filters and candidate code are never run on the host.
3. A new candidate container receives only the reconstructed fixture. It executes the module using a reviewed wrapper and returns a bounded observation. The candidate container is removed before grading starts.
4. A different, fresh grader container receives the private declarative tests, the observation and source as inert JSON text. It never imports, evals or execs candidate source. A small AST interpreter independently attests the source's value before comparing it with the private tests.
5. Only the separate grader's validated response determines a passing score. The controller owns the final record. Candidate-provided scores are rejected, and malformed or absent grader responses are invalid.

The AST contract deliberately supports exactly one assignment to `VALUE`: string/integer/boolean/None constants, string addition, and literal list/tuple string joins, with bounded depth/output. A valid Python solution outside this grammar is **unsupported/invalid**, not necessarily incorrect. This is the explicit cost of independently authenticating the existing tiny fixture without running arbitrary Python alongside the oracle. Extending this to arbitrary repositories needs a different qualified test interface; this module must not silently become a general Python sandbox.

The source attestation was added after review identified a real weakness in observation-only scoring: a candidate could print a correctly shaped observation and exit without exporting that value. The `forged-observation` control now rejects that shortcut. A score-shaped JSON object is separately rejected by the observation schema. Unit tests also reject inconsistent source/value pairs and executable expressions in the AST interpreter.

## Isolation and execution limits

Both roles use the exact locally validated Phase 2 image ID, without automatic image pulls:

`sha256:2688969f72923b9f2a60704f8504b0e13b9c28f3968e57e68e0f95da2a7aad5e`

Docker inspection and in-container probes confirm uid/gid 65534, no network, no host bind mounts or volumes, no Docker socket or readable host auth, dropped capabilities, no-new-privileges, read-only root, 1 CPU, 256 MiB memory with no extra swap, and 64 processes. The only writable filesystems explicitly provided are 8 MiB `/workspace` and 16 MiB `/tmp` tmpfs mounts with noexec/nosuid/nodev. Python can interpret source on noexec tmpfs; noexec is not a code-execution prohibition. Direct outbound IP access fails with errno 101. The candidate cannot see the hidden-suite file, and the grader has no candidate file. Candidate source enters the grader only as data to the restricted AST parser.

Candidate execution defaults to 5 seconds; qualification uses 2 seconds. Grading has a 5-second timeout and Docker management operations have 30-second limits. Combined captured stdout/stderr are capped at 64 KiB. Timed-out and excessive-output candidates are removed; all qualification containers were confirmed removed. These are separate containers sharing the Docker VM kernel, not separate VMs or a proof against kernel/container-runtime exploits.

## Evidence and reproducibility

Validation completed with 34 passing tests, clean Ruff checks, successful wheel/sdist builds, matching evidence hashes, and no private suite or work directory in the distribution artifacts. Both original reference checkouts retained their HEAD and working-tree state.

Curated records are in `docs/evidence/phase3/`. Each candidate record binds base, patch, reconstructed source, private suite, worker and grader-script hashes, image identity, execution outcome, observation and score. The manifest additionally binds the executed implementation and qualification sources. Hidden tests, raw development artifacts and private material remain ignored under `work/phase3/`; only hashes and reviewed observations are published.

Run from this repository with its existing Python environment and Docker image. No new Python dependencies are required. Use the Docker endpoint appropriate to your machine (the measured endpoint here is `unix:///Users/junyu/.colima/default/docker.sock`). Provision a trusted private suite separately; its schema has unique string `id`, `field` (`type` or `value`), and string `expected`, with both fields represented. Public unrelated schema examples are in `tests/test_phase3_contract.py`.

```sh
export DOCKER_HOST=unix:///Users/junyu/.colima/default/docker.sock
.venv/bin/python -m capability_eval.validation.phase3_controls \
  --output work/phase3/reproduction-NEW \
  --hidden-tests /secure/path/hidden-tests.json \
  --phase2-patch docs/evidence/phase2/live-01/submission.patch

.venv/bin/python -m capability_eval.runtime.phase3 \
  --patch docs/evidence/phase2/live-01/submission.patch \
  --base-sha256 e68d64f3704621913abb8b695afa61ff1628a0202d9c54f0acc21b56a74c858d \
  --hidden-tests /secure/path/hidden-tests.json \
  --tests-sha256 YOUR_REVIEWED_SUITE_SHA256 \
  --output work/phase3/single-NEW.json
```

Outputs must be new. The runtime CLI exits 2 for invalid evaluation, 0 for a completed pass/fail evaluation; consumers must read `status` and `score`. Qualification exits unsuccessfully if any control differs from its expected outcome. The original private qualification file remains locally in `work/phase3/private/hidden-tests.json` and must be transferred separately if needed; it is absent from Git and distribution artifacts.

During development, `docker cp` failed against the read-only container root despite the writable tmpfs. Input transfer now uses stdin into a fixed Python file writer operating inside the tmpfs. This retains the read-only/no-host-mount policy. A preliminary permission probe also assumed `Path.exists()` under `/root` would return false; the nonroot permission denial required testing readability instead. These failed development runs were not counted as accepted evidence.

## Scope decision

The experiment demonstrates independent scoring and patch handoff for the fixed Phase 2 fixture, with a qualified restricted expression contract. It does not yet demonstrate arbitrary Python hidden-test execution, broad coding capability, original pytest-task parity, or an advantage over Harbor. The additional source-attestation logic is custom maintenance cost and must be included in a future comparison.

Phase 3 was explicitly approved. Stop after committing, publishing and reporting these results. Phase 4 requires new user approval.
