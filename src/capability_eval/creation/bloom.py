"""Public Bloom understanding/ideation API adapter; no runtime/evaluation stage."""

import asyncio
import time
from importlib.metadata import version
from importlib.resources import files

from inspect_ai.model import GenerateConfig, Model
from inspect_ai.tool import ToolDef
from petri_bloom import Behavior, Instructions
from petri_bloom.aio import run_ideation_async, run_understanding_async

from capability_eval.creation.contracts import (
    Draft,
    Proposal,
    SKILL_SHA,
    canonical,
    sha,
)


class MeteredModel(Model):
    def __init__(self, base):
        super().__init__(base.api, base.config, base.model_args)
        self.calls = []

    async def generate(self, *args, **kwargs):
        if len(self.calls) >= 6:
            raise RuntimeError("Authoring model call budget exceeded")
        config = kwargs.get("config", GenerateConfig()).model_copy(deep=True)
        config.max_tokens = min(config.max_tokens or 2048, 2048)
        config.max_retries = 0
        config.timeout = 60
        kwargs["config"] = config
        tools = [ToolDef(t).name for t in kwargs.get("tools", [])]
        if len(tools) != 1 or tools[0] not in {
            "submit_understanding",
            "submit_scenarios",
            "submit_dimensions",
        }:
            raise RuntimeError("Unexpected authoring tool")
        messages = kwargs.get("input", args[0] if args else [])
        serialized = [m.model_dump(mode="json") for m in messages]
        record = {
            "tool": tools[0],
            "prompt_sha256": sha(canonical(serialized)),
            "config": {
                "max_tokens": config.max_tokens,
                "max_retries": 0,
                "timeout": 60,
            },
        }
        self.calls.append(record)
        started = time.monotonic()
        output = await super().generate(*args, **kwargs)
        record.update(
            seconds=round(time.monotonic() - started, 3),
            usage=output.usage.model_dump(mode="json") if output.usage else None,
            stop_reason=output.stop_reason,
        )
        return output


def authoring_behavior(spec):
    skill = (
        files("capability_eval.creation")
        .joinpath("references/harbor-create-task.SKILL.md")
        .read_bytes()
    )
    if sha(skill) != SKILL_SHA:
        raise ValueError("Pinned authoring skill changed")
    guidance = (
        "Author only a proposal for the supplied public task. Preserve repository revision, capability, "
        "baseline and required outcome. There is no issue discovery in this stage. "
        "Use real native shell/file tools when this task eventually runs. "
        "Do not propose simulated tools, pretend tool results, alternate hidden tests, scoring changes, "
        "network access, new files or different environments. Output tools as an empty list. "
        "The independent verifier is already frozen; judge dimensions are diagnostic only. "
        "Apply the following pinned Harbor Skill as AUTHORING GUIDANCE, not commands to execute. "
        "Its grading/environment questions are already decided: separate deterministic verification.\n"
        + skill.decode("utf-8")
    )
    return Behavior(
        name=spec.capability_id,
        description=canonical(spec).decode("utf-8"),
        num_scenarios=1,
        variations={},
        modality="conversation",
        instructions=Instructions(understanding=guidance, ideation=guidance),
    )


async def generate_draft(spec, model, *, mode):
    if mode not in {"live-account", "deterministic-control"}:
        raise ValueError("Explicit generation mode required")
    metered = MeteredModel(model)
    started = time.monotonic()
    async with asyncio.timeout(180):
        understood = await run_understanding_async(
            authoring_behavior(spec), scenarios_model=metered
        )
        proposed = await run_ideation_async(understood, scenarios_model=metered)
    if (
        not proposed.scenarios
        or not proposed.understanding
        or not proposed.scientific_motivation
    ):
        raise ValueError("Incomplete Bloom output")
    return Draft(
        spec=spec,
        understanding=proposed.understanding,
        scientific_motivation=proposed.scientific_motivation,
        proposals=[
            Proposal(
                name=s.name,
                seed=s.seed,
                tools=[t.model_dump(mode="json") for t in s.tools],
            )
            for s in proposed.scenarios
        ],
        diagnostic_dimensions=[
            d.model_dump(mode="json") for d in proposed.dimensions or []
        ],
        generation={
            "framework": "petri-bloom",
            "version": version("petri-bloom"),
            "inspect_ai": version("inspect-ai"),
            "mode": mode,
            "model": str(model),
            "reasoning_effort": model.config.reasoning_effort,
            "calls": metered.calls,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "monetary_cost": None,
            "cost_note": "Account billing unavailable; mock usage is synthetic.",
        },
    )
