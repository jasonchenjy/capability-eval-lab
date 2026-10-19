"""Explicit public qualification controls; hidden suite supplied separately."""

import argparse
import difflib
import json
from pathlib import Path

from capability_eval.runtime.phase3 import digest, verify
from capability_eval.validation.phase3_isolation import check_isolation
from capability_eval.verifier.handoff import BASE, BASE_SHA256
from capability_eval.verifier.sandbox import IMAGE, docker


def patch_for(source):
    return (
        "diff --git a/fixture.py b/fixture.py\n"
        + "".join(
            difflib.unified_diff(
                BASE.decode().splitlines(keepends=True),
                source.splitlines(keepends=True),
                fromfile="a/fixture.py",
                tofile="b/fixture.py",
            )
        )
    ).encode()


def run_controls(output, hidden_tests, live_patch):
    output.mkdir(parents=True, exist_ok=False)
    controls = {
        "phase2-live": (live_patch, "pass", 1, "hidden_tests_completed"),
        "correct": (
            patch_for('VALUE = "native-edit-confirmed"\n'),
            "pass",
            1,
            "hidden_tests_completed",
        ),
        "alternative": (
            patch_for('VALUE = "-".join(("native", "edit", "confirmed"))\n'),
            "pass",
            1,
            "hidden_tests_completed",
        ),
        "wrong": (patch_for('VALUE = "wrong"\n'), "fail", 0, "hidden_tests_completed"),
        "wrong-type": (patch_for("VALUE = 42\n"), "fail", 0, "hidden_tests_completed"),
        "no-op": (b"", "fail", 0, "hidden_tests_completed"),
        "syntax-error": (patch_for("VALUE = (\n"), "fail", 0, "candidate_exception"),
        "timeout": (patch_for("while True: pass\n"), "invalid", None, "timeout"),
        "missing-observation": (
            patch_for("import os\nos._exit(0)\n"),
            "invalid",
            None,
            "missing_or_malformed_observation",
        ),
        "forged-score": (
            patch_for(
                'import os\nprint(\'{"status":"pass","score":1}\', flush=True)\nos._exit(0)\n'
            ),
            "invalid",
            None,
            "observation_schema_mismatch",
        ),
        "output-limit": (
            patch_for('import os\nwhile True: os.write(1,b"x"*8192)\n'),
            "invalid",
            None,
            "output_limit",
        ),
        "forged-observation": (
            patch_for(
                'import os\nprint(\'{"type":"str","value":"native-edit-confirmed"}\', flush=True)\nos._exit(0)\n'
            ),
            "invalid",
            None,
            "source_attestation_failed",
        ),
        "encoding-bypass": (
            patch_for(
                '# coding: unicode_escape\nVALUE = "native-edit-confirmed"\n# '
                + r'\u000aVALUE = "wrong"\u000aimport os,json\u000aprint(json.dumps({"type":"str","value":"native-edit-confirmed"}),flush=True)\u000aos._exit(0)'
                + "\n"
            ),
            "invalid",
            None,
            "patch_rejected:source_encoding_not_utf8",
        ),
        "deep-json": (
            patch_for(
                'import os\nprint("["*20000+"0"+"]"*20000,flush=True)\nos._exit(0)\n'
            ),
            "invalid",
            None,
            "missing_or_malformed_observation",
        ),
        "utf8-declared": (
            patch_for('# coding: utf-8\n# café\nVALUE = "native-edit-confirmed"\n'),
            "pass",
            1,
            "hidden_tests_completed",
        ),
        "malformed": (
            b"not a patch\n",
            "invalid",
            None,
            "patch_rejected:path_not_allowed",
        ),
        "path-traversal": (
            patch_for('VALUE = "wrong"\n').replace(b"fixture.py", b"../escape.py"),
            "invalid",
            None,
            "patch_rejected:path_not_allowed",
        ),
    }
    summary = []
    for name, (patch, status, score, reason) in controls.items():
        result = verify(
            patch,
            base_sha256=BASE_SHA256,
            hidden_tests=hidden_tests,
            tests_sha256=digest(hidden_tests),
            timeout=2,
        )
        (output / f"{name}.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n"
        )
        passed = (result["status"], result["score"], result["reason"]) == (
            status,
            score,
            reason,
        )
        summary.append(
            {
                "control": name,
                "accepted": passed,
                "status": result["status"],
                "score": result["score"],
                "reason": result["reason"],
            }
        )
        print(json.dumps(summary[-1]), flush=True)
    # No image pull: nonexistent content-addressed image must be invalid, never 0/1.
    result = verify(
        b"",
        base_sha256=BASE_SHA256,
        hidden_tests=hidden_tests,
        tests_sha256=digest(hidden_tests),
        image="sha256:" + "0" * 64,
    )
    (output / "infrastructure.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    summary.append(
        {
            "control": "infrastructure",
            "accepted": result["status"] == "invalid" and result["score"] is None,
            "status": result["status"],
            "score": result["score"],
            "reason": result["reason"],
        }
    )
    isolation = check_isolation(hidden_tests)
    (output / "isolation.json").write_text(
        json.dumps(isolation, indent=2, sort_keys=True) + "\n"
    )
    summary.append(
        {
            "control": "isolation",
            "accepted": True,
            "status": "pass",
            "score": None,
            "reason": "isolation_verified",
        }
    )
    remaining = (
        docker("ps", "-aq", "--filter", "name=capability-phase3-").decode().strip()
    )
    if remaining:
        raise RuntimeError("Probe containers remain")
    report = {
        "controls": summary,
        "all_accepted": all(x["accepted"] for x in summary),
        "containers_remaining": False,
        "image": IMAGE,
        "tests_sha256": digest(hidden_tests),
        "base_sha256": BASE_SHA256,
        "phase2_patch_sha256": digest(live_patch),
    }
    (output / "summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    if not report["all_accepted"]:
        raise RuntimeError("Qualification controls failed")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--hidden-tests", type=Path, required=True)
    p.add_argument("--phase2-patch", type=Path, required=True)
    a = p.parse_args()
    run_controls(a.output, a.hidden_tests.read_bytes(), a.phase2_patch.read_bytes())
