# pytest command recovery — planned new equivalent case

Status: design placeholder only. The original TODO-search/rg mock was not located. This directory is reserved for a newly constructed pytest-based scenario, as authorized for planning by the user; it is not pytest_5786 and is not a recovered historical benchmark.

Planned contract: a real coding agent encounters unavailable `rg`, recovers with a legitimate search alternative, fixes a TODO-linked bug, and submits a real patch. Independent hidden tests determine correctness; actual command receipts determine recovery. A successful patch without an attempted missing-rg command is not evidence of recovery. See `docs/implementation-plan.md` for controls and approval gates.

No prompt, hidden test, oracle, sandbox or runtime is implemented in Phase 1.
