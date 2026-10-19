"""Frozen-seed smoke qualification through real Dish/Codex tools and Phase 3."""

import argparse
import json
import shlex
from pathlib import Path

from inspect_ai import Task, eval
from inspect_ai.model import ChatMessageAssistant, ModelOutput, get_model
from inspect_ai.solver import solver
from inspect_ai.tool import ToolCall
from inspect_ai.util import sandbox

from capability_eval.audit.frozen_seed import native_audit_solver, seed_sample
from capability_eval.creation.contracts import canonical, identity, load_frozen, sha
from capability_eval.creation.ground_truth import (
    check_lock,
    verify_frozen,
    VerifierLock,
)
from capability_eval.creation.phase4 import read
from capability_eval.verifier.handoff import BASE
from capability_eval.validation.phase3_controls import patch_for


def qualify(
    bundle_data, expected_bundle, lock, expected_lock, hidden_tests, compose, output
):
    bundle = load_frozen(bundle_data, expected_bundle)
    check_lock(lock, expected_lock, hidden_tests)
    if bundle.verifier_lock_sha256 != expected_lock:
        raise ValueError("Wrong verifier binding")
    output.mkdir(parents=True, exist_ok=False)
    observed = {}

    @solver
    def prepare():
        async def run(state, generate):
            s = sandbox()
            await s.write_file("/workspace/fixture.py", BASE.decode())
            r = await s.exec(
                [
                    "bash",
                    "-lc",
                    "git init -q && git config user.email probe@example.invalid && git config user.name Probe && git add fixture.py && git commit -qm baseline",
                ],
                cwd="/workspace",
                timeout=30,
            )
            if not r.success:
                raise RuntimeError("Baseline initialization failed")
            return state

        return run

    @solver
    def collect():
        async def run(state, generate):
            s = sandbox()
            observed["fixture"] = await s.read_file("/workspace/fixture.py")
            diff = await s.exec(
                ["git", "diff", "--", "fixture.py"], cwd="/workspace", timeout=30
            )
            if not diff.success:
                raise RuntimeError("Patch export failed")
            observed["patch"] = diff.stdout
            (output / "submission.patch").write_text(diff.stdout)
            return state

        return run

    calls = 0

    def response(messages, tools, tool_choice, config):
        nonlocal calls
        calls += 1
        if calls == 1:
            if "exec_command" not in {t.name for t in tools}:
                raise RuntimeError("Native exec_command absent")
            script = 'from pathlib import Path; p=Path("fixture.py"); print(p.read_text()); p.write_text(\'VALUE = "native-edit-confirmed"\\n\'); print(p.read_text())'
            return ModelOutput.from_message(
                ChatMessageAssistant(
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="phase4_native_edit",
                            function="exec_command",
                            arguments={
                                "cmd": "python3 -c " + shlex.quote(script),
                                "workdir": "/workspace",
                            },
                        )
                    ],
                )
            )
        if calls > 4:
            raise RuntimeError("Target call budget exceeded")
        return ModelOutput.from_content(
            "mockllm/phase4-target", "Native file edit completed."
        )

    model = get_model("mockllm/phase4-target", custom_outputs=response)
    task = Task(
        dataset=[seed_sample(bundle_data, expected_bundle)],
        solver=[
            prepare(),
            native_audit_solver(bundle_data, expected_bundle),
            collect(),
        ],
        sandbox=("docker", compose),
        time_limit=180,
    )
    logs = eval(
        task,
        model=model,
        model_roles={"target": model, "auditor": model},
        log_dir=str(output / "logs"),
        display="plain",
        ctl_server=False,
        max_samples=1,
        retry_on_error=0,
    )
    if len(logs) != 1 or logs[0].status != "success" or len(logs[0].samples or []) != 1:
        raise RuntimeError("Native audit failed")
    sample = logs[0].samples[0]
    if sample.error or sample.limit or not observed.get("patch"):
        raise RuntimeError("Native audit incomplete")
    if observed["fixture"] != 'VALUE = "native-edit-confirmed"\n':
        raise RuntimeError("Independent file observation mismatch")
    results = {}
    for name, patch in [
        ("native", observed["patch"].encode()),
        ("no-op", b""),
        ("wrong", patch_for('VALUE = "wrong"\n')),
    ]:
        results[name] = verify_frozen(
            bundle, expected_bundle, lock, expected_lock, hidden_tests, patch
        )
    if [
        (results[n]["status"], results[n]["score"])
        for n in ["native", "no-op", "wrong"]
    ] != [("pass", 1), ("fail", 0), ("fail", 0)]:
        raise RuntimeError("Frozen scorer qualification failed")
    messages = [
        {"role": m.role, "text": m.text}
        for m in sample.messages
        if m.role in {"tool", "assistant"}
    ]
    report = {
        "frozen_seed_sha256": identity(bundle),
        "verifier_lock_sha256": identity(lock),
        "fixture_sha256": sha(observed["fixture"].encode()),
        "patch_sha256": sha(observed["patch"].encode()),
        "target_mode": "deterministic inference; real Codex ACP/Dish execution",
        "target_calls": calls,
        "eval_status": logs[0].status,
        "log_sha256": sha(next((output / "logs").glob("*.eval")).read_bytes()),
        "ground_truth_unchanged": True,
        "verifier_results": results,
        "messages": messages,
    }
    check_lock(lock, expected_lock, hidden_tests)
    (output / "result.json").write_bytes(canonical(report) + b"\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--roots", type=Path, required=True)
    p.add_argument("--verifier-lock", type=Path, required=True)
    p.add_argument("--hidden-tests", type=Path, required=True)
    p.add_argument("--compose", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    roots = json.loads(a.roots.read_text())
    qualify(
        a.bundle.read_bytes(),
        roots["frozen_seed_sha256"],
        read(a.verifier_lock, VerifierLock),
        roots["verifier_lock_sha256"],
        a.hidden_tests.read_bytes(),
        a.compose,
        a.output,
    )
