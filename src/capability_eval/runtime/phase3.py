"""Phase 3: strict patch admission, disposable execution, separate trusted grading."""

import argparse
import hashlib
import json
from pathlib import Path

from capability_eval.grading.phase3 import grader_script, validate_tests
from capability_eval.verifier.handoff import InvalidPatch, admit
from capability_eval.verifier.sandbox import IMAGE, InfrastructureError, Sandbox

WORKER = """
import json, runpy
try:
    module = runpy.run_path('/workspace/fixture.py')
    value = module['VALUE']
    observation = {'type': type(value).__name__,
                   'value': value if isinstance(value, str) else repr(value)}
except BaseException:
    observation = {'candidate_error': True}
print(json.dumps(observation, sort_keys=True))
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    return json.loads(data, object_pairs_hook=unique)


def verify(patch, *, base_sha256, hidden_tests, tests_sha256, timeout=5, image=IMAGE):
    """Never consume a candidate-provided score; only grade observed behaviour.

    `hidden_tests` is trusted controller input and must not be sent to the agent.
    The deliberately narrow contract is the Phase 2 fixture's VALUE export.
    """
    result = {
        "status": "invalid",
        "score": None,
        "reason": None,
        "base_sha256": base_sha256,
        "patch_sha256": digest(patch),
        "tests_sha256": tests_sha256,
        "image": image,
        "contract": "phase2-fixture-value-v1",
        "boundaries": {},
        "worker_sha256": digest(WORKER.encode()),
    }
    try:
        if digest(hidden_tests) != tests_sha256:
            raise ValueError("hidden_tests_hash_mismatch")
        validate_tests(strict_json(hidden_tests))
        candidate = admit(patch, base_sha256)
        result["candidate_sha256"] = digest(candidate)
        with Sandbox("candidate", image) as candidate_box:
            candidate_box.put("fixture.py", candidate)
            result["boundaries"]["candidate"] = candidate_box.boundaries
            execution = candidate_box.python(WORKER, timeout=timeout)
        result["execution"] = {
            "returncode": execution.returncode,
            "limit": execution.limit,
            "stdout_sha256": digest(execution.stdout),
            "stderr_sha256": digest(execution.stderr),
            "stdout_bytes": len(execution.stdout),
            "stderr_bytes": len(execution.stderr),
        }
        if execution.limit:
            result["reason"] = execution.limit
            return result
        if execution.returncode:
            result["reason"] = "execution_failed_without_observation"
            return result
        try:
            observation = strict_json(execution.stdout)
        except (ValueError, UnicodeError):
            result["reason"] = "missing_or_malformed_observation"
            return result
        if observation == {"candidate_error": True}:
            result.update(status="fail", score=0, reason="candidate_exception")
            return result
        if (
            not isinstance(observation, dict)
            or set(observation) != {"type", "value"}
            or not all(isinstance(v, str) for v in observation.values())
        ):
            result["reason"] = "observation_schema_mismatch"
            return result
        result["observation"] = observation
        script = grader_script(observation, candidate.decode("utf-8"))
        result["grader_script_sha256"] = digest(script.encode())
        with Sandbox("grader", image) as grader_box:
            grader_box.put("hidden-tests.json", hidden_tests)
            result["boundaries"]["grader"] = grader_box.boundaries
            graded = grader_box.python(script, timeout=5)
        result["grader_execution"] = {
            "returncode": graded.returncode,
            "limit": graded.limit,
            "stdout_sha256": digest(graded.stdout),
            "stderr_sha256": digest(graded.stderr),
        }
        if graded.limit or graded.returncode:
            result["reason"] = "grader_infrastructure_failure"
            return result
        try:
            score = strict_json(graded.stdout)
        except (ValueError, UnicodeError):
            result["reason"] = "missing_grader_observation"
            return result
        if score == {"status": "invalid", "reason": "source_attestation_failed"}:
            result["reason"] = "source_attestation_failed"
            return result
        if (
            not isinstance(score, dict)
            or set(score) != {"status", "score", "passed", "total"}
            or not isinstance(score["status"], str)
            or score["status"] not in {"pass", "fail"}
            or type(score["score"]) is not int
            or score["score"] != int(score["status"] == "pass")
            or type(score["passed"]) is not int
            or type(score["total"]) is not int
            or not 0 <= score["passed"] <= score["total"]
            or score["total"] != len(strict_json(hidden_tests))
            or (score["passed"] == score["total"]) != (score["status"] == "pass")
        ):
            result["reason"] = "invalid_grader_observation"
            return result
        result.update(score)
        result["reason"] = "hidden_tests_completed"
        return result
    except InvalidPatch as exc:
        result["reason"] = "patch_rejected:" + str(exc)
    except InfrastructureError as exc:
        result["reason"] = str(exc)
    except (ValueError, UnicodeError):
        result["reason"] = "invalid_trusted_test_input"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--base-sha256", required=True)
    parser.add_argument("--hidden-tests", type=Path, required=True)
    parser.add_argument("--tests-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    result = verify(
        args.patch.read_bytes(),
        base_sha256=args.base_sha256,
        hidden_tests=args.hidden_tests.read_bytes(),
        tests_sha256=args.tests_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        output.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "score": result["score"],
                "reason": result["reason"],
            }
        )
    )
    return 2 if result["status"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
