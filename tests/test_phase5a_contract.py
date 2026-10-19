import io
import tarfile
from types import SimpleNamespace

import pytest

from capability_eval.verifier import phase5a as v


def base():
    return {v.EDIT_PATH: b"x = 1\n", "LICENSE": b"public license\n"}


def inputs():
    files = base()
    raw = v.archive_files(files)
    snapshot = {
        "archive_sha256": v.digest(raw),
        "files": {p: v.digest(b) for p, b in files.items()},
    }
    suite = v.canonical(
        [
            {
                "id": "a",
                "request": {"op": "splitlines", "text": "public"},
                "expected": ["public"],
            },
            {
                "id": "b",
                "request": {
                    "op": "indent",
                    "text": "public",
                    "margin": ">",
                    "newline": "\n",
                },
                "expected": ">public",
            },
        ]
    )
    lock = v.make_lock(snapshot, suite)
    return dict(
        archive=raw,
        snapshot=snapshot,
        suite=suite,
        lock=lock,
        expected_lock=v.digest(v.canonical(lock)),
    )


def test_snapshot_and_replacement_roundtrip():
    args = inputs()
    assert v.read_snapshot(args["archive"], args["snapshot"]) == base()
    changed = {**base(), v.EDIT_PATH: b"# nonascii: \xc3\xa9\nx = 2\n"}
    patch = v.export_patch(base(), changed)
    assert v.admit(patch, base()) == changed
    assert v.admit(v.export_patch(base(), base()), base()) == base()
    with pytest.raises(ValueError):
        v.read_snapshot(args["archive"] + b"bad", args["snapshot"])


@pytest.mark.parametrize(
    "path",
    ["../escape", "/escape", "tests/test_x.py", "LICENSE", "boltons/../strutils.py"],
)
def test_patch_paths_rejected(path):
    patch = v.canonical(
        {
            "version": v.PATCH_VERSION,
            "base_tree": v.tree_digest(base()),
            "files": {path: "x"},
        }
    )
    with pytest.raises(ValueError):
        v.admit(patch, base())


@pytest.mark.parametrize(
    "content",
    ["\ufeffx=1", "# coding: latin-1\nx=1", "x\x00", "x" * (v.MAX_SOURCE + 1)],
)
def test_source_encoding_and_size(content):
    patch = v.canonical(
        {
            "version": v.PATCH_VERSION,
            "base_tree": v.tree_digest(base()),
            "files": {v.EDIT_PATH: content},
        }
    )
    with pytest.raises(ValueError):
        v.admit(patch, base())


@pytest.mark.parametrize(
    "change",
    [
        {"version": "unknown"},
        {"base_tree": "bad"},
        {"mode": "100755"},
        {"files": {v.EDIT_PATH: {"symlink": "x"}}},
    ],
)
def test_patch_metadata(change):
    patch = {
        "version": v.PATCH_VERSION,
        "base_tree": v.tree_digest(base()),
        "files": {},
    }
    patch.update(change)
    with pytest.raises(ValueError):
        v.admit(v.canonical(patch), base())


def test_collection_cannot_hide_out_of_scope_edits():
    for files in [
        {**base(), "new": b"x"},
        {v.EDIT_PATH: b"x"},
        {**base(), "LICENSE": b"changed"},
    ]:
        with pytest.raises(ValueError):
            v.export_patch(base(), files)


@pytest.mark.parametrize("kind", ["symlink", "traversal", "duplicate"])
def test_even_hashed_bad_archive_is_rejected(kind):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as archive:
        name = "../bad" if kind == "traversal" else "file"
        item = tarfile.TarInfo(name)
        item.size = 1
        if kind == "symlink":
            item.type, item.linkname = tarfile.SYMTYPE, "/etc/passwd"
        archive.addfile(item, io.BytesIO(b"x"))
        if kind == "duplicate":
            archive.addfile(item, io.BytesIO(b"x"))
    raw = buf.getvalue()
    with pytest.raises(ValueError):
        v.read_snapshot(raw, {"archive_sha256": v.digest(raw), "files": {}})


def test_lock_pins_strategy_suite_snapshot_and_code(monkeypatch):
    args = inputs()
    v.check_lock(args["lock"], args["expected_lock"], args["snapshot"], args["suite"])
    for field, value in [
        ("strategy", "repository-test-v1"),
        ("contract_version", 2),
        ("contract_version", True),
        ("mandatory_count", 1),
        ("image", "latest"),
    ]:
        lock = {**args["lock"], field: value}
        with pytest.raises(ValueError):
            v.check_lock(
                lock, v.digest(v.canonical(lock)), args["snapshot"], args["suite"]
            )
    with pytest.raises(ValueError):
        v.check_lock(
            args["lock"], args["expected_lock"], args["snapshot"], args["suite"] + b" "
        )
    monkeypatch.setattr(v, "source_hashes", lambda: {})
    with pytest.raises(ValueError):
        v.check_lock(
            args["lock"], args["expected_lock"], args["snapshot"], args["suite"]
        )


def fake_box(monkeypatch, outputs):
    requests = []

    class Box:
        boundaries = {"synthetic": True}

        def __init__(self, *args):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def install(self, files):
            assert files == base()

        def request(self, request, timeout):
            requests.append(request)
            out = outputs[len(requests) - 1]
            return SimpleNamespace(returncode=0, limit=None, stdout=out, stderr=b"")

    monkeypatch.setattr(v, "CandidateBox", Box)
    return requests


def test_only_requests_cross_boundary_and_all_checks_required(monkeypatch):
    requests = fake_box(
        monkeypatch,
        [
            v.canonical({"version": 1, "value": ["public"]}),
            v.canonical({"version": 1, "value": ">public"}),
        ],
    )
    result = v.verify(v.export_patch(base(), base()), **inputs())
    assert (result["status"], result["score"], result["completed"]) == ("pass", 1, 2)
    assert len(requests) == 2 and all(
        "expected" not in x and "id" not in x for x in requests
    )


@pytest.mark.parametrize(
    "response",
    [
        b'{"score":1}',
        b"",
        b"not json",
        b'{"version":true,"value":[]}',
        b'{"version":1,"value":1}',
        b"[" * 1000,
    ],
)
def test_untrusted_protocol_cannot_become_a_score(monkeypatch, response):
    fake_box(monkeypatch, [response])
    result = v.verify(v.export_patch(base(), base()), **inputs())
    assert result["status"] == "invalid" and result["score"] is None


def test_functional_failure_still_runs_all_checks(monkeypatch):
    fake_box(
        monkeypatch,
        [
            v.canonical({"version": 1, "error": "candidate_exception"}),
            v.canonical({"version": 1, "value": ">public"}),
        ],
    )
    result = v.verify(v.export_patch(base(), base()), **inputs())
    assert (result["status"], result["score"], result["completed"]) == ("fail", 0, 2)


def test_changed_ground_truth_after_execution_cannot_pass(monkeypatch):
    args = inputs()
    fake_box(
        monkeypatch,
        [
            v.canonical({"version": 1, "value": ["public"]}),
            v.canonical({"version": 1, "value": ">public"}),
        ],
    )
    original = v.check_lock
    calls = []

    def check(*a):
        calls.append(1)
        if len(calls) == 2:
            raise ValueError("changed_after_run")
        return original(*a)

    monkeypatch.setattr(v, "check_lock", check)
    result = v.verify(v.export_patch(base(), base()), **args)
    assert result["status"] == "invalid" and result["score"] is None


@pytest.mark.parametrize("raw", [b"[]", b"{}", b"null", b"[" * 1000])
def test_missing_or_malformed_private_suite_is_rejected(raw):
    with pytest.raises(ValueError):
        v.validate_suite(raw)


def test_duplicate_private_case_and_missing_operation_rejected():
    cases = v.strict_json(inputs()["suite"])
    for bad in [[cases[0], cases[0]], [{**cases[0], "id": "x"}, cases[0]]]:
        with pytest.raises(ValueError):
            v.validate_suite(v.canonical(bad))
