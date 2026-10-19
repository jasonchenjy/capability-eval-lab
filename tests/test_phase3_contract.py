import json
import sys

import pytest

from capability_eval.grading.phase3 import grade, validate_tests
from capability_eval.runtime import phase3
from capability_eval.validation.phase3_controls import patch_for
from capability_eval.verifier.handoff import BASE, BASE_SHA256, InvalidPatch, admit
from capability_eval.verifier.sandbox import bounded

# Public test data, deliberately unrelated to the private qualification suite.
TESTS = [
    {"id": "type", "field": "type", "expected": "str"},
    {"id": "value", "field": "value", "expected": "public-unit-test"},
]


@pytest.mark.parametrize(
    "source", ['VALUE = "changed"\n', 'VALUE = (\n    "changed"\n)\n']
)
def test_handoff_reconstructs_exact_bytes(source):
    assert admit(patch_for(source), BASE_SHA256) == source.encode()
    assert admit(b"", BASE_SHA256) == BASE


@pytest.mark.parametrize(
    "transform",
    [
        lambda p: p.replace(b"fixture.py", b"../escape.py"),
        lambda p: p.replace(b"fixture.py", b"/tmp/escape.py"),
        lambda p: p.replace(b"--- a/fixture.py", b"--- /dev/null"),
        lambda p: p.replace(b"@@ -1 +1 @@", b"@@ -2 +1 @@"),
        lambda p: p.replace(b'"before"', b'"other"'),
        lambda p: p + p,
        lambda p: p.replace(b"--- a/", b"new file mode 120000\n--- a/"),
        lambda p: p[:-1],
        lambda p: p + b"\x00",
        lambda p: b"x" * 65537,
    ],
)
def test_reject_unsafe_or_inconsistent_patch(transform):
    with pytest.raises(InvalidPatch):
        admit(transform(patch_for('VALUE = "changed"\n')), BASE_SHA256)


def test_wrong_base_is_rejected():
    with pytest.raises(InvalidPatch, match="base_mismatch"):
        admit(b"", "0" * 64)


def test_score_is_deterministic_and_all_or_nothing():
    assert grade(TESTS, {"type": "str", "value": "public-unit-test"}) == {
        "status": "pass",
        "score": 1,
        "passed": 2,
        "total": 2,
    }
    assert grade(TESTS, {"type": "str", "value": "wrong"}) == {
        "status": "fail",
        "score": 0,
        "passed": 1,
        "total": 2,
    }
    with pytest.raises(ValueError):
        grade(TESTS, {"score": 1, "status": "pass"})
    with pytest.raises(ValueError):
        validate_tests([])
    with pytest.raises(ValueError):
        validate_tests(TESTS + TESTS)


def test_duplicate_json_is_rejected():
    with pytest.raises(ValueError, match="duplicate_json_key"):
        phase3.strict_json(b'{"value":"wrong","value":"public-unit-test"}')


def test_bad_provenance_rejected_before_any_sandbox(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Untrusted handoff must be rejected before execution")

    monkeypatch.setattr(phase3, "Sandbox", forbidden)
    tests = json.dumps(TESTS).encode()
    result = phase3.verify(
        b"", base_sha256=BASE_SHA256, hidden_tests=tests, tests_sha256="0" * 64
    )
    assert result["status"] == "invalid" and result["score"] is None
    result = phase3.verify(
        b"bad\n",
        base_sha256=BASE_SHA256,
        hidden_tests=tests,
        tests_sha256=phase3.digest(tests),
    )
    assert result["status"] == "invalid" and result["score"] is None


def test_execution_bounds_output_and_time():
    result = bounded([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1)
    assert result.limit == "timeout"
    result = bounded([sys.executable, "-c", 'print("x"*100000)'], max_output=1024)
    assert result.limit == "output_limit"
    assert len(result.stdout) + len(result.stderr) <= 1024


@pytest.mark.parametrize(
    "graded",
    [
        b"",
        b'{"status":"pass","score":1}',
        b'{"status":"pass","score":1,"passed":0,"total":2}',
    ],
)
def test_missing_or_inconsistent_grader_output_is_invalid(monkeypatch, graded):
    from capability_eval.verifier.sandbox import Execution

    class FakeSandbox:
        boundaries = {}

        def __init__(self, role, image):
            self.role = role

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def put(self, name, data):
            # Hidden test inputs must never be sent to the candidate container.
            assert name == (
                "fixture.py" if self.role == "candidate" else "hidden-tests.json"
            )

        def python(self, script, **kwargs):
            out = (
                b'{"type":"str","value":"public-unit-test"}'
                if self.role == "candidate"
                else graded
            )
            return Execution(0, out, b"")

    monkeypatch.setattr(phase3, "Sandbox", FakeSandbox)
    tests = json.dumps(TESTS).encode()
    result = phase3.verify(
        b"",
        base_sha256=BASE_SHA256,
        hidden_tests=tests,
        tests_sha256=phase3.digest(tests),
    )
    assert result["status"] == "invalid" and result["score"] is None


@pytest.mark.parametrize(
    "source",
    [
        'VALUE = "public-unit-test"\n',
        'VALUE = "-".join(["public", "unit", "test"])\n',
        'VALUE = "public-" + "unit-test"\n',
    ],
)
def test_trusted_attestation_supports_equivalent_expressions(source):
    from capability_eval.grading.phase3 import attest_source

    observation = {"type": "str", "value": "public-unit-test"}
    assert attest_source(source, observation) == observation


@pytest.mark.parametrize(
    "source",
    [
        'VALUE = "wrong"\n',
        'import os\nprint("forged observation")\nos._exit(0)\n',
        'VALUE = __import__("os").system("exit 0")\n',
        'VALUE = "public-unit-test"\nVALUE = "wrong"\n',
        'VALUE = "x" * 1000000000\n',
    ],
)
def test_untrusted_source_cannot_forge_attested_value(source):
    from capability_eval.grading.phase3 import attest_source

    with pytest.raises(ValueError):
        attest_source(source, {"type": "str", "value": "public-unit-test"})
