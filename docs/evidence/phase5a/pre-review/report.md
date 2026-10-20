# Phase 5A — real repository task and independent black-box verification

Phase 5A implementation and offline qualification completed on 2026-10-19. Architecture v2 is approved with the user's two amendments; [decision history](decisions/architecture-v2-approval.md) preserves the original proposals. No live model calls, rg environment changes, interactive auditor, Phase 5B/5C or Harbor comparison were performed.

## Selected task and immutable inputs

The task uses [Boltons](https://github.com/mahmoud/boltons) at **`967864f89791509f9eb36b22b4579d36b72a6df2`**, the parent of upstream fix `d12d86a4706aa4a367a91679b0ff9b6a572e5298`. [PR #475](https://github.com/mahmoud/boltons/pull/475) records the actual defect: incorrect Unicode separator escapes cause ordinary numeric/date text to be split and fail to recognize Unicode line/paragraph separators. `indent` inherits the defect. This is a real historical bug, not a mutation or identification of the old missing pytest/rg case.

The public [instruction](../evals/boltons_unicode_lines/instruction.md) asks for the API repair without prescribing implementation or fallback tool. The full 112-file baseline, including public pytest tests and BSD-3-Clause LICENSE, is materialized from the frozen Git archive, not a provenance-only toy fixture. The source archive stays under ignored work storage; [snapshot.json](../configs/phase5a/snapshot.json) binds every file and the complete archive. All baseline Git entries are regular 100644 files. The execution snapshot deliberately applies read-only permissions except the allowed source path.

Only `boltons/strutils.py` may be replaced. The private reference control uses the upstream fix with attribution; the alternative control uses literal Unicode separators and has different bytes. Both preserve all other repository files. The task is manually curated; an autonomous Scenario Designer is not implemented.

## Architecture changes and implementation scope

The Scenario Designer is explicitly the central creation decision maker coordinating Task, Environment Scenario and Auditor Behavior generators, with the shared contract governing compatible artifacts. In 5A its decisions are documented manually. Environment and auditor conditions remain independent future axes, with no 5B implementation hidden in this milestone.

[Verifier Contract v1](verifier-contract-v1.md) distinguishes the implemented `black-box-json-v1` strategy from a future Repository Test Verifier. The latter remains design-only and cannot inherit black-box secrecy claims. The existing Phase 3 AST verifier is unchanged and not generalized. A fixed JSON adapter exposes the existing library APIs; Boltons does not need to have a native CLI. There is no general plugin loader or new dependency.

The private suite contains 22 reviewed input/expected-output assertions over both APIs. The trusted host driver compares actual candidate responses. It does not import candidate code. Each verification creates a fresh restricted candidate container; each request gets a new Python interpreter. Expected values, case IDs and authoritative result state stay outside that container. No hidden pytest executes alongside candidate code. Private test inputs are necessarily observable to the candidate during execution.

The manually provisioned private suite and solution controls were created by this engineering session in a trusted custodian capacity. This is not a claim of independent human review, automated multi-role context separation, or blind authoring. No separate creation/target model received private material. Future automated creation must enforce the role boundaries approved in Architecture v2.

## Acceptance results

The final qualification run is `work/phase5a/qualification-02`; curated evidence is in [evidence/phase5a](evidence/phase5a/). The first run also passed, then lock comparison was tightened to reject JSON boolean/integer equivalence and the entire control matrix was rerun on the final verifier bytes. The private suite was not tuned between runs.

| Acceptance area | Evidence and result |
|---|---|
| Real task validity | Baseline/no-op fail; upstream reference and different alternative pass all 22 mandatory checks. Wrong and public-example-only overfit repairs fail. |
| Verifier validity | Functional exception is fail/0 after all checks. Forged score, missing/malformed result, abrupt exit, excessive output, deep JSON and timeout are invalid/null. Candidate never supplies authoritative score. |
| Handoff/reconstruction | Whole public repository is installed and independently collected from a real container. Reconstructed source tree matches collected bytes exactly. Actual mode changes and symlinks fail collection; traversal/extra paths, metadata changes, unsupported encoding, size and base mismatch are rejected by contract tests. |
| Independent execution | Real Python calls in pinned container; expected results and aggregation remain host-side. No candidate imports on host. No-op and wrong controls demonstrate actual assertions, not successful-looking transcript grading. |
| Isolation | Nonroot uid 65534; private suite paths, Docker socket and host auth unreadable; egress probe blocked; no credential environment variables. Docker inspection enforces no host binds/privilege, read-only root, dropped capabilities and bounded tmpfs/CPU/memory/PIDs. |
| Reproducibility/provenance | Fixed Git/tree/archive, image, adapter, driver, scorer and suite identities. Repeated correct run has identical deterministic observations and outcome from a new container; lock rechecked after execution. |
| Existing regressions | All 61 previous tests preserved; full suite now **94 passing tests**. Full src/tests Ruff check and wheel/sdist build pass. No private/work/source-checkout artifacts in packages. Original reference HEAD and worktree state unchanged. |

Control matrix: 17 submission controls, one repeat and one real missing-Docker-endpoint infrastructure control. The infrastructure control returns invalid/null. Separate handoff and isolation probes also pass. All candidate verification containers were removed; a final Docker name check found no `capability-phase3` containers remaining. No model usage or cost is incurred/reported.

For passing and ordinary failing candidates every mandatory check is executed. Invalid protocol/time/resource/transport runs terminate early and record incomplete counts, never claim all checks ran. A source exception caught by the adapter is a functional failure; abrupt exit outside the adapter cannot establish a valid response and is invalid. These semantics are frozen in the contract.

## Reproduction

Use the existing locked Python environment and exact prequalified Docker image. The runtime image ID is in `configs/phase5a/verifier-lock.json`; it is never auto-pulled. Download/provision source before offline qualification:

```sh
# A new task-data checkout only; never use the original evaluation checkout.
git clone https://github.com/mahmoud/boltons.git work/phase5a/boltons
git -C work/phase5a/boltons archive --format=tar \
  967864f89791509f9eb36b22b4579d36b72a6df2 > work/phase5a/base.tar
```

A trusted operator must separately provision the exact private suite and qualification patch controls. They remain locally under ignored `work/phase5a/private/`, are not in Git or distributions, and must not be exposed to a future target. Hashes are in the lock and scenario manifest. The JSON suite schema is documented in the verifier contract; creating a new suite requires a new qualification and approval root. Public synthetic unit fixtures are not the private benchmark suite.

```sh
export DOCKER_HOST=unix:///Users/junyu/.colima/default/docker.sock
.venv/bin/python -m capability_eval.validation.phase5a \
  --archive work/phase5a/base.tar \
  --snapshot configs/phase5a/snapshot.json \
  --private work/phase5a/private \
  --lock configs/phase5a/verifier-lock.json \
  --expected-lock "$(.venv/bin/python -c 'import json; print(json.load(open("configs/phase5a/approved-root.json"))["verifier_lock_sha256"])')" \
  --output work/phase5a/qualification-NEW
```

Use an unused output directory. The standalone `capability_eval.verifier.phase5a` CLI accepts a patch/archive/snapshot/suite/lock/external expected digest and writes a new result; exit 2 means invalid, while exit 0 means read the completed pass/fail result. Qualification fails if any control differs from its expected result. Reproducibility requires authorized access to the private artifacts; hashes alone do not reproduce hidden expectations.

## Remaining risks and limits

- This is one finite library API task, not a universal Python verifier or proof of capability. Candidate behavior can overfit a finite suite; the tested narrow overfit is rejected, not all conceivable shortcuts.
- Inputs and prior same-run requests may be observed by candidate code; one container is shared within a verification run. It has no expected outputs or host suite access, but per-request isolation is not claimed. Containers share the VM kernel; kernel exploit resistance is not proven.
- Public historical bug/fix visibility is a model-contamination confound. A future live trial must report it. No independent-agent or command-recovery result exists yet.
- The handoff is a deliberately narrow source-replacement envelope, not arbitrary multi-file Git patch support. The only editable path and its interface are task-specific.
- The source/scoring lock assumes a trusted controller and separately controlled root; hashes do not authenticate a human reviewer. The approved root is an integrity anchor, not a signature.
- Public upstream pytest tests are preserved but were not run as hidden verification or used to qualify a Repository Test Verifier. The independent suite verifies this task's documented API behavior only.
- Phase 2–4 runtime/regression code was preserved. Its historical assumptions are not upgraded implicitly by this new verifier.

## Phase 5B readiness

**Ready to request approval for 5B, not authorized to execute it.** The prerequisite real task/verifier/handoff now has passing controls and fixed provenance. 5B must separately freeze rg availability/installation policy, authoritative native command events, recovery evidence predicates and a passive structured auditor. It must distinguish successful task completion without exposure from actual recovery. The scenario manifest explicitly marks capability evidence `not_exercised` and environment/auditor control deferred. No live model calls are required for 5B qualification; 5C remains a separate gate.
