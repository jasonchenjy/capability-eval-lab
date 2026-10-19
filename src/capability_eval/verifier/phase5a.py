"""Versioned, deliberately narrow black-box contract for the Boltons case.

The controller never imports candidate source. No plugin loading or repository
pytest strategy is implemented. Private assertions stay in this process.
"""

import argparse
import codecs
import hashlib
import io
import json
import tarfile
import tokenize
from pathlib import Path, PurePosixPath

from capability_eval.runtime.phase3 import strict_json
from capability_eval.verifier.sandbox import (
    IMAGE,
    InfrastructureError,
    Sandbox,
    bounded,
    docker,
)

VERSION = "black-box-json-v1"
PATCH_VERSION = "source-replacement-v1"
EDIT_PATH = "boltons/strutils.py"
MAX_SOURCE = 262144
MAX_ARCHIVE = 4 * 1024 * 1024
SOURCE_PATHS = (
    "verifier/phase5a.py",
    "verifier/sandbox.py",
    "runtime/phase3.py",
)

# No expected answers or suite metadata enter this candidate-side adapter.
ADAPTER = r"""
import json, sys
request = json.loads(sys.stdin.buffer.read())
sys.path.insert(0, '/workspace/repo')
try:
    from boltons.strutils import iter_splitlines, indent
    if request['op'] == 'splitlines':
        value = list(iter_splitlines(request['text']))
    else:
        value = indent(request['text'], request['margin'], request['newline'])
except BaseException:
    print(json.dumps({'version': 1, 'error': 'candidate_exception'}))
else:
    print(json.dumps({'version': 1, 'value': value}, ensure_ascii=True))
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode()


def source_hashes():
    root = Path(__file__).resolve().parents[1]
    return {p: digest((root / p).read_bytes()) for p in SOURCE_PATHS}


def read_snapshot(raw, manifest):
    """Read a pinned archive as inert bytes; never extract or run it on host."""
    if len(raw) > MAX_ARCHIVE or digest(raw) != manifest["archive_sha256"]:
        raise ValueError("snapshot_digest")
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        total = 0
        for member in archive:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or str(path) != member.name.rstrip("/")
            ):
                raise ValueError("snapshot_path")
            if member.isdir():
                continue
            if not member.isfile() or member.name in result or member.size > MAX_SOURCE:
                raise ValueError("snapshot_type_or_size")
            total += member.size
            if total > MAX_ARCHIVE:
                raise ValueError("snapshot_size")
            result[member.name] = archive.extractfile(member).read()
    if {p: digest(b) for p, b in result.items()} != manifest["files"]:
        raise ValueError("snapshot_files")
    return result


def tree_digest(files):
    return digest(canonical({p: digest(b) for p, b in files.items()}))


def validate_source(data):
    if len(data) > MAX_SOURCE or b"\x00" in data:
        raise ValueError("source_size_or_nul")
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        if codecs.lookup(encoding).name != "utf-8":
            raise ValueError("source_encoding")
        data.decode("utf-8")
    except (SyntaxError, LookupError, UnicodeError) as exc:
        raise ValueError("source_encoding") from exc


def admit(patch, base):
    """A replacement envelope, not general git apply. Only one regular source."""
    if len(patch) > MAX_SOURCE * 6:
        raise ValueError("patch_size")
    data = strict_json(patch)
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "base_tree", "files"}
        or data["version"] != PATCH_VERSION
        or data["base_tree"] != tree_digest(base)
        or not isinstance(data["files"], dict)
        or not set(data["files"]).issubset({EDIT_PATH})
    ):
        raise ValueError("patch_contract")
    result = dict(base)
    for path, text in data["files"].items():
        if not isinstance(text, str):
            raise ValueError("patch_content")
        content = text.encode("utf-8")
        validate_source(content)
        result[path] = content
    return result


def export_patch(base, collected):
    """Controller-collected regular bytes, with whole-tree scope validation."""
    if set(base) != set(collected) or any(
        not isinstance(b, bytes) for b in collected.values()
    ):
        raise ValueError("collected_tree")
    changed = {p: b for p, b in collected.items() if b != base[p]}
    if not set(changed).issubset({EDIT_PATH}):
        raise ValueError("edit_scope")
    for b in changed.values():
        validate_source(b)
    patch = canonical(
        {
            "version": PATCH_VERSION,
            "base_tree": tree_digest(base),
            "files": {p: b.decode("utf-8") for p, b in changed.items()},
        }
    )
    if admit(patch, base) != collected:
        raise ValueError("reconstruction_mismatch")
    return patch


def archive_files(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, content in sorted(files.items()):
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or str(path) != name:
                raise ValueError("archive_path")
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(content), 0o444
            archive.addfile(info, io.BytesIO(content))
    return stream.getvalue()


class CandidateBox(Sandbox):
    def install(self, files):
        script = """
import sys, tarfile, pathlib
root = pathlib.Path('/workspace/repo')
root.mkdir()
with tarfile.open(fileobj=sys.stdin.buffer, mode='r|') as archive:
    for member in archive:
        p = root / member.name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(archive.extractfile(member).read())
        p.chmod(0o644 if member.name == 'boltons/strutils.py' else 0o444)
"""
        docker(
            "exec",
            "-i",
            self.name,
            "python3",
            "-I",
            "-c",
            script,
            data=archive_files(files),
        )

    def collect(self):
        # No candidate imports. Reject nonregular nodes and excess output before
        # allowing the collected bytes to enter a new verification sandbox.
        script = """
import pathlib, os, stat, json, base64
root = pathlib.Path('/workspace/repo')
result = {}
for directory, dirs, names in os.walk(root, followlinks=False):
    for name in dirs + names:
        p = pathlib.Path(directory) / name
        mode = p.lstat().st_mode
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise RuntimeError('nonregular node')
        if stat.S_ISREG(mode):
            expected = 0o644 if str(p.relative_to(root)) == 'boltons/strutils.py' else 0o444
            if stat.S_IMODE(mode) != expected:
                raise RuntimeError('mode changed')
            if p.stat().st_size > 262144:
                raise RuntimeError('file too large')
            result[str(p.relative_to(root))] = base64.b64encode(p.read_bytes()).decode()
print(json.dumps(result))
"""
        execution = bounded(
            ["docker", "exec", self.name, "python3", "-I", "-B", "-c", script],
            timeout=10,
            max_output=MAX_ARCHIVE * 2,
        )
        if execution.returncode or execution.limit:
            raise ValueError("collection_failed")
        import base64

        data = strict_json(execution.stdout)
        return {p: base64.b64decode(b, validate=True) for p, b in data.items()}

    def request(self, request, timeout):
        return bounded(
            ["docker", "exec", "-i", self.name, "python3", "-I", "-B", "-c", ADAPTER],
            data=canonical(request),
            timeout=timeout,
            max_output=65536,
        )


def validate_suite(raw):
    if len(raw) > 65536:
        raise ValueError("suite_size")
    suite = strict_json(raw)
    if not isinstance(suite, list) or not 2 <= len(suite) <= 64:
        raise ValueError("suite_count")
    ids, operations = set(), set()
    for case in suite:
        if not isinstance(case, dict) or set(case) != {"id", "request", "expected"}:
            raise ValueError("suite_schema")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in ids:
            raise ValueError("suite_id")
        ids.add(case["id"])
        request = case["request"]
        if not isinstance(request, dict) or request.get("op") not in {
            "splitlines",
            "indent",
        }:
            raise ValueError("request_op")
        op = request["op"]
        fields = (
            {"op", "text"}
            if op == "splitlines"
            else {"op", "text", "margin", "newline"}
        )
        if set(request) != fields or not all(
            isinstance(v, str) and len(v) <= 4096 for v in request.values()
        ):
            raise ValueError("request_schema")
        expected = case["expected"]
        if op == "splitlines":
            if not isinstance(expected, list) or not all(
                isinstance(v, str) for v in expected
            ):
                raise ValueError("expected_type")
        elif not isinstance(expected, str):
            raise ValueError("expected_type")
        operations.add(op)
    if operations != {"splitlines", "indent"}:
        raise ValueError("missing_operations")
    return suite


def make_lock(snapshot, suite):
    cases = validate_suite(suite)
    return {
        "contract_version": 1,
        "strategy": VERSION,
        "threat_model": "separate-driver-visible-input-v1",
        "snapshot_sha256": digest(canonical(snapshot)),
        "suite_sha256": digest(suite),
        "mandatory_count": len(cases),
        "image": IMAGE,
        "timeout_seconds": 2,
        "sources": source_hashes(),
        "adapter_sha256": digest(ADAPTER.encode()),
    }


def check_lock(lock, expected, snapshot, suite):
    if digest(canonical(lock)) != expected or canonical(lock) != canonical(
        make_lock(snapshot, suite)
    ):
        raise ValueError("approval_or_verifier_changed")


def verify(patch, *, archive, snapshot, suite, lock, expected_lock):
    """Return only controller-owned results; candidate sees one request at a time."""
    result = {
        "contract_version": 1,
        "strategy": VERSION,
        "status": "invalid",
        "score": None,
        "reason": None,
        "patch_sha256": digest(patch),
        "lock_sha256": expected_lock,
        "completed": 0,
        "checks": [],
        "boundaries": None,
    }
    try:
        check_lock(lock, expected_lock, snapshot, suite)
        base = read_snapshot(archive, snapshot)
        candidate = admit(patch, base)
        result["candidate_tree_sha256"] = tree_digest(candidate)
        cases = validate_suite(suite)
        passed = 0
        with CandidateBox("phase5a", lock["image"]) as box:
            box.install(candidate)
            result["boundaries"] = box.boundaries
            for index, case in enumerate(cases):
                execution = box.request(case["request"], lock["timeout_seconds"])
                receipt = {
                    "index": index,
                    "returncode": execution.returncode,
                    "limit": execution.limit,
                    "stdout_sha256": digest(execution.stdout),
                    "stderr_sha256": digest(execution.stderr),
                }
                result["checks"].append(receipt)
                if execution.limit or execution.returncode:
                    result["reason"] = execution.limit or "candidate_process_exit"
                    break
                try:
                    response = strict_json(execution.stdout)
                except (ValueError, UnicodeError):
                    result["reason"] = "invalid_protocol"
                    break
                if (
                    not isinstance(response, dict)
                    or type(response.get("version")) is not int
                    or response["version"] != 1
                ):
                    result["reason"] = "invalid_protocol"
                    break
                if response == {"version": 1, "error": "candidate_exception"}:
                    ok = False
                elif set(response) == {"version", "value"}:
                    value = response["value"]
                    if (
                        case["request"]["op"] == "splitlines"
                        and (
                            not isinstance(value, list)
                            or not all(isinstance(v, str) for v in value)
                        )
                    ) or (
                        case["request"]["op"] == "indent" and not isinstance(value, str)
                    ):
                        result["reason"] = "invalid_protocol"
                        break
                    ok = value == case["expected"]
                else:
                    result["reason"] = "invalid_protocol"
                    break
                receipt["passed"] = ok
                passed += int(ok)
                result["completed"] += 1
        check_lock(lock, expected_lock, snapshot, suite)
        if result["reason"] is None:
            if result["completed"] != lock["mandatory_count"]:
                raise ValueError("incomplete_checks")
            result.update(
                status="pass" if passed == len(cases) else "fail",
                score=int(passed == len(cases)),
                passed=passed,
                reason="all_mandatory_checks_completed",
            )
    except InfrastructureError as exc:
        result["reason"] = "infrastructure:" + str(exc)
    except (ValueError, UnicodeError, tarfile.TarError) as exc:
        result["reason"] = "rejected:" + str(exc)
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ["patch", "archive", "snapshot", "suite", "lock", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-lock", required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output must be new")
    result = verify(
        args.patch.read_bytes(),
        archive=args.archive.read_bytes(),
        snapshot=strict_json(args.snapshot.read_bytes()),
        suite=args.suite.read_bytes(),
        lock=strict_json(args.lock.read_bytes()),
        expected_lock=args.expected_lock,
    )
    with args.output.open("xb") as stream:
        stream.write(canonical(result) + b"\n")
    raise SystemExit(2 if result["status"] == "invalid" else 0)


if __name__ == "__main__":
    main()
