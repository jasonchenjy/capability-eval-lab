# Eval Creation Skill assessment

Inspected on 2026-10-19. The user supplied two candidate skills. Neither can be identified conclusively as the exact historical skill used for the earlier task, but both are relevant authoring references.

## Verified scope

| Workflow stage | Harbor `create-task` | Standalone `harbor-task-creator` |
|---|---|---|
| Capability + GitHub repository input | No defined input schema or implemented repository analysis pipeline | No defined input schema or repository analysis pipeline |
| Automatic issue discovery | Not provided by the inspected skill or invoked init implementation | Not provided; no discovery script in the skill package |
| Eval task generation | Agent-guided writing, CLI templates for prompt, environment, verifier and solution | Agent-guided writing plus worked examples and config reference |
| Verifier / hidden tests | Authoring guidance, pytest/RewardKit/custom options, separate verifier configuration | Authoring guidance, pytest/custom examples, post-agent test upload model |
| Qualification | Oracle verification and optional agent trial | Oracle verification and quality-check rubric |

The implementation evidence is `src/harbor/cli/tasks.py:init` delegating to `src/harbor/cli/init.py:_init_task`: it copies instruction/environment/tests/solution templates and creates configuration. It does not accept a capability/repository pair, query GitHub issues, rank bugs, or synthesize repository-specific hidden tests. The standalone skill contains only SKILL.md and two Markdown references; there is no bundled discovery implementation. Natural-language authoring guidance can help an agent write tests, but is not an autonomous issue-mining pipeline.

Pinned sources:

- [Harbor create-task](https://github.com/harbor-framework/harbor/blob/346d04c545ddad5d171606ee9f2a3db3e5838f18/skills/create-task/SKILL.md)
- [Harbor init implementation](https://github.com/harbor-framework/harbor/blob/346d04c545ddad5d171606ee9f2a3db3e5838f18/src/harbor/cli/init.py)
- [Harbor task command](https://github.com/harbor-framework/harbor/blob/346d04c545ddad5d171606ee9f2a3db3e5838f18/src/harbor/cli/tasks.py)
- [Standalone task creator](https://github.com/harbor-framework/skills/blob/b8cdcfb534b1aff65c7699eab4673530b1b4120a/skills/harbor-task-creator/SKILL.md)
- [Examples](https://github.com/harbor-framework/skills/blob/b8cdcfb534b1aff65c7699eab4673530b1b4120a/skills/harbor-task-creator/references/example-tasks.md) and [configuration reference](https://github.com/harbor-framework/skills/blob/b8cdcfb534b1aff65c7699eab4673530b1b4120a/skills/harbor-task-creator/references/task-toml-reference.md)

## Reuse decision

Prefer the current Harbor create-task skill as an upstream authoring reference. Reuse its separation of public instruction, environment, private verifier, reference solution and oracle qualification. The experiment's adaptation is documented in `creation-workflow.md`; no replacement Skill, task generator, discovery service or Harbor runtime integration is implemented in Phase 1. The skills' questions about grading and environment are already answered by the user's independent hidden-test and deterministic-scoring requirements.

Keep issue selection as a separate modular input: initially a curator supplies a frozen issue/specification and repository revision. Any later automated discovery component must be separately designed, evaluated for issue relevance/reproducibility and approved. Bloom's behavior ideation does not fill this repository issue-discovery gap.

## Do not copy examples blindly

The standalone skill's pytest example appends `|| true` and then reads `PIPESTATUS[0]`; this loses the failing pytest status. A local shell probe `false || true` followed by reading `PIPESTATUS[0]` returned 0. A future verifier must capture the original exit status immediately or branch directly on the command, and test a failing control.

The two skills also describe different Harbor-era CLI/configuration conventions. Pin the actual tool version before using their command examples. Installing verifier dependencies at run time and uploading tests into a shared agent environment do not meet this experiment's frozen, independent-verifier contract. Missing reward data is an invalid run here, not an invented numeric reward. No upstream file was changed.

## Phase 4 reuse

The pinned Harbor create-task Skill is now packaged with its Apache-2.0 license and supplied to native Bloom authoring calls. Its hash is checked before use. This confirms reuse of the inspected reference, not identification of the exact historical skill. See `phase-4-report.md` for the implemented adaptation and explicit review boundary.
