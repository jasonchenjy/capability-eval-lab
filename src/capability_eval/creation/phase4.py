"""Phase 4 CLI: draft, explicit review/freeze, and pinned verifier binding."""

import argparse
import asyncio
from pathlib import Path

from capability_eval.creation.contracts import (
    Draft,
    Review,
    TaskSpec,
    freeze,
    identity,
    save_new,
)
from capability_eval.creation.ground_truth import VerifierLock, make_lock
from capability_eval.runtime.phase3 import strict_json


def read(path, cls):
    return cls.model_validate(strict_json(path.read_bytes()))


def account_model(auth_path, model_name):
    from inspect_ai.model import GenerateConfig, get_model

    auth = strict_json(auth_path.read_bytes())["tokens"]
    return get_model(
        "openai/" + model_name,
        base_url="https://chatgpt.com/backend-api/codex",
        api_key=auth["access_token"],
        default_headers={
            "ChatGPT-Account-ID": auth["account_id"],
            "originator": "codex_cli_rs",
            "User-Agent": "capability-eval-lab-phase4",
        },
        responses_api=True,
        responses_store=False,
        streaming=True,
        config=GenerateConfig(
            max_retries=0,
            reasoning_effort="low",
            extra_body={
                "instructions": "Use the requested structured submission tool to propose an evaluation. Do not execute commands."
            },
        ),
    )


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    lock = commands.add_parser("lock")
    lock.add_argument("--hidden-tests", type=Path, required=True)
    lock.add_argument("--output", type=Path, required=True)
    draft = commands.add_parser("draft")
    draft.add_argument("--spec", type=Path, required=True)
    draft.add_argument("--codex-auth", type=Path, required=True)
    draft.add_argument("--model", default="gpt-6-luna")
    draft.add_argument("--output", type=Path, required=True)
    export = commands.add_parser("freeze")
    export.add_argument("--draft", type=Path, required=True)
    export.add_argument("--review", type=Path, required=True)
    export.add_argument("--verifier-lock", type=Path, required=True)
    export.add_argument("--expected-lock-sha256", required=True)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output must be new")
    if args.command == "lock":
        artifact = make_lock(args.hidden_tests.read_bytes())
    elif args.command == "draft":
        from capability_eval.creation.bloom import generate_draft

        artifact = asyncio.run(
            generate_draft(
                read(args.spec, TaskSpec),
                account_model(args.codex_auth, args.model),
                mode="live-account",
            )
        )
    else:
        verifier_lock = read(args.verifier_lock, VerifierLock)
        if identity(verifier_lock) != args.expected_lock_sha256:
            raise ValueError("Verifier lock changed")
        artifact = freeze(
            read(args.draft, Draft),
            read(args.review, Review),
            args.expected_lock_sha256,
        )
    save_new(args.output, artifact)
    print(identity(artifact))


if __name__ == "__main__":
    main()
