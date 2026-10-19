"""Strict, bounded handoff for the Phase 2 one-file fixture only."""

import codecs
import hashlib
import io
import re
import tokenize

BASE = b'VALUE = "before"\n'
BASE_SHA256 = hashlib.sha256(BASE).hexdigest()
MAX_PATCH = 65536


class InvalidPatch(ValueError):
    pass


def admit(patch: bytes, base_sha256: str) -> bytes:
    """Reconstruct bytes without running git, shell commands, or candidate code.

    This intentionally accepts one full-file hunk for fixture.py, not general
    repository patches. Modes, symlinks, renames and extra paths are rejected.
    """
    if base_sha256 != BASE_SHA256:
        raise InvalidPatch("base_mismatch")
    if not patch:
        return BASE
    if len(patch) > MAX_PATCH or b"\x00" in patch or b"\r" in patch:
        raise InvalidPatch("patch_size_or_encoding")
    try:
        patch.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidPatch("patch_encoding") from exc
    lines = patch.splitlines(keepends=True)
    if any(not line.endswith(b"\n") for line in lines):
        raise InvalidPatch("missing_final_newline")
    if lines.pop(0) != b"diff --git a/fixture.py b/fixture.py\n":
        raise InvalidPatch("path_not_allowed")
    if lines and lines[0].startswith(b"index "):
        if not re.fullmatch(rb"index [0-9a-f]+\.\.[0-9a-f]+ 100644\n", lines.pop(0)):
            raise InvalidPatch("mode_not_allowed")
    if len(lines) < 3 or lines[:2] != [b"--- a/fixture.py\n", b"+++ b/fixture.py\n"]:
        raise InvalidPatch("headers_not_allowed")
    hunk = re.fullmatch(rb"@@ -1(?:,1)? \+1(?:,([1-9][0-9]{0,4}))? @@\n", lines[2])
    if hunk is None:
        raise InvalidPatch("hunk_not_allowed")
    old, new = [], []
    for line in lines[3:]:
        if line[:1] not in (b" ", b"+", b"-"):
            raise InvalidPatch("hunk_body_not_allowed")
        if line[:1] in (b" ", b"-"):
            old.append(line[1:])
        if line[:1] in (b" ", b"+"):
            new.append(line[1:])
    if b"".join(old) != BASE or len(new) != int(hunk.group(1) or b"1"):
        raise InvalidPatch("hunk_mismatch")
    source = b"".join(new)
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
        if codecs.lookup(encoding).name != "utf-8":
            raise InvalidPatch("source_encoding_not_utf8")
        source.decode("utf-8")
    except (SyntaxError, LookupError, UnicodeError) as exc:
        raise InvalidPatch("source_encoding_invalid") from exc
    return source
