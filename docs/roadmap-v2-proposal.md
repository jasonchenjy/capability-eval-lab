# Roadmap v2 proposal — decision before Phase 5

**Status: Architecture v2 approved with amendments; Phase 5A complete and Phase 5B authorized. Phase 5C and later milestones remain proposals.** The original proposal baseline is `6a441fc21a67ad59e0e8660ebb63228c7502f636`, 2026-10-19. This document supplements [the existing implementation plan](implementation-plan.md), preserving the original proposal and subsequent decision history below. Architecture and contracts are specified in [architecture-v2-proposal.md](architecture-v2-proposal.md).

## Decision on original Phase 5

| Option | Benefit | Cost/risk | Recommendation |
|---|---|---|---|
| A — unchanged regression and comparison | Quickly seeks matched runtime evidence | Assumes repository verification and behavioral scoring that the toy fixture has not established; bundles discovery, new verifier, recovery and comparative statistics | NO-GO unchanged |
| B — full creation framework first | Broad automation and unified abstractions | Generalizes before one real capability experiment is qualified; spends effort on discovery/intervention tooling before the hardest verifier/event questions are answered | NO-GO |
| C — architecture alignment, then focused recovery slice | Tests the key runtime, isolation and behavioral claims with bounded scope | Defers full automation and comparative performance claims | Recommended, pending approval |

Phase 5 should remain primarily **runtime and measurement validation**, with only the task/contract/qualification work necessary to make that validation meaningful. Move Harbor comparison to a later separately approved phase after one common task/verifier/environment/evidence contract runs reliably. Do not weaken the original comparison gate silently: label it deferred and preserve it as a prerequisite for any replacement recommendation.

## Minimum end-to-end slice

One curator-selected capability/repository/bug → one reviewed candidate specification → public task + fixed absent-rg environment + passive auditor policy → independently provisioned private verifier and controls → qualified frozen bundle → one real coding agent via Dish/Inspect → admitted patch → clean candidate sandbox + separate private black-box pytest driver → task outcome and recovery evidence separately.

Bloom may draft the public scenario through the existing adapter; a live generation run is not needed to qualify infrastructure. Record whether a draft is curated, deterministic control or live-generated. The source repository must actually be materialized at its pinned SHA; Phase 4's provenance-only fixture is insufficient. The next slice is not fully automated discovery, general Python verification or an auditor efficacy study.

## Proposed small phases and approval gates

Each row is independently reviewable. Stop, report evidence and request authorization for the next row; approval of this proposal is not blanket execution approval. Implementation commits/pushes belong to the experimental repo only after validation.

| Proposed milestone | Deliverable | Exit criteria / stop condition |
|---|---|---|
| **5A — qualify one task and verifier offline** | Narrow v2 contract, actual pinned repository snapshot, public task, private CLI-interface test driver, patch admission, reference/negative controls | Meets detailed next-phase criteria below without a live model. Stop if hidden tests require unsafe in-process candidate imports or task truth cannot be established. |
| **5B — environment and evidence qualification** | rg-absent/present condition manifests, passive structured auditor, authoritative event capture and recovery classifier | Scripted real native controls prove missing rg, fallback, no-exposure, fake text, repeated failure, irrelevant fallback, missing events and forbidden installation are distinguished. No private material in target context. Stop if event authenticity cannot be established. |
| **5C — passive live vertical slice** | Small explicitly budgeted real-agent run set and independent verification report | All validity gates checked on actual runs; correct patches genuinely verified; outcome/exposure/recovery reported separately. Predeclare model/config, trial count, budget, seeds and retry policy before running. No exposure is a valid negative finding, not permission to keep spending until success. |
| **6A — deterministic controlled auditor** | One frozen event-triggered action and condition matrix | Identical task/verifier can run passive vs controlled; trigger timing, exactly-once action, reset and denylist validated with real tools and deterministic controls. No live efficacy claim required. |
| **6B — bounded interactive auditor** | One reviewed policy with narrow action vocabulary and intervention ledger | LLM suggestions cannot exceed permissions/budgets or touch truth. Injection/forged-event controls pass. Any live assisted trials require a fresh budget and are never pooled with passive results. |
| **7 — creation diversity across a second scenario** | Evidence-backed candidate discovery/ranking and independently varied environment/auditor drafts | At least a second genuinely different bug/condition qualifies; validate relevance, reproducibility, duplicate detection and verifier coverage. Measure creation/review cost and rejected candidates. Reuse Skill/Bloom guidance, not a new orchestration framework by default. |
| **8 — matched runtime comparison** | Harbor vs Inspect/Dish, optionally Inspect-only, on the same qualified scenarios | Match source/task/verifier/agent/budgets/conditions and disclose unavoidable scaffold differences. Preregister repeats and report uncertainty, invalid rates, exposure, recovery, correctness, time, tokens/cost availability and engineering/maintenance burden. No replacement claim from one smoke run. |

Milestone numbering is a proposed replacement decomposition, not a claim that prior approvals extend to these tasks. Existing Phase 2–4 fixtures and evidence remain regression assets with their original scope.

## Next implementation milestone: 5A acceptance criteria

1. **Contract and provenance:** selected repository URL, full SHA, license and materialized tree digest recorded; selected bug has a reproducible failure. Mark a constructed fallback explicitly. Schema separates public, auditor and private projections. Reject unknown fields, unsupported patch paths and digest mismatch.
2. **Task truth:** public instruction describes a legitimate bug without a solution. Baseline/no-op fails targeted private checks; reference and an independently different valid repair pass; wrong and narrow hardcoded repairs fail. All declared mandatory checks run. Private tests assess behavior, not exact patch text.
3. **Independent verification:** private pytest driver never imports candidate code into its process. Candidate runs against a fresh reconstructed snapshot through a bounded documented interface; expected values/assertions remain driver-only. Prove fake success output, forged result JSON, abrupt exit, malformed protocol, timeout and missing tests cannot pass. Candidate functional exceptions and infrastructure errors have distinct frozen classifications.
4. **Patch handoff:** allow only reviewed regular source files; reject traversal, symlinks, mode changes, hidden/public test or harness edits, unsupported encodings and oversized patches. Reconstructed files match independently collected target files. No repository hooks or candidate code execute on the host.
5. **Isolation:** inspect actual images/mounts/environment; hidden tests, reference patch, credentials and approval roots absent from public snapshots and candidate filesystem. Candidate has no network/driver filesystem/result-file access; limits and cleanup confirmed. Document that individual black-box test inputs are necessarily visible to candidate code.
6. **Reproducibility:** pin base/image/dependencies/driver/scorer/contract and approved-root digests; repeated deterministic controls agree from fresh state. Changing any protected artifact invalidates qualification. No live model calls needed.
7. **Reviewability:** produce control matrix, curated evidence, limitations and source manifest; preserve Phase 2–4 regressions. A changed accepted ground truth requires a new version and review, never a runtime mutation. No automatic benchmark acceptance from an LLM rubric or checklist.

5A proves repository task/verifier readiness, **not** command-recovery measurement. 5B proves condition/evidence plumbing. Only 5C attempts real-agent recovery. A complete minimum slice requires all three; do not report 5A as full Phase 5 completion.

## Vertical-slice result acceptance

For 5C, “demonstrated recovery” requires a target-issued real rg failure, relevant successful fallback and continued execution, all linked to controller-owned events. Task tests passing alone cannot satisfy it. If no run attempts rg, report task outcomes plus not_exercised and conclude that this run set did not validate recovery. A separately approved forced-exposure variant may be studied later; it must not overwrite the original results.

Infrastructure-valid pass/fail rates exclude invalid trials only with explicit counts and reasons. Report exposure across all eligible valid runs, recovery conditional on exposure, unknown evidence counts and assistance separately. Do not treat missing costs as zero; distinguish deterministic-inference plumbing measurements from live model cost. One successful live run supports feasibility, not robust capability or comparative superiority.

## Decisions to freeze before code

- Repository/bug and task provenance; private-test custodian and review authority.
- CLI/JSON candidate interface and isolation threat model; no hidden in-process imports.
- Source edit allowlist, snapshot reconstruction and encoding/resource policies.
- Independent environment/policy IDs; actual image digest; rg absence and installation restriction.
- Structured native-event capture, event schema, exposure/recovery predicate and unknown semantics.
- Passive initial mode, intervention prohibition and reset; future controlled/interactive bounds remain unapproved.
- Result dimensions, aggregation rules, qualification controls, approval root and versioning procedure.
- Before 5C separately: target model/harness, call/time/token budget, sample count, retry/exclusion policy and evidence retention.

## Explicitly out of scope for the focused slice

Automatic GitHub issue mining at scale; universal test synthesis; arbitrary in-process Python hidden verification; multi-agent creation orchestration; production benchmark hosting; unrestricted auditor tools; transcript/filesystem rollback; dynamic environment mutation; broad model rankings; replacing Harbor; matched runtime/cost comparisons; identifying the lost historical rg task by assumption. The original Harbor + ReviewKit repositories remain read-only references.

## Open questions and tradeoffs requiring review

The exact repository and defect remain to be selected. If no suitable black-box bug exists, either choose another repository or revisit verification scope explicitly. Final hidden-suite authorship must be independent from ordinary creation agents; an automated privileged author would require a clearly approved exception. Reliable observation of shell pipelines/aliases may need a narrow initial supported-command policy; do not infer native failure from stdout alone. Natural exposure versus a prompted initial rg attempt measures different behavior and needs separate labels.

LangChain eval-engineering guidance may help later discovery and qualification, but no dependency or workflow migration is justified for 5A. The old phase documents contain historical status statements (for example Phase 1 architecture says no integration); this proposal's reuse map supplies the current assessment without rewriting history.

**Recommendation: NO-GO for original Phase 5 unchanged; recommend Option C. First concrete implementation milestone (now authorized): 5A, a pinned real bug with qualified independent black-box verification and positive/negative controls, without live model runs.**

## Approval record — 2026-10-19

The user approved Architecture v2 with a first-class central Evaluation Scenario Designer and an extensible, versioned Verifier Contract. The original roadmap is preserved in [the decision archive](decisions/original-roadmap-v2-proposal.md). Phase 5A is GO under its seven existing acceptance criteria. The designer remains manually curated/design-only; only a narrow black-box strategy is implemented. Repository Test Verifier remains design-only with a separate threat model; no universal AST interpreter or generic plugin framework is authorized. A bounded JSON adapter over a real repository API is allowed by the black-box contract; future coding tasks need not use this interface. Stop after validated 5A changes are committed/pushed and reported. No live models, interactive auditor, Harbor comparison or 5B/5C implementation.

## Subsequent authorization — Phase 5B

After the 5A review fixes, the user authorized Phase 5B environment/evidence
qualification using deterministic controls and a passive auditor only. See
[Phase 5B report](phase-5b-report.md) for the scoped native observer, command
vocabulary, conditions, acceptance evidence and remaining threat-model limits.
This subsequent authorization supersedes the earlier *execution status* saying
5B was unapproved, while preserving that historical decision. Phase 5C and live
model calls remain unapproved; no interactive auditor is implemented.
