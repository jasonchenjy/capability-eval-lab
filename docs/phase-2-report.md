# Phase 2 — real Dish passthrough execution

Phase 2 execution validation passed on 2026-10-19. This is a narrow transport/filesystem experiment, not a hidden-test benchmark or evidence that Dish is superior to Harbor. Phase 3 is not authorized.

## Executed results

| Run | Inference | Native execution | Independent filesystem result | Patch reconstruction |
|---|---|---|---|---|
| `native-02` | Deterministic Inspect mock responses | Real Codex ACP scaffold, `exec_command` passthrough | File changed; fresh on-disk nonce and imported value in receipt match | Pass |
| `simulated-01` | Same deterministic responses | All tools intercepted; auditor deliberately fabricates success | File unchanged, receipt absent, patch empty; negative control passes | Pass, unchanged base |
| `live-01` | Account-backed `openai/gpt-6-luna`, low reasoning | Real Codex ACP scaffold, four `exec_command` calls | File changed; nonce, imported value and cwd match | Pass |

The live run completed in 35 seconds with five model calls. Inspect reports 35,099 uncached input tokens, 7,936 cache-read tokens and 530 output tokens, total 43,565. Monetary cost is not provided by this account-backed run. Deterministic mock token counts are synthetic and must not be used as model cost measurements.

The live agent read the challenge, tried shell executables `apply_patch` and `python`, observed missing-command errors, inspected available tools, and succeeded using `sed` and `python3`. The actual native tool was **`exec_command`**. Although `apply_patch` is in the configured passthrough set, this run does not prove the separate `apply_patch` tool path. The observed recovery is incidental to this smoke task; it is not the planned historical/new rg recovery benchmark.

Curated [evidence](evidence/phase2/) includes native tool calls/results, auditor events, independent observations, exported patches, patch reconstruction results, log hashes and environment provenance. Raw Inspect logs stay under ignored `work/phase2/`; they are not committed.

## Minimal integration used

`runtime/phase2.py` composes public `audit_solver`, `dish_target`, and `interactive_codex_cli` APIs. A fixed auditor sends one reviewed seed and resumes until completion. It has no positive-run path that fabricates tool output, rewrites environment text, restarts or rolls back. The policy test verifies the restricted public tool set contains only send/resume/end. The intentional simulation control alone calls `send_tool_call_result`.

The target factory is Inspect SWE's built-in Codex CLI ACP integration. Specifically, it runs **codex-acp 0.16.0 with its embedded Codex core**, rather than the host's `codex` executable. The global host CLI is broken; it was not repaired or used. The native adapter package is deprecated in favor of `@agentclientprotocol/codex-acp`, but 0.16.0 is the exact package family expected by Inspect SWE 0.2.71. It is preinstalled to avoid Inspect SWE's floating npm version resolver. No upstream implementation was edited, forked, or vendored.

Dish's default simulation path is insufficient for this goal. Its existing public `passthrough_tools` option was sufficient for this tested native shell path; no custom command execution bridge was necessary. Inspect's bridge routes inference from the container to the trusted controller. The account token is read from the existing Codex auth file by the controller; the scaffold receives only Inspect's dummy `api-key`. Account credentials are never mounted in the sandbox. The test uses an explicit Responses endpoint and no token refresh implementation. Expired authorization must fail rather than silently changing authentication.

After the audit, the controller reads files via a separate sandbox operation and checks exact bytes and a fresh nonce. An offline reviewer applies the exported toy patch to a fresh initialized Git directory and compares resulting bytes with the independently collected file. This is proof of this known fixture's artifact, not a general untrusted patch admission implementation or a Phase 3 verifier.

## Environment and measured boundaries

- Python controller: 3.13.12; Inspect AI 0.3.282, Petri 3.1.1, Dish 0.3.4, Inspect SWE 0.2.71; exact resolved versions in `uv.lock`.
- Dedicated Linux arm64 image, Node 22.22.0 and codex-acp 0.16.0. Base image digest, final image identity, npm integrity hashes, adapter binary hash and Debian package inventory are in `environment.json`.
- Executed image: `sha256:2688969f72923b9f2a60704f8504b0e13b9c28f3968e57e68e0f95da2a7aad5e`.
- Docker inspection and in-container cgroups confirmed 1 CPU, 2 GiB memory and 128-process limit. Network mode was `none`; a direct IP egress attempt returned errno 101. No mounts, Docker socket, host auth file or privileged mode; all Linux capabilities dropped and no-new-privileges enabled.
- Each task has a 240-second execution limit. Root runs inside the container; no disk quota is imposed. Containers share the VM kernel. These observations are not a hostile-code isolation qualification.
- No private tests, oracle or original task package was supplied. Their isolation must still be designed and tested in Phase 3. This probe does not establish that a malicious candidate cannot exploit the framework's model/tool bridge.
- All probe containers were removed by framework cleanup.

## Validation and discovered issues

Six package/policy/completion tests pass. The post-review regression exercises the actual collection solver: an unchanged negative control passes, while a modified or empty challenge nonce fails. This regression failed before the nonce check was added and passed after it. The original model runs were not repeated for this validation-only fix. The completion gate rejects a successful-looking Inspect evaluation if its sample is limited, errored, missing independent observations or has a mismatched filesystem outcome. Final completion checks were replayed against all three actual logs. Offline patch reconstruction passed for each run.

The initial `native-01` attempt failed because the image lacked `curl`, which Inspect SWE needs for MCP readiness. Adding curl fixed setup; it was an infrastructure failure, not a model failure. The successful runs emitted AnyIO object-destructor warnings during interpreter shutdown, after successful collection; they are retained in raw console logs and should be tracked as an upstream cleanup concern. There were no sample limits or errors in the three accepted runs.

After execution, assertions were replaced with explicit failure exceptions and completion checks were hardened; these changes affect validation, not scaffold/inference execution. `executed-source.json` records the exact harness hash used by the runs. The offline reviewer was corrected to serialize Inspect ToolCall dataclasses; this only affected report generation. No additional live model run was needed for these post-run checks.

## Reproduction

Run from the repository root with Python 3.13, uv 0.13.2, Docker and Docker Compose/buildx. Use your actual Docker endpoint; this machine uses `unix:///Users/junyu/.colima/default/docker.sock`. All caches and raw outputs below stay in this repository.

```sh
export DOCKER_HOST=unix:///Users/junyu/.colima/default/docker.sock
export XDG_CACHE_HOME="$PWD/work/cache"
export XDG_DATA_HOME="$PWD/work/data"
export UV_CACHE_DIR="$PWD/work/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/work/python"
uv sync --locked --extra research
# Set DOCKER_CONFIG to your installed compose/buildx configuration if necessary.
docker build -t capability-eval-phase2:0.1 -f configs/phase2/Dockerfile configs/phase2
python -m capability_eval.runtime.phase2 --output work/phase2/native-NEW --compose "$PWD/configs/phase2/compose.yaml"
python -m capability_eval.runtime.phase2 --output work/phase2/simulated-NEW --compose "$PWD/configs/phase2/compose.yaml" --negative
python -m capability_eval.runtime.phase2 --output work/phase2/live-NEW --compose "$PWD/configs/phase2/compose.yaml" --codex-auth /path/to/existing/codex/auth.json --model gpt-6-luna
python -m capability_eval.validation.phase2_evidence work/phase2/live-NEW
```

Use `.venv/bin/python` or activate the venv for the Python commands. Output directories must be fresh. Rebuilding uses Debian package repositories; the resulting image may differ. Record the resulting image identity and revalidate; the committed evidence identifies the exact image used here. The compose file's local tag is a convenience, not an immutable deployment guarantee.

## Scope decision

The native shell/file-edit path works through public Dish integration with the pinned Codex ACP scaffold. Continue only with explicit Phase 3 approval to build independent hidden-test execution and robust patch/status contracts. Auditor creativity, Bloom generation, automatic issue discovery, broad coding capability, native apply_patch coverage and Harbor replacement remain unproven.
