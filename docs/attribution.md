# Attribution and reuse boundaries

Phase 1 installs pinned framework distributions; it does not vendor their source trees. Package metadata and distribution hashes are recorded in the evidence and lock file. Petri Dish, Petri Bloom and Inspect Petri declare MIT licenses; Inspect AI declares MIT. License terms for their dependencies remain applicable.

Harbor create-task and harbor-task-creator are authoring references from harbor-framework, licensed Apache-2.0 at the revisions in `evidence/creation-skills.json`. The creation workflow is an independently worded design adaptation of their authoring responsibilities. Source links and the license text are retained below. No upstream skill or code is distributed verbatim in the tracked project.

The prior `jasonchenjy/evals` repository is referenced by commit and path only. Before future code/test reuse, identify its applicable rights and preserve original notices; an owner's authorization does not remove third-party license obligations. pytest source must retain its own license and provenance when incorporated. Hidden tests and sensitive historical evidence must not be published even if present in a reference repository.

Sources: [Harbor license](https://github.com/harbor-framework/harbor/blob/346d04c545ddad5d171606ee9f2a3db3e5838f18/LICENSE), [skills license](https://github.com/harbor-framework/skills/blob/b8cdcfb534b1aff65c7699eab4673530b1b4120a/LICENSE). A copy is at `licenses/Apache-2.0.txt` for the documented adaptation. No license for the new project's original code is selected in Phase 1; private hosting does not imply an open-source license.
