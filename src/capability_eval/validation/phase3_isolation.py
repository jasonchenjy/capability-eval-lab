"""Measure both sandbox roles; never execute a candidate in the grader."""

import json

from capability_eval.verifier.handoff import BASE
from capability_eval.verifier.sandbox import Sandbox

PROBE = """
import errno, json, os, socket
from pathlib import Path
checks = {
    'nonroot': os.getuid() == 65534,
    'no_docker_socket': not Path('/var/run/docker.sock').exists(),
    'no_host_auth': not os.access('/root/.codex/auth.json', os.R_OK),
    'hidden_tests_present': Path('/workspace/hidden-tests.json').exists(),
    'candidate_present': Path('/workspace/fixture.py').exists(),
    'cpu': Path('/sys/fs/cgroup/cpu.max').read_text().strip(),
    'memory': Path('/sys/fs/cgroup/memory.max').read_text().strip(),
    'pids': Path('/sys/fs/cgroup/pids.max').read_text().strip(),
}
s = socket.socket()
s.settimeout(1)
try:
    checks['egress_errno'] = s.connect_ex(('1.1.1.1', 443))
finally:
    s.close()
try:
    Path('/etc/phase3-write-probe').write_text('probe')
    checks['root_write_blocked'] = False
except OSError as e:
    checks['root_write_blocked'] = e.errno in (errno.EROFS, errno.EACCES)
print(json.dumps(checks))
"""


def check_isolation(hidden_tests):
    evidence = {}
    for role in ("candidate", "grader"):
        with Sandbox(role) as box:
            box.put(
                "fixture.py" if role == "candidate" else "hidden-tests.json",
                BASE if role == "candidate" else hidden_tests,
            )
            run = box.python(PROBE)
            if run.limit or run.returncode:
                raise RuntimeError("Isolation observation failed")
            checks = json.loads(run.stdout)
            if not (
                checks["nonroot"]
                and checks["no_docker_socket"]
                and checks["no_host_auth"]
                and checks["root_write_blocked"]
                and checks["egress_errno"] == 101
                and checks["hidden_tests_present"] == (role == "grader")
                and checks["candidate_present"] == (role == "candidate")
                and checks["cpu"] == "100000 100000"
                and checks["memory"] == "268435456"
                and checks["pids"] == "64"
            ):
                raise RuntimeError("Isolation contract failed")
            evidence[role] = {"observed": checks, "boundaries": box.boundaries}
    return evidence
