from inspect_ai.tool import ToolDef
from capability_eval.runtime.phase2 import EXCLUDED, PASSTHROUGH, restricted_tools


def test_auditor_cannot_simulate_or_rollback():
    names = {ToolDef(t).name for t in restricted_tools()}
    assert names == {"send_message", "resume", "end_conversation"}
    assert not names & EXCLUDED


def test_native_edit_tools_are_explicit():
    assert {"exec_command", "apply_patch"} <= PASSTHROUGH
    assert "auditor_execute" not in PASSTHROUGH


def test_eval_success_with_limited_sample_is_rejected(tmp_path):
    from types import SimpleNamespace
    import pytest
    from capability_eval.runtime.phase2 import require_completed

    sample = SimpleNamespace(error=None, limit="time")
    log = SimpleNamespace(status="success", samples=[sample])
    with pytest.raises(RuntimeError, match="execution limit"):
        require_completed([log], tmp_path)
    sample.limit = None
    with pytest.raises(RuntimeError, match="collection"):
        require_completed([log], tmp_path)


def test_reported_success_cannot_override_failed_filesystem_proof(tmp_path):
    from types import SimpleNamespace
    import pytest
    from capability_eval.runtime.phase2 import require_completed

    log = SimpleNamespace(
        status="success", samples=[SimpleNamespace(error=None, limit=None)]
    )
    (tmp_path / "result.json").write_text(
        '{"negative_control": false, "native_filesystem_success": false}'
    )
    with pytest.raises(RuntimeError, match="Filesystem evidence"):
        require_completed([log], tmp_path)


def test_negative_control_requires_original_challenge(tmp_path, monkeypatch):
    import asyncio
    import json
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import pytest
    from capability_eval.runtime import phase2

    nonce = "original-challenge"
    monkeypatch.setattr(phase2.secrets, "token_hex", lambda _: nonce)
    observed = {
        "fixture": phase2.BEFORE,
        "challenge": nonce,
        "receipt": None,
        "cwd": "/workspace",
    }
    sandbox = SimpleNamespace(exec=AsyncMock())
    monkeypatch.setattr(phase2, "sandbox", lambda: sandbox)
    collect = phase2.task(tmp_path, "unused-compose.yaml", negative=True).solver[-1]
    state = object()

    def run_collection():
        sandbox.exec.side_effect = [
            SimpleNamespace(success=True, stdout=json.dumps(observed)),
            SimpleNamespace(success=True, stdout=""),
        ]
        return asyncio.run(collect(state, None))

    # A genuinely unchanged control must continue to pass.
    assert run_collection() is state
    for changed_challenge in ("modified-challenge", ""):
        observed["challenge"] = changed_challenge
        with pytest.raises(RuntimeError, match="Simulation control"):
            run_collection()
