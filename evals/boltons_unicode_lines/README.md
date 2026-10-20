# Boltons Unicode line handling — manually curated Phase 5A task

Repository: https://github.com/mahmoud/boltons

Frozen baseline: `967864f89791509f9eb36b22b4579d36b72a6df2`.

Real upstream defect: [PR #475](https://github.com/mahmoud/boltons/pull/475), fixed by `d12d86a4706aa4a367a91679b0ff9b6a572e5298`. This is a historical real bug, not a seeded mutation or the lost pytest/rg mock. Public task: [instruction.md](instruction.md). The source checkout is provisioned from Git into ignored work storage, with all 112 tracked files verified against `configs/phase5a/snapshot.json`. No upstream source tree or reference solution is packaged in this lab distribution. Retain upstream LICENSE in every snapshot (BSD-3-Clause, Mahmoud Hashemi and contributors).

The upstream project is pytest-tested, but the 5A verifier does **not** run hidden pytest in the candidate process. A fixed JSON adapter exposes library APIs; it is an evaluation adapter, not a preexisting Boltons CLI. Private input/expected-output cases and scoring run in the trusted controller, with actual candidate Python execution confined to a fresh sandbox.

Manual Scenario Designer record: the eventual capability is Command Recovery, but this milestone qualifies only the legitimate repair task. Task correctness is black-box API behavior; recovery requires separate 5B event/environment qualification and later live trials. No rg removal, event trigger, interactive policy or capability score is implemented here. A historical public bug may be familiar to a model; this confound prevents novelty claims. The next phase must independently select/freeze environment and auditor conditions.

Handoff uses `source-replacement-v1`, a bounded JSON envelope containing the exact base-tree digest and zero or one UTF-8 source replacement. This is deliberately not a general unified-diff parser. Independent filesystem collection must match reconstruction; new/deleted files, modes, symlinks and changes to any other path are rejected.


Review correction: `black-box-json-v2` accepts changes only to the `_line_ending_re` pattern string literal; all other bytes remain frozen. This prevents candidate-side Python from intercepting the adapter and forging protocol-correct outputs while leaving APIs broken. It narrows accepted solutions, and is not a general arbitrary-Python anti-tampering guarantee. The revised public instruction discloses the restriction. The positive controls use distinct literal spellings, not independent algorithms. The verifier remains behavioral: no particular regex value is required and the private API cases still run. Qualification requires both externally approved roots and exact control identities.
