"""Trusted grader program: runs only in the separate hidden-test sandbox."""

import json


def validate_tests(data):
    if not isinstance(data, list) or not data:
        raise ValueError("empty_or_invalid_tests")
    ids = set()
    for test in data:
        if (
            not isinstance(test, dict)
            or set(test) != {"id", "field", "expected"}
            or not isinstance(test["id"], str)
            or test["id"] in ids
            or not isinstance(test["field"], str)
            or test["field"] not in {"type", "value"}
            or not isinstance(test["expected"], str)
        ):
            raise ValueError("invalid_test_contract")
        ids.add(test["id"])
    if {test["field"] for test in data} != {"type", "value"}:
        raise ValueError("missing_contract_field")
    return data


def grade(tests, observation):
    validate_tests(tests)
    if (
        not isinstance(observation, dict)
        or set(observation) != {"type", "value"}
        or not all(isinstance(v, str) for v in observation.values())
    ):
        raise ValueError("invalid_observation")
    passed = sum(observation[t["field"]] == t["expected"] for t in tests)
    return {
        "status": "pass" if passed == len(tests) else "fail",
        "score": int(passed == len(tests)),
        "passed": passed,
        "total": len(tests),
    }


def attest_source(source, observation):
    """Interpret a tiny expression grammar, never eval/exec candidate code.

    Supported modules have exactly VALUE = <constant/string-add/string-join>.
    This is a toy-fixture contract, not a general Python verifier.
    """
    import ast

    tree = ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Assign):
        raise ValueError("unsupported_candidate_contract")
    assignment = tree.body[0]
    if (
        len(assignment.targets) != 1
        or not isinstance(assignment.targets[0], ast.Name)
        or assignment.targets[0].id != "VALUE"
    ):
        raise ValueError("unsupported_candidate_contract")

    def interpret(node, depth=0):
        if depth > 20:
            raise ValueError("expression_too_deep")
        if isinstance(node, ast.Constant) and type(node.value) in (
            str,
            int,
            bool,
            type(None),
        ):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = (
                interpret(node.left, depth + 1),
                interpret(node.right, depth + 1),
            )
            if isinstance(left, str) and isinstance(right, str):
                value = left + right
                if len(value) <= 65536:
                    return value
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "join"
            and len(node.args) == 1
            and not node.keywords
            and isinstance(node.args[0], (ast.Tuple, ast.List))
        ):
            separator = interpret(node.func.value, depth + 1)
            parts = [interpret(part, depth + 1) for part in node.args[0].elts]
            if isinstance(separator, str) and all(isinstance(p, str) for p in parts):
                size = sum(map(len, parts)) + max(0, len(parts) - 1) * len(separator)
                if size <= 65536:
                    return separator.join(parts)
        raise ValueError("unsupported_candidate_contract")

    value = interpret(assignment.value)
    trusted = {
        "type": type(value).__name__,
        "value": value if isinstance(value, str) else repr(value),
    }
    if observation != trusted:
        raise ValueError("source_observation_mismatch")
    return trusted


# Source arrives as inert JSON text; the grader never imports or executes it.
SCRIPT = """
import json
from pathlib import Path
{definitions}
if Path('/workspace/fixture.py').exists():
    raise RuntimeError('Candidate source in grader')
tests = json.loads(Path('/workspace/hidden-tests.json').read_text())
observation = json.loads({observation!r})
source = json.loads({source!r})
try:
    trusted = attest_source(source, observation)
except (ValueError, SyntaxError, RecursionError):
    print(json.dumps({{"status": "invalid", "reason": "source_attestation_failed"}}))
else:
    print(json.dumps(grade(tests, trusted), sort_keys=True))
"""


def grader_script(observation, source):
    import inspect

    return SCRIPT.format(
        definitions="\n".join(
            inspect.getsource(f) for f in (validate_tests, grade, attest_source)
        ),
        observation=json.dumps(observation),
        source=json.dumps(source),
    )
