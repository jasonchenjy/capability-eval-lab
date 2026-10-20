"""Offline real-container qualification. No models or runtime auditor involved."""

import argparse
import json
import os
from pathlib import Path

from capability_eval.verifier import phase5a as v

EXPECTED = {
    "baseline": ("fail", 0),
    "noop": ("fail", 0),
    "correct": ("pass", 1),
    "alternative": ("pass", 1),
    "wrong": ("fail", 0),
    "invalid-regex": ("fail", 0),
    "overfit": ("fail", 0),
    "exception": ("invalid", None),
    **{
        name: ("invalid", None)
        for name in [
            "forged-score",
            "missing-result",
            "malformed-output",
            "timeout",
            "excess-output",
            "deep-json",
            "abrupt-exit",
            "path-traversal",
            "malformed-patch",
            "encoding",
            "adapter-bypass",
            "literal-injection",
        ]
    },
}


def check_scenario(
    scenario, expected_scenario, snapshot, expected_lock, instruction, controls
):
    if v.digest(v.canonical(scenario)) != expected_scenario:
        raise ValueError("scenario_approval_mismatch")
    if (
        scenario.get("schema_version") != 2
        or scenario.get("snapshot_manifest_sha256") != v.digest(v.canonical(snapshot))
        or scenario.get("repository") != snapshot.get("repository")
        or scenario.get("revision") != snapshot.get("revision")
        or scenario.get("verifier_lock_sha256") != expected_lock
        or scenario.get("verifier_strategy") != v.VERSION
        or scenario.get("edit_policy") != v.EDIT_POLICY
        or scenario.get("public_instruction_sha256") != v.digest(instruction)
    ):
        raise ValueError("scenario_binding_mismatch")
    expected_names = {name + ".patch" for name in EXPECTED}
    if (
        set(controls) != set(EXPECTED)
        or not isinstance(scenario.get("controls"), dict)
        or set(scenario["controls"]) != expected_names
    ):
        raise ValueError("control_inventory_mismatch")
    for name, data in controls.items():
        if v.digest(data) != scenario["controls"][name + ".patch"]:
            raise ValueError("control_digest_mismatch:" + name)
    if controls["correct"] == controls["alternative"]:
        raise ValueError("positive_controls_must_differ")


def load_controls(private):
    # Load once: the bytes checked here are exactly the bytes executed below.
    paths = list(private.glob("*.patch.json"))
    if {p.name for p in paths} != {n + ".patch.json" for n in EXPECTED}:
        raise ValueError("control_inventory_mismatch")
    return {n: (private / (n + ".patch.json")).read_bytes() for n in EXPECTED}


def qualify(
    archive,
    snapshot,
    private,
    output,
    lock,
    expected_lock,
    *,
    scenario,
    expected_scenario,
    instruction,
):
    controls = load_controls(private)
    check_scenario(
        scenario, expected_scenario, snapshot, expected_lock, instruction, controls
    )
    suite = (private / "suite.json").read_bytes()
    v.check_lock(lock, expected_lock, snapshot, suite)
    base = v.read_snapshot(archive, snapshot)
    if v.admit(controls["correct"], base) == v.admit(controls["alternative"], base):
        raise ValueError("positive_control_trees_must_differ")
    output.mkdir(parents=True, exist_ok=False)
    args = dict(
        archive=archive,
        snapshot=snapshot,
        suite=suite,
        lock=lock,
        expected_lock=expected_lock,
    )
    records = {}
    for name, expected in EXPECTED.items():
        result = v.verify(controls[name], **args)
        (output / (name + ".json")).write_bytes(v.canonical(result) + b"\n")
        if (result["status"], result["score"]) != expected:
            raise RuntimeError(f"Control failed: {name}: {result['reason']}")
        if expected[0] in {"pass", "fail"}:
            if (
                result["completed"] != lock["mandatory_count"]
                or result["reason"] != "all_mandatory_checks_completed"
            ):
                raise RuntimeError("Incomplete functional control:" + name)
        elif name == "timeout":
            if result["reason"] != "timeout" or result["boundaries"] is None:
                raise RuntimeError("Timeout control did not execute")
        elif (
            not result["reason"].startswith("rejected:")
            or result["boundaries"] is not None
        ):
            raise RuntimeError(
                "Unsafe control was not rejected before execution:" + name
            )
        records[name] = {
            "status": result["status"],
            "score": result["score"],
            "reason": result["reason"],
            "completed": result["completed"],
        }
        print(name, result["status"], result["score"], flush=True)

    base = v.read_snapshot(archive, snapshot)
    reference_patch = controls["correct"]
    reference = v.admit(reference_patch, base)
    # Real filesystem materialization/collection, then independent reconstruction.
    with v.CandidateBox("handoff", v.IMAGE) as box:
        box.install(reference)
        collected = box.collect()
        exported = v.export_patch(base, collected)
        if v.admit(exported, base) != collected or collected != reference:
            raise RuntimeError("Independent reconstruction failed")
        handoff = {
            "reconstructed_tree": v.tree_digest(collected),
            "patch_sha256": v.digest(exported),
            "file_count": len(collected),
            "matches_reference": True,
            "boundaries": box.boundaries,
        }
        # Fail collection on actual file-mode and symlink changes.
        v.docker(
            "exec", box.name, "chmod", "755", "/workspace/repo/boltons/strutils.py"
        )
        try:
            box.collect()
        except ValueError:
            handoff["mode_rejected"] = True
        else:
            raise RuntimeError("mode accepted")
        v.docker(
            "exec", box.name, "chmod", "644", "/workspace/repo/boltons/strutils.py"
        )
        v.docker("exec", box.name, "ln", "-s", "/etc/passwd", "/workspace/repo/link")
        try:
            box.collect()
        except ValueError:
            handoff["symlink_rejected"] = True
        else:
            raise RuntimeError("symlink accepted")
    (output / "handoff.json").write_bytes(v.canonical(handoff) + b"\n")
    repeated = v.verify(exported, **args)
    first = json.loads((output / "correct.json").read_bytes())
    # Container names are intentionally new. Check every deterministic observation.
    keys = ["status", "score", "completed", "passed", "checks", "candidate_tree_sha256"]
    if any(repeated[k] != first[k] for k in keys):
        raise RuntimeError("Replay differs")
    (output / "repeat.json").write_bytes(v.canonical(repeated) + b"\n")
    records["repeat"] = {
        "status": repeated["status"],
        "score": repeated["score"],
        "deterministic_observations_match": True,
    }

    # A real missing Docker endpoint exercises transport failure, not a mock.
    previous = os.environ.get("DOCKER_HOST")
    try:
        os.environ["DOCKER_HOST"] = "unix:///tmp/capability-eval-nonexistent-5a.sock"
        result = v.verify(reference_patch, **args)
    finally:
        if previous is None:
            os.environ.pop("DOCKER_HOST", None)
        else:
            os.environ["DOCKER_HOST"] = previous
    if (
        result["status"] != "invalid"
        or result["score"] is not None
        or not result["reason"].startswith("infrastructure:")
    ):
        raise RuntimeError("Infrastructure failure not classified")
    (output / "infrastructure.json").write_bytes(v.canonical(result) + b"\n")
    records["infrastructure"] = {
        "status": result["status"],
        "score": result["score"],
        "reason": result["reason"],
    }

    # Controlled fixed code probes OS boundaries; it imports no repository code.
    with v.CandidateBox("isolation", v.IMAGE) as box:
        box.install(base)
        script = """
import os, pathlib, json, socket
paths = ['/workspace/hidden-tests.json', '/workspace/suite.json', '/var/run/docker.sock', '/root/.codex/auth.json', HOST_PRIVATE_PATH]
readable = []
for p in paths:
    try:
        with open(p, 'rb') as f: f.read(1)
        readable.append(p)
    except OSError: pass
s = socket.socket(); s.settimeout(1)
try:
    s.connect(('1.1.1.1', 443)); egress = True
except OSError: egress = False
finally: s.close()
print(json.dumps({'uid': os.getuid(), 'private_readable_count': len(readable), 'egress': egress,
                 'credential_env': any(k in os.environ for k in ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GH_TOKEN'])}))
""".replace("HOST_PRIVATE_PATH", repr(str((private / "suite.json").resolve())))
        probe = box.python(script, timeout=3)
        observed = v.strict_json(probe.stdout)
        if (
            probe.returncode
            or probe.limit
            or observed
            != {
                "uid": 65534,
                "private_readable_count": 0,
                "egress": False,
                "credential_env": False,
            }
        ):
            raise RuntimeError("Isolation probe failed")
        isolation = {
            "observed": observed,
            "boundaries": box.boundaries,
            "private_tests_entered_candidate": False,
        }
    (output / "isolation.json").write_bytes(v.canonical(isolation) + b"\n")
    v.check_lock(lock, expected_lock, snapshot, suite)
    remaining = v.docker(
        "ps",
        "-a",
        "--filter",
        "name=capability-phase3-phase5a-",
        "--format",
        "{{.Names}}",
    )
    if remaining.strip():
        raise RuntimeError("Candidate containers remain")
    check_scenario(
        scenario,
        expected_scenario,
        snapshot,
        expected_lock,
        instruction,
        load_controls(private),
    )
    if (private / "suite.json").read_bytes() != suite:
        raise ValueError("private_suite_changed_during_qualification")
    summary = {
        "scenario_sha256": expected_scenario,
        "approved_controls_verified": True,
        "contract": v.VERSION,
        "lock_sha256": expected_lock,
        "controls": records,
        "mandatory_checks": lock["mandatory_count"],
        "no_live_models": True,
        "phase5b_started": False,
        "cleanup_verified": True,
        "snapshot_tree_sha256": v.tree_digest(base),
    }
    (output / "summary.json").write_bytes(v.canonical(summary) + b"\n")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for field in [
        "archive",
        "snapshot",
        "private",
        "output",
        "lock",
        "scenario",
        "instruction",
    ]:
        p.add_argument("--" + field, type=Path, required=True)
    p.add_argument("--expected-lock", required=True)
    p.add_argument("--expected-scenario", required=True)
    a = p.parse_args()
    qualify(
        a.archive.read_bytes(),
        v.strict_json(a.snapshot.read_bytes()),
        a.private,
        a.output,
        v.strict_json(a.lock.read_bytes()),
        a.expected_lock,
        scenario=v.strict_json(a.scenario.read_bytes()),
        expected_scenario=a.expected_scenario,
        instruction=a.instruction.read_bytes(),
    )
