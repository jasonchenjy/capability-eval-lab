"""Trusted verifier lock, never made available to Bloom or the coding agent."""

from pathlib import Path
from typing import Literal

from capability_eval.creation.contracts import Artifact, identity, sha
from capability_eval.runtime.phase3 import verify
from capability_eval.verifier.handoff import BASE_SHA256
from capability_eval.verifier.sandbox import IMAGE

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "runtime/phase3.py",
    "grading/phase3.py",
    "verifier/handoff.py",
    "verifier/sandbox.py",
)


def source_hashes():
    return {p: sha((ROOT / p).read_bytes()) for p in SOURCES}


class VerifierLock(Artifact):
    version: Literal[1] = 1
    contract: Literal["phase2-fixture-value-v1"] = "phase2-fixture-value-v1"
    base_sha256: str
    image: str
    tests_sha256: str
    sources: dict[str, str]
    scoring: Literal["all-pass=1;fail=0;invalid=null"] = (
        "all-pass=1;fail=0;invalid=null"
    )


def make_lock(hidden_tests: bytes):
    from capability_eval.grading.phase3 import validate_tests
    from capability_eval.runtime.phase3 import strict_json

    validate_tests(strict_json(hidden_tests))
    return VerifierLock(
        base_sha256=BASE_SHA256,
        image=IMAGE,
        tests_sha256=sha(hidden_tests),
        sources=source_hashes(),
    )


def check_lock(lock, expected_sha256, hidden_tests):
    if identity(lock) != expected_sha256:
        raise ValueError("Verifier lock digest mismatch")
    if (
        lock.base_sha256 != BASE_SHA256
        or lock.image != IMAGE
        or lock.sources != source_hashes()
        or lock.tests_sha256 != sha(hidden_tests)
    ):
        raise ValueError("Frozen ground truth changed")


def verify_frozen(
    bundle, expected_bundle_sha256, lock, expected_lock_sha256, hidden_tests, patch
):
    # Both expected hashes must come from the trusted caller, not the bundle.
    if (
        identity(bundle) != expected_bundle_sha256
        or bundle.verifier_lock_sha256 != expected_lock_sha256
    ):
        raise ValueError("Seed or verifier identity changed")
    check_lock(lock, expected_lock_sha256, hidden_tests)
    result = verify(
        patch,
        base_sha256=lock.base_sha256,
        hidden_tests=hidden_tests,
        tests_sha256=lock.tests_sha256,
        image=lock.image,
    )
    check_lock(lock, expected_lock_sha256, hidden_tests)
    return result
