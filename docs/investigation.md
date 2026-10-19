# Framework investigation — 2026-10-19

## Versions and evidence

The research extra pins `petri-dish==0.3.4`, `petri-bloom==0.2.6`, `inspect-petri==3.1.1`, and `inspect-ai==0.3.282`. The resolved Inspect SWE version is 0.2.71. All four installed together under Python 3.13.12; dependency checks passed. This establishes packaging compatibility only. No model, Docker, ACP, or end-to-end evaluation was run. PyPI metadata is retained in `evidence/package-metadata.json`; `uv.lock` contains exact transitive versions and distribution hashes. These are investigation-date versions, not a promise that future upgrades remain compatible.

## Native capabilities and custom work

| Component | Reuse natively | Work this experiment must supply |
|---|---|---|
| [Petri Bloom](https://meridianlabs-ai.github.io/petri_bloom/pipeline.html) | Behavior definitions, understanding, scenario ideation, variations, generated seeds and judge dimensions | Repository/capability contract, review and freezing of generated seeds; filter simulated-tool assumptions when exporting to Dish; deterministic tests are not generated ground truth |
| [Inspect Petri](https://meridianlabs-ai.github.io/inspect_petri/components/custom_task.html) | Seed dataset, auditor orchestration, target interface, approval/tool customization, transcript judge and viewer | Capability-specific auditor policy and constraints; objective results separate from judge opinion |
| [Petri Dish](https://meridianlabs-ai.github.io/petri_dish/reference.html) | Real scaffold target via Inspect SWE/ACP; Docker sandbox configuration; `dish_target(..., passthrough_tools=...)`; auditor tools and injection handling | Explicit native execution tool selection, immutable grounding, patch capture, filesystem/conversation consistency and verifier lifecycle |
| [Inspect AI](https://inspect.aisi.org.uk/) | Task/dataset/solver/scorer abstractions, model roles, logging, sandbox providers | Independent verifier boundary, trusted observation validation and status mapping |

Bloom's generated seeds can feed the audit, but its default evaluation path uses Petri targets and simulated tool definitions. Running Bloom's default task does not establish the proposed Dish coding workflow. Start with a manually frozen, reviewed seed; later validate Bloom as an authoring stage. Two user-supplied Harbor creation skills were located and inspected; they provide task-authoring guidance but no automatic issue-discovery implementation. See `creation-skill-assessment.md`. Keep authoring modular; do not implement a replacement generator now.

## Critical Dish finding

The official [Dish vs. Petri documentation](https://meridianlabs-ai.github.io/petri_dish/dish_vs_petri.html) explicitly describes simulated tool results as the default. A real scaffold does not by itself imply real bash/file edits. Installed 0.3.4 source confirms `dish_target` accepts a passthrough set, while the convenience task defaults do not select all filesystem tools for native execution. Its default sandbox disables network; this alone is not qualification of the complete agent and verifier boundaries.

The first experiment should compose the public Dish/Petri APIs and allow the exact native execution/edit tool names exposed by the pinned scaffold. Confirm an actual file mutation and export its bytes independently of the transcript. Tool names, delayed tool results and scaffold versions must be measured, not assumed. Avoid copying private `_target` implementation. If public APIs cannot provide a reliable seam, report the limitation before adding a broader adapter.

Auditor rollback/restart changes conversation state; no verified source establishes matching filesystem rollback for this setup. Disable those actions through the public auditor tool composition for the first run. Test this restriction. Do not claim a text-only rollback restores disk state. Auditor injection rewriting also needs restriction so repository identity and observed command failures remain factual.

## Scoring and isolation

Petri's judge evaluates behavioral transcripts; it cannot replace independent hidden tests. Inspect scorers can report trusted deterministic results alongside an optional auditor rubric. Preserve infrastructure errors, rejected submissions and invalid trials separately from task failures. Do not score missing/malformed observations as a clean zero or success.

Use two separately controlled execution domains, with the verifier created from the frozen base plus validated patch. The agent must never see verifier tests, oracle patches, private manifest fields or verifier logs during a trial. Candidate code must not control the trusted result aggregator. Preserve the legacy Python 3.8.20 test environment if `pytest_5786` is later reused; the framework controller requires modern Python.

## Hypothesis, not conclusion

The package APIs suggest a narrow integration is possible. Actual native tool execution, ACP/model routing, resource enforcement, patch completeness, hidden-test isolation and operational cost remain untested. A replacement recommendation requires the phase gates in the implementation plan, including an equivalent Harbor baseline and engineering-cost accounting. Native framework code may reduce maintenance, but additional adapters and dependency churn may outweigh that benefit.
