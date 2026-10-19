# Planned reuse of Harbor task-authoring guidance

This Phase 1 design adapts the responsibilities described by Harbor's Apache-2.0 create-task and harbor-task-creator skills; see `creation-skill-assessment.md` for pinned references. It is documentation, not an installed or executable replacement Skill.

1. A curator selects a repository revision and an issue/specification tied to an explicit capability. Record provenance and reproduction evidence. Automatic issue discovery is an unresolved upstream stage and must not be implied by the authoring skill.
2. Use upstream authoring guidance to make the public problem statement precise and independently define the verifier contract, reference solution, negative controls and environment requirements.
3. Export only public source and instructions to the agent image. Keep hidden checks and oracle patches outside its filesystem and context. Build pinned verifier dependencies before the trial rather than installing them during grading.
4. Map the reviewed capability contract to a Petri seed. Bloom can propose scenarios/variations later, subject to review; it must not redefine expected correctness based on target performance.
5. Run the independent verifier against validated patch bytes in a fresh frozen base. Preserve mandatory-vs-diagnostic and infrastructure-vs-submission distinctions.
6. Qualify positive, alternative, no-op and broken controls, then freeze artifacts before agent trials. Record exact source and dependency identities.

Future creation input should include capability, repository URL/SHA, selected issue/specification, license/provenance, public payload allowlist and private verifier reference. Future output should include reviewed public task, frozen seed, private verification manifest and qualification evidence. These are proposed interface responsibilities, not schemas or code implemented in Phase 1.
