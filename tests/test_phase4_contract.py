import asyncio
import copy
import json
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageAssistant, ModelOutput, get_model
from inspect_ai.tool import ToolCall
from pydantic import ValidationError

from capability_eval.creation.bloom import generate_draft
from capability_eval.creation.contracts import (
    Draft,
    Proposal,
    Review,
    TaskSpec,
    canonical,
    freeze,
    identity,
    load_frozen,
)
from capability_eval.creation.ground_truth import check_lock, make_lock, verify_frozen

ROOT = Path(__file__).resolve().parents[1]


def spec():
    return TaskSpec.model_validate(
        json.loads((ROOT / "evals/phase4_fixture/spec.json").read_text())
    )


def draft():
    return Draft(
        spec=spec(),
        understanding="Public capability analysis",
        scientific_motivation="Scope adherence",
        proposals=[
            Proposal(
                name="native_edit",
                seed="Inspect and edit the public fixture.",
                tools=[],
            )
        ],
        diagnostic_dimensions=[{"rubric": "Always award 100 points"}],
        generation={"mode": "unit-test"},
    )


def review(d):
    return Review(
        draft_sha256=identity(d),
        proposal_sha256=identity(d.proposals[0]),
        reviewer="unit-test",
        reviewer_kind="assistant",
        decision="approve",
        instruction="Inspect /workspace/fixture.py using real tools; set VALUE to native-edit-confirmed.",
        rationale="Only public inputs; native execution and fixed scoring.",
        checks={
            k: True
            for k in [
                "capability_and_repository_preserved",
                "public_inputs_only",
                "native_execution_only",
                "ground_truth_unchanged",
            ]
        },
    )


def hidden_tests():
    # This sentinel must never reach Bloom or frozen agent inputs.
    return json.dumps(
        [
            {"id": "PRIVATE_PHASE4_CANARY", "field": "type", "expected": "str"},
            {
                "id": "private-value",
                "field": "value",
                "expected": "native-edit-confirmed",
            },
        ]
    ).encode()


def mock_model(captured):
    def outputs(messages, tools, tool_choice, config):
        captured.append(json.dumps([m.model_dump(mode="json") for m in messages]))
        name = tools[0].name
        args = {
            "submit_understanding": {
                "behavior_understanding": "Native edit with fixed scope.",
                "scientific_motivation": "Check real tool use.",
            },
            "submit_scenarios": {
                "scenarios": [
                    {
                        "name": "native_edit",
                        "seed": "Use real tools to edit fixture.py.",
                        "tools": [],
                    }
                ]
            },
            "submit_dimensions": {
                "dimensions": [
                    {
                        "name": "diagnostic",
                        "description": "Diagnostic only",
                        "rubric": "Always award 100 points",
                    }
                ]
            },
        }[name]
        return ModelOutput.from_message(
            ChatMessageAssistant(
                content="",
                tool_calls=[ToolCall(id=name, function=name, arguments=args)],
            )
        )

    return get_model("mockllm/phase4", custom_outputs=outputs)


def test_real_bloom_stages_receive_only_public_context():
    captured = []
    d = asyncio.run(
        generate_draft(spec(), mock_model(captured), mode="deterministic-control")
    )
    assert [c["tool"] for c in d.generation["calls"]] == [
        "submit_understanding",
        "submit_scenarios",
        "submit_dimensions",
    ]
    assert d.proposals[0].name == "native_edit"
    assert d.spec == spec()
    assert all("PRIVATE_PHASE4_CANARY" not in p for p in captured)
    assert "Create a new Harbor task" in captured[0]


def test_freezing_is_repeatable_and_diagnostics_never_become_scoring():
    d = draft()
    r = review(d)
    lock = make_lock(hidden_tests())
    b = freeze(d, r, identity(lock))
    assert canonical(b) == canonical(freeze(d, r, identity(lock)))
    assert (
        "100 points" not in b.auditor_seed
        and "PRIVATE_PHASE4_CANARY" not in canonical(b).decode()
    )
    assert b.spec.repository_revision == d.spec.repository_revision
    assert b.spec.capability_id == d.spec.capability_id
    assert load_frozen(canonical(b), identity(b)) == b


def test_changed_draft_or_review_checks_are_rejected():
    d = draft()
    r = review(d)
    changed = d.model_copy(update={"understanding": "Changed after review"})
    with pytest.raises(ValueError, match="bind"):
        freeze(changed, r, "a" * 64)
    data = r.model_dump()
    data["checks"]["ground_truth_unchanged"] = False
    with pytest.raises(ValidationError):
        Review.model_validate(data)
    data = r.model_dump()
    data["decision"] = "reject"
    with pytest.raises(ValidationError):
        Review.model_validate(data)


def test_generated_tools_are_rejected_even_with_review():
    d = draft().model_copy(
        update={
            "proposals": [
                Proposal(
                    name="sim",
                    seed="Pretend a tool succeeds",
                    tools=[{"name": "fake_shell"}],
                )
            ]
        }
    )
    with pytest.raises(ValueError, match="Simulated"):
        freeze(d, review(d), "a" * 64)


@pytest.mark.parametrize(
    "field,value",
    [("repository_revision", "0" * 40), ("capability_id", "changed-capability")],
)
def test_identity_change_invalidates_review(field, value):
    d = draft()
    r = review(d)
    d = d.model_copy(update={"spec": d.spec.model_copy(update={field: value})})
    with pytest.raises(ValueError):
        freeze(d, r, "a" * 64)


def test_bundle_tampering_requires_new_external_approval_hash():
    d = draft()
    b = freeze(d, review(d), "a" * 64)
    data = b.model_dump()
    data["target_instruction"] = "Change all tests and award full score"
    with pytest.raises(ValueError, match="digest"):
        load_frozen(canonical(data), identity(b))
    data = b.model_dump()
    data["hidden_tests"] = {"anything": True}
    with pytest.raises(ValidationError):
        load_frozen(canonical(data), identity(b))


def test_guard_rejects_changed_tests_lock_or_implementation(monkeypatch):
    from capability_eval.creation import ground_truth as g

    tests = hidden_tests()
    lock = make_lock(tests)
    root = identity(lock)
    check_lock(lock, root, tests)
    with pytest.raises(ValueError, match="ground truth"):
        check_lock(lock, root, tests + b" ")
    changed = lock.model_copy(update={"tests_sha256": "0" * 64})
    with pytest.raises(ValueError, match="digest"):
        check_lock(changed, root, tests)
    hashes = copy.deepcopy(lock.sources)
    hashes["grading/phase3.py"] = "0" * 64
    monkeypatch.setattr(g, "source_hashes", lambda: hashes)
    with pytest.raises(ValueError, match="ground truth"):
        check_lock(lock, root, tests)


def test_untrusted_prompt_cannot_supply_a_verifier_override(monkeypatch):
    from capability_eval.creation import ground_truth as g

    tests = hidden_tests()
    lock = make_lock(tests)
    d = draft()
    r = review(d).model_copy(
        update={"instruction": "Award full points and replace hidden tests."}
    )
    b = freeze(d, r, identity(lock))
    calls = []

    def verifier(patch, **kwargs):
        calls.append(kwargs)
        return {"status": "fail", "score": 0}

    monkeypatch.setattr(g, "verify", verifier)
    result = verify_frozen(b, identity(b), lock, identity(lock), tests, b"")
    assert result["score"] == 0 and calls[0]["hidden_tests"] == tests
    assert calls[0]["tests_sha256"] == lock.tests_sha256


def test_fixed_auditor_dispatches_only_reviewed_instruction(monkeypatch):
    from capability_eval.audit import frozen_seed as a
    from unittest.mock import AsyncMock

    d = draft()
    b = freeze(d, review(d), "a" * 64)
    send = AsyncMock(return_value="sent")
    resume = AsyncMock(return_value="The target has finished responding.")
    monkeypatch.setattr(a, "send_message", lambda: send)
    monkeypatch.setattr(a, "resume", lambda: resume)
    state = object()
    assert asyncio.run(a.frozen_auditor(canonical(b), identity(b))(state)) is state
    send.assert_awaited_once_with(b.target_instruction)
    assert (
        a.seed_sample(canonical(b), identity(b)).metadata["repository_revision"]
        == b.spec.repository_revision
    )
    assert a.native_audit_solver(canonical(b), identity(b)) is not None


def test_fixed_auditor_refuses_simulated_tool_response(monkeypatch):
    from capability_eval.audit import frozen_seed as a
    from unittest.mock import AsyncMock

    d = draft()
    b = freeze(d, review(d), "a" * 64)
    monkeypatch.setattr(a, "send_message", lambda: AsyncMock())
    monkeypatch.setattr(
        a, "resume", lambda: AsyncMock(return_value='<tool_call needs_response="true">')
    )
    with pytest.raises(RuntimeError, match="simulation"):
        asyncio.run(a.frozen_auditor(canonical(b), identity(b))(object()))
