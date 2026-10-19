"""Offline review of this toy probe's known patch; no candidate code is run."""

import argparse
import dataclasses
import tempfile
import hashlib
import json
import re
import subprocess
from pathlib import Path

from inspect_ai.log import read_eval_log
from capability_eval.runtime.phase2 import BEFORE, require_completed


def review(run_dir: Path):
    log_paths = list((run_dir / "logs").glob("*.eval"))
    if len(log_paths) != 1:
        raise ValueError("Expected one Inspect log")
    log = read_eval_log(log_paths[0])
    require_completed([log], run_dir)
    result = json.loads((run_dir / "result.json").read_text())
    patch = (run_dir / "submission.patch").read_bytes()
    if hashlib.sha256(patch).hexdigest() != result["patch_sha256"]:
        raise ValueError("Patch hash mismatch")
    # This deliberately only supports the fixed toy fixture. Not a general
    # untrusted patch validator or Phase 3 verifier implementation.
    scratch = Path(tempfile.mkdtemp(prefix="reconstruction-", dir=run_dir))
    subprocess.run(["git", "init", "-q", str(scratch)], check=True)
    (scratch / "fixture.py").write_text(BEFORE)
    if patch:
        headers = re.findall(rb"^diff --git (.+)$", patch, re.M)
        if headers != [b"a/fixture.py b/fixture.py"]:
            raise ValueError("This review only supports the fixed toy fixture")
        subprocess.run(
            ["git", "-C", str(scratch), "apply", "--check", "-"],
            input=patch,
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(scratch), "apply", "-"], input=patch, check=True
        )
    matches = (scratch / "fixture.py").read_text() == result["observed"]["fixture"]
    if not matches:
        raise ValueError("Patch does not reconstruct independently collected bytes")
    sample = log.samples[0]
    messages = []
    for m in sample.messages:
        if m.role in {"assistant", "tool"}:
            item = {"role": m.role, "text": m.text}
            if getattr(m, "tool_calls", None):
                item["tool_calls"] = [dataclasses.asdict(c) for c in m.tool_calls]
            messages.append(item)
    report = {
        "eval_status": log.status,
        "sample_error": None,
        "sample_limit": None,
        "patch_reconstruction_matches": matches,
        "model": log.eval.model,
        "started_at": str(log.stats.started_at),
        "completed_at": str(log.stats.completed_at),
        "model_usage": {k: v.model_dump() for k, v in log.stats.model_usage.items()},
        "log_sha256": hashlib.sha256(log_paths[0].read_bytes()).hexdigest(),
        "messages": messages,
    }
    (run_dir / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("run_dir", type=Path)
    args = p.parse_args()
    report = review(args.run_dir)
    print(json.dumps({k: v for k, v in report.items() if k != "messages"}, indent=2))
