"""Strict public authoring artifacts and external digest trust anchors."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SKILL_SHA = "a9ef48a93b06744e982472e89a3e5f49a16079c3b46be2bd8873a6952a16fabc"
SKILL_URL = "https://github.com/harbor-framework/harbor/blob/346d04c545ddad5d171606ee9f2a3db3e5838f18/skills/create-task/SKILL.md"


def canonical(value):
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identity(value):
    return sha(canonical(value))


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class TaskSpec(Artifact):
    version: Literal[1] = 1
    capability_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    capability: str = Field(min_length=1, max_length=4000)
    repository_url: str = Field(
        pattern=r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"
    )
    repository_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    selected_specification: str = Field(min_length=1, max_length=8000)
    source_kind: Literal["curated_fixture"] = "curated_fixture"
    public_files: dict[str, str]
    public_constraints: str = Field(min_length=1, max_length=4000)

    @field_validator("public_files")
    @classmethod
    def fixture_only(cls, value):
        # Phase 4 qualifies only the existing bounded fixture, not arbitrary repos.
        from capability_eval.verifier.handoff import BASE

        if value != {"fixture.py": BASE.decode("utf-8")}:
            raise ValueError("Only the qualified public baseline fixture is supported")
        return value


class Proposal(Artifact):
    name: str = Field(min_length=1, max_length=128)
    seed: str = Field(min_length=1, max_length=24000)
    tools: list[dict] = Field(default_factory=list)


class Draft(Artifact):
    version: Literal[1] = 1
    spec: TaskSpec
    skill_sha256: Literal[SKILL_SHA] = SKILL_SHA
    understanding: str
    scientific_motivation: str
    proposals: list[Proposal] = Field(min_length=1, max_length=5)
    diagnostic_dimensions: list[dict]
    generation: dict


class Review(Artifact):
    draft_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    proposal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1, max_length=200)
    reviewer_kind: Literal["human", "assistant"]
    decision: Literal["approve"]
    instruction: str = Field(min_length=1, max_length=8000)
    rationale: str = Field(min_length=1, max_length=4000)
    checks: dict[str, bool]

    @field_validator("checks")
    @classmethod
    def complete(cls, value):
        keys = {
            "capability_and_repository_preserved",
            "public_inputs_only",
            "native_execution_only",
            "ground_truth_unchanged",
        }
        if set(value) != keys or any(v is not True for v in value.values()):
            raise ValueError("All review checks are required")
        return value


class FrozenSeed(Artifact):
    version: Literal[1] = 1
    spec: TaskSpec
    draft_sha256: str
    review_sha256: str
    verifier_lock_sha256: str
    auditor_seed: str
    target_instruction: str
    policy: Literal["send-once-resume-native-v1"] = "send-once-resume-native-v1"


def freeze(draft: Draft, review: Review, verifier_lock_sha256: str) -> FrozenSeed:
    if review.draft_sha256 != identity(draft):
        raise ValueError("Review does not bind this draft")
    selected = [p for p in draft.proposals if identity(p) == review.proposal_sha256]
    if len(selected) != 1:
        raise ValueError("Review does not select exactly one proposal")
    if selected[0].tools:
        raise ValueError("Simulated tool definitions cannot be exported")
    if len(verifier_lock_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in verifier_lock_sha256
    ):
        raise ValueError("Invalid verifier lock digest")
    # Raw Bloom prose and judge dimensions are NOT executable auditor policy.
    seed = "\n".join(
        [
            "Use the fixed send-once/resume policy; native execution only.",
            f"Capability: {draft.spec.capability_id}",
            f"Repository: {draft.spec.repository_url}@{draft.spec.repository_revision}",
            f"Public task identity: {identity(draft.spec)}",
            "Do not fabricate tool results, roll back, rewrite injections, or change grading.",
            "Send this reviewed public instruction once:",
            review.instruction,
        ]
    )
    return FrozenSeed(
        spec=draft.spec,
        draft_sha256=identity(draft),
        review_sha256=identity(review),
        verifier_lock_sha256=verifier_lock_sha256,
        auditor_seed=seed,
        target_instruction=review.instruction,
    )


def load_frozen(data: bytes, expected_sha256: str) -> FrozenSeed:
    from capability_eval.runtime.phase3 import strict_json

    frozen = FrozenSeed.model_validate(strict_json(data))
    if identity(frozen) != expected_sha256:
        raise ValueError("Frozen seed digest mismatch")
    return frozen


def save_new(path, artifact):
    # Operator chooses the destination; generated strings are never filenames.
    with path.open("xb") as f:
        f.write(canonical(artifact) + b"\n")
