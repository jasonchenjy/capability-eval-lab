# Architecture v2 approval and scope record

On 2026-10-19 the user approved Architecture v2 with two amendments:

1. Evaluation Scenario Designer is the first-class central creation decision maker, coordinating Task, Environment Scenario and Auditor Behavior generators. It remains manually curated/design-only in Phase 5A.
2. Verifier architecture has a minimal versioned contract distinguishing black-box and repository-test strategies. Only narrow black-box verification is implemented in 5A; repository-level pytest verification is design-only with a distinct threat model. The Phase 3 AST verifier is not generalized.

The user authorized Phase 5A only: a real pinned defect, legitimate task, independent black-box verifier, handoff/reconstruction, controls, isolation, provenance, tests, commit and push. No live models, 5B/5C, autonomous designer, interactive auditor or Harbor comparison. Original repositories remain read-only.

The proposal files were previously uncommitted; their exact pre-amendment bytes are preserved here rather than pretending they existed in earlier Git history. Their relative links were authored relative to docs/. SHA-256 identities:

- `original-architecture-v2-proposal.md`: `858f5499a5f6c92d577ede9464797d677e4c0247fe8bfb31d46b90e60d02b0b1`
- `original-roadmap-v2-proposal.md`: `bc8b69498b19914fb69d92c0a4a67c2a5f54fa14bcad4bb9b185faf053d45523`

Approval applies to the revised architecture, not to unimplemented roadmap milestones.
