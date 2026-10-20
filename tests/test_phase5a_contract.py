import io
import tarfile
from types import SimpleNamespace

import pytest

from capability_eval.verifier import phase5a as v


def base():
    return {
        v.EDIT_PATH: b"import re\n_line_ending_re = re.compile(r'bad',\n                             re.UNICODE)\n",
        "LICENSE": b"public license\n",
    }


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
    changed = {
        **base(),
        v.EDIT_PATH: base()[v.EDIT_PATH].replace(b"r'bad'", "r'é'".encode()),
    }
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
        ("contract_version", 3),
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


@pytest.mark.parametrize(
    "literal",
    [
        "__import__('os').system('true')",
        "f'{1}'",
        "b'bytes'",
        "'a' + 'b'",
        "'a', re.UNICODE); print('fake'); re.compile('b'",
        "'a' # comment",
    ],
)
def test_no_executable_expression_in_pattern(literal):
    modified = base()[v.EDIT_PATH].replace(b"r'bad'", literal.encode())
    with pytest.raises(ValueError):
        v.export_patch(base(), {**base(), v.EDIT_PATH: modified})


def test_reject_protocol_bypass_before_candidate_launch(monkeypatch):
    source = b'import os; os.write(1,b\'{"version":1,"value":[]}\'); os._exit(0)\n'
    patch = v.canonical(
        {
            "version": v.PATCH_VERSION,
            "base_tree": v.tree_digest(base()),
            "files": {v.EDIT_PATH: source.decode()},
        }
    )
    monkeypatch.setattr(v, "CandidateBox", lambda *a: pytest.fail("candidate launched"))
    result = v.verify(patch, **inputs())
    assert (result["status"], result["score"], result["completed"]) == (
        "invalid",
        None,
        0,
    )
    assert result["reason"] == "rejected:executable_source_changed"


def scenario_inputs():
    from capability_eval.validation.phase5a import EXPECTED

    controls = {n: n.encode() for n in EXPECTED}
    snapshot = {"repository": "repo", "revision": "revision"}
    scenario = {
        "schema_version": 2,
        "snapshot_manifest_sha256": v.digest(v.canonical(snapshot)),
        "repository": "repo",
        "revision": "revision",
        "verifier_lock_sha256": "lock",
        "verifier_strategy": v.VERSION,
        "edit_policy": v.EDIT_POLICY,
        "public_instruction_sha256": v.digest(b"instruction"),
        "controls": {n + ".patch": v.digest(data) for n, data in controls.items()},
    }
    return scenario, v.digest(v.canonical(scenario)), snapshot, controls


def test_scenario_and_all_control_identities():
    from capability_eval.validation.phase5a import check_scenario

    scenario, root, snapshot, controls = scenario_inputs()
    check_scenario(scenario, root, snapshot, "lock", b"instruction", controls)
    for name in controls:
        changed = {**controls, name: b"substitution"}
        with pytest.raises(ValueError, match="control_digest"):
            check_scenario(scenario, root, snapshot, "lock", b"instruction", changed)
    with pytest.raises(ValueError, match="scenario_approval"):
        check_scenario(
            {**scenario, "revision": "changed"},
            root,
            snapshot,
            "lock",
            b"instruction",
            controls,
        )
    with pytest.raises(ValueError, match="scenario_binding"):
        check_scenario(
            scenario, root, snapshot, "lock", b"changed instruction", controls
        )
    with pytest.raises(ValueError, match="control_inventory"):
        check_scenario(
            scenario, root, snapshot, "lock", b"instruction", {"correct": b"correct"}
        )


def test_duplicate_alternative_rejected_before_any_execution(monkeypatch, tmp_path):
    from capability_eval.validation import phase5a as q

    scenario, root, snapshot, controls = scenario_inputs()
    controls["alternative"] = controls["correct"]
    for n, data in controls.items():
        (tmp_path / (n + ".patch.json")).write_bytes(data)
    monkeypatch.setattr(
        v, "verify", lambda *a, **kw: pytest.fail("verification started")
    )
    with pytest.raises(ValueError, match="control_digest"):
        q.qualify(
            b"",
            snapshot,
            tmp_path,
            tmp_path / "output",
            {},
            "lock",
            scenario=scenario,
            expected_scenario=root,
            instruction=b"instruction",
        )
    assert not (tmp_path / "output").exists()
    # Even a newly approved root cannot call duplicate bytes an alternative.
    scenario["controls"]["alternative.patch"] = v.digest(controls["correct"])
    with pytest.raises(ValueError, match="positive_controls_must_differ"):
        q.check_scenario(
            scenario,
            v.digest(v.canonical(scenario)),
            snapshot,
            "lock",
            b"instruction",
            controls,
        )


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_control_inventory_is_exact(tmp_path, change):
    from capability_eval.validation.phase5a import load_controls

    _, _, _, controls = scenario_inputs()
    for name, data in controls.items():
        (tmp_path / (name + ".patch.json")).write_bytes(data)
    if change == "missing":
        (tmp_path / "correct.patch.json").unlink()
    else:
        (tmp_path / "extra.patch.json").write_bytes(b"extra")
    with pytest.raises(ValueError, match="control_inventory"):
        load_controls(tmp_path)


def test_distinct_envelopes_cannot_hide_duplicate_positive_trees(tmp_path, monkeypatch):
    from capability_eval.validation import phase5a as q

    args = inputs()
    patch = v.export_patch(base(), base())
    controls = {name: name.encode() for name in q.EXPECTED}
    controls["correct"] = patch
    controls["alternative"] = b"\n" + patch + b"\n"
    for name, data in controls.items():
        (tmp_path / (name + ".patch.json")).write_bytes(data)
    (tmp_path / "suite.json").write_bytes(args["suite"])
    scenario = {
        "schema_version": 2,
        "snapshot_manifest_sha256": v.digest(v.canonical(args["snapshot"])),
        "repository": None,
        "revision": None,
        "verifier_lock_sha256": args["expected_lock"],
        "verifier_strategy": v.VERSION,
        "edit_policy": v.EDIT_POLICY,
        "public_instruction_sha256": v.digest(b"task"),
        "controls": {n + ".patch": v.digest(data) for n, data in controls.items()},
    }
    monkeypatch.setattr(
        v, "verify", lambda *a, **kw: pytest.fail("verification started")
    )
    with pytest.raises(ValueError, match="positive_control_trees"):
        q.qualify(
            args["archive"],
            args["snapshot"],
            tmp_path,
            tmp_path / "output",
            args["lock"],
            args["expected_lock"],
            scenario=scenario,
            expected_scenario=v.digest(v.canonical(scenario)),
            instruction=b"task",
        )
    assert not (tmp_path / "output").exists()
