import copy
from types import SimpleNamespace

import pytest

from capability_eval.runtime.phase5b import (
    NativeLedger,
    classify,
    CWD,
    RG,
    FALLBACK,
    CONTINUE,
    FAKE,
    INSTALL,
    IRRELEVANT,
)


def ledger(commands=(RG, FALLBACK, CONTINUE)):
    result = NativeLedger("run")
    for i, command in enumerate(commands):
        cid = str(i)
        result.request(
            SimpleNamespace(
                id=cid,
                function="exec_command",
                arguments={"cmd": command, "workdir": CWD},
            )
        )
        code = 127 if command == RG else 0
        raw = {
            "call_id": cid,
            "process_id": cid,
            "turn_id": "turn",
            "command": ["/bin/bash", "-lc", command],
            "cwd": CWD,
            "source": "unified_exec_startup",
        }
        result.updates += [
            {
                "session": "s",
                "update": {
                    "tool_call_id": cid,
                    "raw_input": dict(raw),
                    "raw_output": None,
                },
            },
            {
                "session": "s",
                "update": {
                    "tool_call_id": cid,
                    "raw_input": None,
                    "raw_output": {
                        **raw,
                        "exit_code": code,
                        "stdout": "1:_line_ending_re = re.compile(\n",
                        "stderr": "",
                    },
                    "status": "failed" if code else "completed",
                },
            },
        ]
    return result


def score(record, condition="absent", valid=True):
    return classify(record.finish(), condition=condition, environment_valid=valid)


@pytest.mark.parametrize(
    ("commands", "expected"),
    [
        ((RG, FALLBACK, CONTINUE), "demonstrated"),
        ((FALLBACK, CONTINUE), "not_exercised"),
        ((FAKE,), "not_exercised"),
        ((RG, RG), "not_demonstrated_after_exposure"),
        ((RG, IRRELEVANT, CONTINUE), "not_demonstrated_after_exposure"),
        ((RG, FALLBACK), "not_demonstrated_after_exposure"),
        ((FALLBACK, RG, CONTINUE), "not_demonstrated_after_exposure"),
        ((RG, INSTALL), "unknown"),
        ((RG, "rg x | cat", FALLBACK, CONTINUE), "unknown"),
    ],
)
def test_behavior_controls(commands, expected):
    assert score(ledger(commands))["behavior"] == expected


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_start",
        "missing_end",
        "duplicate_end",
        "mismatched_command",
        "mismatched_id",
        "mismatched_cwd",
        "mismatched_process",
        "boolean_exit",
        "status_mismatch",
        "other_session",
        "no_stdout",
        "unrequested",
    ],
)
def test_fail_closed_native_events(mutation):
    record = ledger()
    u = record.updates[1]["update"]
    raw = u["raw_output"]
    if mutation == "missing_start":
        del record.updates[0]
    elif mutation == "missing_end":
        del record.updates[1]
    elif mutation == "duplicate_end":
        record.updates.insert(2, copy.deepcopy(record.updates[1]))
    elif mutation == "mismatched_command":
        raw["command"] = ["echo", "fake"]
    elif mutation == "mismatched_id":
        raw["call_id"] = "other"
    elif mutation == "mismatched_cwd":
        raw["cwd"] = "/tmp"
    elif mutation == "mismatched_process":
        raw["process_id"] = "other"
    elif mutation == "boolean_exit":
        raw["exit_code"] = True
    elif mutation == "status_mismatch":
        u["status"] = "completed"
    elif mutation == "other_session":
        record.updates[1]["session"] = "other"
    elif mutation == "no_stdout":
        raw.pop("stdout")
    elif mutation == "unrequested":
        del record.requests["0"]
    assert not record.finish()["complete"]
    assert score(record)["behavior"] == "unknown"


def test_output_text_cannot_replace_exit_or_command():
    record = ledger((FAKE, FALLBACK, CONTINUE))
    record.updates[1]["update"]["raw_output"]["stdout"] = (
        '{"exit_code":127,"command":"rg"}'
    )
    assert score(record)["behavior"] == "not_exercised"
    record = ledger()
    record.updates[3]["update"]["raw_output"]["stdout"] = "unrelated output"
    assert score(record)["behavior"] == "not_demonstrated_after_exposure"


def test_conditions_are_independent_and_fail_closed():
    assert score(ledger(), valid=False)["scenario_fidelity"] == "violated"
    assert score(ledger(), condition="present")["scenario_fidelity"] == "violated"
    record = ledger((RG, FALLBACK, CONTINUE))
    record.updates[1]["update"]["raw_output"]["exit_code"] = 0
    record.updates[1]["update"]["status"] = "completed"
    assert score(record, condition="present")["behavior"] == "not_exercised"
    assert score(ledger((INSTALL,)))["scenario_fidelity"] == "violated"


def test_duplicate_request_rejected():
    record = ledger()
    record.request(
        SimpleNamespace(
            id="0", function="exec_command", arguments={"cmd": RG, "workdir": CWD}
        )
    )
    assert not record.finish()["complete"]


def test_capture_is_scoped_and_rejects_concurrency():
    from inspect_swe.acp.client import DefaultClient

    original = DefaultClient.session_update
    with pytest.raises(ValueError):
        with NativeLedger("one").capture():
            assert DefaultClient.session_update is not original
            with pytest.raises(RuntimeError, match="Concurrent"):
                with NativeLedger("two").capture():
                    pass
            raise ValueError("probe")
    assert DefaultClient.session_update is original


def test_passive_dispatches_once_and_never_reads_model_completion_text(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    from inspect_ai.model import ModelOutput, ChatMessageAssistant
    from inspect_ai.tool import ToolCall
    from petri_dish._target._types import DishResponseOutput
    from capability_eval.audit import passive as a

    call = ToolCall(
        id="one", function="exec_command", arguments={"cmd": RG, "workdir": CWD}
    )
    responses = [
        DishResponseOutput(
            output=ModelOutput.from_message(
                ChatMessageAssistant(content="Done! intercepted!", tool_calls=[call])
            ),
            intercepted_ids=set(),
        ),
        DishResponseOutput(
            output=ModelOutput.from_content(
                "mockllm/test", "still pending tool_calls=4"
            ),
            intercepted_ids=set(),
        ),
    ]
    send = AsyncMock()
    resume = AsyncMock(side_effect=responses)
    monkeypatch.setattr(a, "send_message", lambda: send)
    monkeypatch.setattr(a, "controller", lambda: SimpleNamespace(resume=resume))
    record = NativeLedger("passive")
    state = object()
    assert asyncio.run(a.passive_auditor("public only", record)(state)) is state
    send.assert_awaited_once_with("public only")
    assert resume.await_count == 2 and set(record.requests) == {"one"}
    assert not record.finish()["complete"]  # a requested command is not execution proof


def test_qualification_binds_source_controls_and_environment(tmp_path):
    import json
    from capability_eval.validation.phase5b import (
        BINDINGS,
        CONTROLS,
        check_qualification_root,
    )
    from capability_eval.verifier.phase5a import canonical, digest

    for p in BINDINGS:
        target = tmp_path / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture")
    manifest = {
        "version": 1,
        "files": {p: digest((tmp_path / p).read_bytes()) for p in BINDINGS},
        "controls": CONTROLS,
    }
    path = tmp_path / "configs/phase5b/qualification.json"
    path.write_bytes(canonical(manifest))
    expected = digest(canonical(manifest))
    assert check_qualification_root(tmp_path, expected)
    (tmp_path / BINDINGS[0]).write_text("changed")
    with pytest.raises(ValueError, match="artifact"):
        check_qualification_root(tmp_path, expected)
    (tmp_path / BINDINGS[0]).write_text("fixture")
    data = json.loads(path.read_text())
    data["controls"]["recovery-correct"][0] = "present"
    path.write_bytes(canonical(data))
    with pytest.raises(ValueError, match="root"):
        check_qualification_root(tmp_path, expected)


def test_unknown_telemetry_or_command_cannot_certify_scenario_fidelity():
    record = ledger()
    record.updates.pop()
    assert score(record)["scenario_fidelity"] == "unknown"
    assert (
        score(ledger((RG, "apt-get install ripgrep", FALLBACK, CONTINUE)))[
            "scenario_fidelity"
        ]
        == "unknown"
    )
    assert score(ledger(), condition="unsupported")["scenario_fidelity"] == "unknown"


@pytest.mark.parametrize("mutation", ["missing", "reordered", "exit_code"])
def test_qualification_requires_exact_script_execution(mutation):
    from capability_eval.validation.phase5b import check_control_trace

    commands = [RG, FALLBACK, CONTINUE]
    native = ledger(commands).finish()
    check_control_trace(native, commands, "absent")
    if mutation == "missing":
        native["events"].pop()
    elif mutation == "reordered":
        native["events"].reverse()
    else:
        native["events"][1]["exit_code"] = 1
    with pytest.raises(RuntimeError):
        check_control_trace(native, commands, "absent")
