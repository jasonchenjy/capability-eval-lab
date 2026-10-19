"""Disposable, bounded Docker execution; no host mounts or Docker socket inside."""

import json
import os
import selectors
import subprocess
import time
import uuid
from dataclasses import dataclass

IMAGE = "sha256:2688969f72923b9f2a60704f8504b0e13b9c28f3968e57e68e0f95da2a7aad5e"


class InfrastructureError(RuntimeError):
    pass


@dataclass
class Execution:
    returncode: int
    stdout: bytes
    stderr: bytes
    limit: str | None = None


def bounded(command, *, data=b"", timeout=15, max_output=65536):
    # Input is small and written from a file so a child that never reads cannot
    # block the timeout loop. Output is drained with a shared hard byte limit.
    import tempfile

    with tempfile.TemporaryFile() as stdin:
        stdin.write(data)
        stdin.seek(0)
        proc = subprocess.Popen(
            command, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = {proc.stdout: bytearray(), proc.stderr: bytearray()}
        deadline = time.monotonic() + timeout
        limit = None
        try:
            with selectors.DefaultSelector() as selector:
                for stream in output:
                    selector.register(stream, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        limit = "timeout"
                        break
                    for key, _ in selector.select(min(remaining, 0.1)):
                        chunk = os.read(key.fileobj.fileno(), 8192)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        available = max_output - sum(map(len, output.values()))
                        output[key.fileobj].extend(chunk[:available])
                        if len(chunk) > available:
                            limit = "output_limit"
                            break
                    if limit:
                        break
                if limit:
                    proc.kill()
                try:
                    proc.wait(timeout=max(0.01, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    limit = "timeout"
                    proc.kill()
                    proc.wait()
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            proc.stdout.close()
            proc.stderr.close()
        return Execution(
            proc.returncode,
            bytes(output[proc.stdout]),
            bytes(output[proc.stderr]),
            limit,
        )


def docker(*args, data=b"", timeout=30):
    try:
        result = bounded(["docker", *args], data=data, timeout=timeout)
    except OSError as exc:
        raise InfrastructureError("docker_unavailable") from exc
    if result.limit or result.returncode:
        raise InfrastructureError("docker_operation_failed")
    return result.stdout


class Sandbox:
    def __init__(self, role, image=IMAGE):
        self.name = f"capability-phase3-{role}-{uuid.uuid4().hex[:12]}"
        self.image = image
        self.boundaries = None

    def __enter__(self):
        try:
            docker(
                "create",
                "--pull",
                "never",
                "--name",
                self.name,
                "--network",
                "none",
                "--read-only",
                "--user",
                "65534:65534",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--cpus",
                "1",
                "--memory",
                "256m",
                "--memory-swap",
                "256m",
                "--pids-limit",
                "64",
                "--ipc",
                "none",
                "--log-driver",
                "none",
                "--init",
                "--tmpfs",
                "/workspace:rw,noexec,nosuid,nodev,size=8m,uid=65534,gid=65534",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,nodev,size=16m,uid=65534,gid=65534",
                "--workdir",
                "/workspace",
                self.image,
                "sleep",
                "infinity",
            )
            docker("start", self.name)
            info = json.loads(docker("inspect", self.name))[0]
            h = info["HostConfig"]
            self.boundaries = {
                "image": info["Image"],
                "network": h["NetworkMode"],
                "readonly_rootfs": h["ReadonlyRootfs"],
                "user": info["Config"]["User"],
                "cap_drop": h["CapDrop"],
                "security_opt": h["SecurityOpt"],
                "memory": h["Memory"],
                "memory_swap": h["MemorySwap"],
                "nano_cpus": h["NanoCpus"],
                "pids_limit": h["PidsLimit"],
                "binds": h["Binds"],
                "mounts": info["Mounts"],
                "tmpfs": h["Tmpfs"],
                "privileged": h["Privileged"],
            }
            if (
                info["Image"] != self.image
                or h["NetworkMode"] != "none"
                or not h["ReadonlyRootfs"]
                or info["Config"]["User"] != "65534:65534"
                or h["CapDrop"] != ["ALL"]
                or "no-new-privileges:true" not in h["SecurityOpt"]
                or h["Memory"] != 256 * 1024 * 1024
                or h["MemorySwap"] != h["Memory"]
                or h["NanoCpus"] != 1_000_000_000
                or h["PidsLimit"] != 64
                or h["Privileged"]
                or h["Binds"]
                or any(m["Type"] != "tmpfs" for m in info["Mounts"])
            ):
                raise InfrastructureError("sandbox_boundary_mismatch")
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def put(self, name, content):
        if name not in {"fixture.py", "hidden-tests.json"}:
            raise ValueError("Unexpected sandbox file")
        script = (
            "import pathlib,sys; "
            f"p=pathlib.Path('/workspace/{name}'); "
            "p.write_bytes(sys.stdin.buffer.read()); p.chmod(0o444)"
        )
        docker("exec", "-i", self.name, "python3", "-I", "-c", script, data=content)

    def python(self, script, *, timeout=5):
        try:
            return bounded(
                ["docker", "exec", "-i", self.name, "python3", "-I", "-B", "-"],
                data=script.encode(),
                timeout=timeout,
            )
        except OSError as exc:
            raise InfrastructureError("docker_unavailable") from exc

    def __exit__(self, *_):
        docker("rm", "-f", self.name)
