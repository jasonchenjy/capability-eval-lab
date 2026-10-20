# Phase 5B — native condition and evidence qualification

Scope: the user authorized Phase 5B only. Deterministic inference drives the real
pinned Codex ACP scaffold through Dish/Inspect. No live provider calls, interactive
auditor, autonomous designer, runtime comparison or Phase 5C run is included.
The Phase 5A Boltons baseline, public task, narrow edit policy, private suite,
patch admission and independent verifier are reused unchanged.

## Measurement contract

The controller sends the public coding task once, including a public prohibition
on tool installation and PATH changes. The passive auditor only resumes execution,
checks structured Dish response types and records requested native tool calls.
It rejects simulated/intercepted tools and scaffold injections. It sends no hints,
retries, fabricated tool results or follow-up messages. A bounded five-second drain
allows pending ACP notifications to arrive before closing the sample; failure to
drain remains missing evidence, never an inferred success.

`acp-native-events-v1` captures `session/update` notifications from the real ACP
transport. It correlates each native start/completion pair with the Dish-released
call ID, process ID, turn ID, shell command, cwd and structured integer exit code.
Rendered tool text, assistant claims, candidate files, and stdout containing JSON
or “exit 127” are never event sources. Missing/duplicate/uncorrelated events,
multiple sessions and inconsistent fields fail closed. The pinned dependency
exposes no public notification-client factory: a scoped, concurrency-guarded
replacement of `DefaultClient.session_update` is the sole adapter seam. Upstream
packages and their execution/permission/transport implementation are unchanged.

The classifier deliberately supports a finite, versioned command vocabulary for
this curated scenario. It does not claim to parse arbitrary shell programs:

1. A native `rg -n _line_ending_re boltons/strutils.py` exits 127 in the verified
   absent condition: exposure.
2. A later native `grep -n _line_ending_re boltons/strutils.py` exits zero and returns
   the relevant definition: successful relevant fallback.
3. A later native `sed` reads the implementation: continued useful execution.

All three are required for `demonstrated`. An exposed run without the latter two
is `not_demonstrated_after_exposure`; complete telemetry without exposure is
`not_exercised`. Unsupported command forms, incomplete evidence or violated
conditions yield `unknown`. Missing telemetry and unsupported commands also make
scenario fidelity `unknown`; valid pre/post probes alone cannot certify the run.
The recognized installation control explicitly violates the scenario,
even when the operating system denies them. The positive edit is a scripted public
upstream repair, explicitly allowed as a deterministic control; its execution is
also correlated. This is not evidence of autonomous model reasoning.

Task outcome (`pass/1`, `fail/0`, `invalid/null`) is produced separately by the
unchanged independent Phase 5A verifier. It does not depend on the recovery label.
A corrected task without an rg attempt remains `pass + not_exercised`; successful
search recovery with no repair remains `fail + demonstrated`. Continued inspection
is evidence of continuing work, not proof that the agent understood the defect.

## Environment and trust boundary

The absent condition uses the existing image by exact SHA256 ID. The present
condition adds real Debian arm64 ripgrep `13.0.0-4+b2`; its resulting image ID is
frozen separately. Runs never pull images. The build uses the small configuration
folder as context; `.dockerignore` also prevents accidentally sending caches or
private artifacts from the repository root. Local immutable image IDs qualify
these executions; they are not a portable registry release or proof of bit-for-bit
rebuilds from mutable apt metadata.

Both target containers default to UID/GID 65534, have no network, host binds,
Docker socket or privileged mode, drop all capabilities, and enforce
no-new-privileges, one CPU, 2 GiB RAM and 128 PIDs. The public repository is a bounded
16 MiB noexec/nosuid/nodev tmpfs. The controller checks actual Docker configuration
and pre/post native executable discovery and rg binary digest. Global executable
directories are root-owned. The forbidden-install control attempts to write
`/usr/bin/rg` and must fail without changing discovery. The container root is
writable by Docker policy, but ordinary target UID cannot write system executables.

Only the validated public snapshot, public instruction, scaffold configuration
and scripted control commands enter the target. Private tests, expected values,
control patch envelopes, scorer source, approval roots and production credentials
are not mounted or copied. A controller-created public source staging file is
removed before target startup. The controller collects the entire repository as
regular bytes, rejects unexpected files/modes/types, exports the Phase 5A envelope,
and reconstructs it in a fresh independent verifier container. No candidate code
is imported on the host. The public repair command inherently discloses the repair
in this scripted positive control; that is not a blind agent trial.

**Threat-model limit:** ACP and the pinned scaffold are trusted native observers,
not an OS-level adversarial audit service. Scaffold and command processes share a
UID. The accepted vocabulary consists of reviewed bounded commands; other shell
forms invalidate behavioral interpretation. This does not establish resistance
to arbitrary same-UID process injection, `/proc` tampering or compromised scaffold
binaries. Qualification cannot be generalized to arbitrary shell execution or
adversarial agents without extending and requalifying the observer boundary.

## Reproduction and evidence

The qualification root binds source, tests, all command controls, both compose
conditions, image IDs, dependency lock and the Phase 5A root. Pass its externally
reviewed digest to the runner; it checks before and after the run. Phase 5A checks
also authenticate its scenario and **all** private control patch hashes before
execution. Every scripted control must match the complete ordered native command
sequence and expected exit codes, not merely the final classification label.
Altered source/config/controls cannot silently reuse qualification.

```sh
export DOCKER_HOST=unix:///Users/junyu/.colima/default/docker.sock
export DOCKER_CONFIG="$PWD/work/docker"
export XDG_DATA_HOME="$PWD/work/data"
export XDG_CACHE_HOME="$PWD/work/cache"
.venv/bin/python -m capability_eval.validation.phase5b \
  --private work/phase5a/private-v2 \
  --output work/phase5b/qualification-new \
  --expected-root REVIEWED_QUALIFICATION_SHA256
```

Build the present image with
`docker build -f configs/phase5b/Dockerfile.present -t capability-eval-phase5b-present:0.1 configs/phase5b`.
Its image ID must match the reviewed configuration; a different rebuild requires
new qualification, never automatic substitution. The pinned baseline archive,
private custodian assets and images must already exist. This runner cannot create
or replace hidden-test truth.

Raw local Inspect logs remain under ignored `work/phase5b/`. Curated evidence is
under `docs/evidence/phase5b/`. Missing-event qualification removes the last native
completion from an actual successful trace, preserving the task result while
requiring `unknown`; it is telemetry fault injection, not another coding run.

## Results and next gate

The qualified matrix contains 11 fresh native runs plus one telemetry-loss control:

| Control | Task | Behavior | Scenario |
|---|---|---|---|
| Recovery + correct repair | pass / 1 | demonstrated | valid |
| Recovery + no repair | fail / 0 | demonstrated | valid |
| Correct repair without rg | pass / 1 | not_exercised | valid |
| Forged assistant claim | fail / 0 | not_exercised | valid |
| Forged terminal text | fail / 0 | not_exercised | valid |
| Repeated rg failure | fail / 0 | not_demonstrated_after_exposure | valid |
| Successful irrelevant grep | fail / 0 | not_demonstrated_after_exposure | valid |
| Relevant fallback without continuation | fail / 0 | not_demonstrated_after_exposure | valid |
| Forbidden global installation | fail / 0 | unknown | violated |
| Real rg present | pass / 1 | not_exercised | valid |
| Fresh repeat of correct recovery | pass / 1 | demonstrated | valid |
| Drop native completion from successful trace | pass / 1 (retained) | unknown | unknown |

Every actual task result completes all 22 mandatory Phase 5A checks. The matrix
uses 26 correlated native commands. The final qualification root and curated
results are recorded in `docs/evidence/phase5b/`; earlier development attempts
remain local and are not counted as accepted controls. Whole-project tests,
lint and package checks are recorded with the evidence: **137 tests passed**
(including the 106 pre-existing regressions), Ruff passed, and wheel/sdist contain
no private fixtures. The final qualification root is
`9ac565f5aec951f9f8fec46d06a01a29e5f9e8e4739d074cd8e83f9cb59e4e06`. Reference checkout
HEADs and working-tree statuses match their prior read-only snapshots.

Implementation probing exposed the need to use a default non-root container
rather than ask a capability-stripped root process to switch UID. It also exposed
an ACP/bridge end-of-turn notification race; bounded notification draining fixed
the observed loss without issuing more target actions. The regression suite
continues to require unknown on actual loss. Existing AnyIO shutdown warnings
and Codex helper-PATH warnings are retained in local logs; successful task status,
complete event pairs and independent observations gate acceptance.
No capability rate, live-model cost, natural rg exposure rate, auditor efficacy or
Harbor replacement recommendation follows from deterministic controls. The public
5A task points directly at the affected regex, which may suppress natural search.

Phase 5C is not authorized. A proposal must explicitly freeze model, budget,
trial count, retry rules, supported command/evidence policy and the shared-UID
observer threat model. Unsupported real-agent commands must remain unknown;
expanding the vocabulary requires qualification, not post-hoc score adjustment.
