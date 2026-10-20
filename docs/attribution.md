# Attribution and reuse boundaries

Phase 1 installs pinned framework distributions; it does not vendor their source trees. Package metadata and distribution hashes are recorded in the evidence and lock file. Petri Dish, Petri Bloom and Inspect Petri declare MIT licenses; Inspect AI declares MIT. License terms for their dependencies remain applicable.

Harbor create-task and harbor-task-creator are authoring references from harbor-framework, licensed Apache-2.0 at the revisions in `evidence/creation-skills.json`. The creation workflow is an independently worded design adaptation of their authoring responsibilities. Source links and the license text are retained below. Phase 1 distributed no upstream skill or code verbatim. Phase 4 now includes the pinned create-task Skill unchanged, with its Apache-2.0 license, under `src/capability_eval/creation/references/`; all framework implementations remain installed dependencies.

The prior `jasonchenjy/evals` repository is referenced by commit and path only. Before future code/test reuse, identify its applicable rights and preserve original notices; an owner's authorization does not remove third-party license obligations. pytest source must retain its own license and provenance when incorporated. Hidden tests and sensitive historical evidence must not be published even if present in a reference repository.

Sources: [Harbor license](https://github.com/harbor-framework/harbor/blob/346d04c545ddad5d171606ee9f2a3db3e5838f18/LICENSE), [skills license](https://github.com/harbor-framework/skills/blob/b8cdcfb534b1aff65c7699eab4673530b1b4120a/LICENSE). A copy is at `licenses/Apache-2.0.txt` for the documented adaptation. No license for the new project's original code is selected in Phase 1; private hosting does not imply an open-source license.

Phase 2 installs the Apache-2.0 `@zed-industries/codex-acp==0.16.0` package in its dedicated container, with npm integrity metadata retained in the evidence. Inspect SWE 0.2.71 is reused as a pinned dependency. No original-evals implementation was copied. Docker CLI plugins were reused locally as ignored tooling; none are distributed in this repository.

Phase 4 generation evidence includes native Bloom/Petri diagnostic rubric text. Their MIT notices are retained at `licenses/Petri-Bloom-MIT.txt` and `licenses/Inspect-Petri-MIT.txt`. These diagnostics do not define deterministic scoring. The new authoring adapter is original code; no prior evaluation implementation or hidden test was copied.


## Phase 5A task source

Boltons is fetched as task data at `967864f89791509f9eb36b22b4579d36b72a6df2` from https://github.com/mahmoud/boltons. The complete BSD-3-Clause LICENSE (Mahmoud Hashemi and contributors) remains in every pinned snapshot; no source tree is committed to this distribution. The private reference control applies the source fix from `d12d86a4706aa4a367a91679b0ff9b6a572e5298`, authored by Guo Jiarui in upstream PR #475. Its attribution and license are retained with the locally provisioned source; the alternative control is independently constructed using literal Unicode separators. Private solution artifacts are not distributed in this repository.

### Phase 5B environment dependency

The present-rg control image installs Debian arm64 `ripgrep=13.0.0-4+b2` from
Debian bookworm, retaining the package's copyright/license files in the image.
No ripgrep source is vendored. The absent condition retains the pinned Phase 2
image. The ACP observer calls installed Inspect SWE/Petri APIs and scopes a
notification-sink override; no upstream package source is edited or copied.
