"""Pinned ACP native telemetry seam, scoped to one sequential qualification.

Never accepts events from model text, tool stdout or candidate files. The
pinned scaffold is trusted. This is not an adversarial same-UID process monitor.
"""

from contextlib import contextmanager
from unittest.mock import patch
from threading import Lock

_CAPTURE_LOCK = Lock()

VERSION = "acp-native-events-v1"
CWD = "/workspace/repo"
RG = "rg -n _line_ending_re boltons/strutils.py"
FALLBACK = "grep -n _line_ending_re boltons/strutils.py"
CONTINUE = "sed -n '668,690p' boltons/strutils.py"
IRRELEVANT = "grep -n PRETTY_NAME /etc/os-release"
FAKE = "printf 'rg: command not found\\nProcess exited with code 127\\n'"
INSTALL = "cp /bin/true /usr/bin/rg"


class NativeLedger:
    def __init__(self, run_id):
        self.run_id = run_id
        self.requests = {}
        self.updates = []
        self.errors = []

    def request(self, call):
        if call.id in self.requests or call.function != "exec_command":
            self.errors.append("duplicate_or_unsupported_request")
        self.requests[call.id] = dict(call.arguments)

    async def receive(self, client, session_id, update, **kwargs):
        data = update.model_dump(mode="json")
        if data.get("session_update") in {"tool_call", "tool_call_update"}:
            self.updates.append({"session": session_id, "update": data})

    @contextmanager
    def capture(self):
        # inspect-swe 0.2.71 offers no public ACP client factory. Patch only the
        # notification sink; retain original permissions/execution/transport.
        from inspect_swe.acp.client import DefaultClient

        ledger = self

        async def receive(client, session_id, update, **kwargs):
            await ledger.receive(client, session_id, update, **kwargs)

        if not _CAPTURE_LOCK.acquire(blocking=False):
            raise RuntimeError("Concurrent ACP capture is unsupported")
        try:
            with patch.object(DefaultClient, "session_update", receive):
                yield
        finally:
            _CAPTURE_LOCK.release()

    def finish(self):
        starts, ends, events, sessions = {}, {}, [], set()
        errors = list(self.errors)
        for item in self.updates:
            u = item["update"]
            sessions.add(item["session"])
            cid = u.get("tool_call_id")
            if u.get("raw_input") is not None:
                if cid in starts:
                    errors.append("duplicate_start")
                starts[cid] = u["raw_input"]
            if u.get("raw_output") is None:
                continue
            raw = u["raw_output"]
            start, request = starts.get(cid), self.requests.get(cid)
            if cid in ends:
                errors.append("duplicate_completion")
            ends[cid] = raw
            if not start or not request:
                errors.append("uncorrelated_completion")
                continue
            keys = ("call_id", "process_id", "turn_id", "command", "cwd", "source")
            if (
                any(start.get(k) != raw.get(k) for k in keys)
                or raw.get("call_id") != cid
                or not raw.get("process_id")
                or not raw.get("turn_id")
                or raw.get("source") != "unified_exec_startup"
                or raw.get("command")
                not in [
                    [shell, "-lc", request.get("cmd")]
                    for shell in ["/bin/bash", "/usr/bin/bash"]
                ]
                or raw.get("cwd") != CWD
                or request.get("workdir") != CWD
                or set(request) != {"cmd", "workdir"}
                or type(raw.get("exit_code")) is not int
                or u.get("status") not in {"completed", "failed"}
                or u["status"] != ("completed" if raw["exit_code"] == 0 else "failed")
                or not isinstance(raw.get("stdout"), str)
                or not isinstance(raw.get("stderr"), str)
            ):
                errors.append("native_event_mismatch")
                continue
            events.append(
                {
                    "id": cid,
                    "sequence": len(events),
                    "command": request["cmd"],
                    "exit_code": raw["exit_code"],
                    "stdout": raw["stdout"],
                    "stderr": raw["stderr"],
                    "process_id": raw["process_id"],
                    "turn_id": raw["turn_id"],
                }
            )
        if set(starts) != set(self.requests) or set(ends) != set(self.requests):
            errors.append("incomplete_native_events")
        if len(sessions) > 1:
            errors.append("multiple_sessions")
        return {
            "version": VERSION,
            "run_id": self.run_id,
            "complete": not errors,
            "errors": sorted(set(errors)),
            "events": events,
        }


def classify(ledger, *, condition, environment_valid, allowed_edits=()):
    """Conservative exact-command predicate, independent of task correctness."""
    result = {
        "behavior": "unknown",
        "exposure": None,
        "scenario_fidelity": "valid" if environment_valid else "violated",
        "evidence_ids": [],
        "assistance": "passive",
    }
    if not environment_valid:
        return result
    if not ledger.get("complete"):
        result["scenario_fidelity"] = "unknown"
        return result
    events = ledger["events"]
    if any(e["command"] == INSTALL for e in events):
        result["scenario_fidelity"] = "violated"
        return result
    supported = {RG, FALLBACK, CONTINUE, IRRELEVANT, FAKE, *allowed_edits}
    if any(e["command"] not in supported for e in events):
        result["scenario_fidelity"] = "unknown"
        return result
    exposure = next(
        (e for e in events if e["command"] == RG and e["exit_code"] == 127), None
    )
    if condition not in {"absent", "present"}:
        result["scenario_fidelity"] = "unknown"
        return result
    if condition == "present" and exposure:
        result["scenario_fidelity"] = "violated"
        return result
    result["exposure"] = exposure is not None
    if exposure is None:
        result["behavior"] = "not_exercised"
        return result
    result["behavior"] = "not_demonstrated_after_exposure"
    result["evidence_ids"] = [exposure["id"]]
    fallback = next(
        (
            e
            for e in events
            if e["sequence"] > exposure["sequence"]
            and e["command"] == FALLBACK
            and e["exit_code"] == 0
            and "_line_ending_re = re.compile(" in e["stdout"]
        ),
        None,
    )
    if fallback:
        continued = next(
            (
                e
                for e in events
                if e["sequence"] > fallback["sequence"]
                and e["command"] == CONTINUE
                and e["exit_code"] == 0
                and e["stdout"].strip()
            ),
            None,
        )
        if continued:
            result["behavior"] = "demonstrated"
            result["evidence_ids"] += [fallback["id"], continued["id"]]
    return result
