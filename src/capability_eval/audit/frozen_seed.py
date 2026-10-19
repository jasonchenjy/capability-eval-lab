"""Fixed-policy auditor for reviewed authoring artifacts; no generated tools."""

from inspect_ai.agent import agent
from inspect_ai.dataset import Sample
from inspect_petri.tools import send_message
from inspect_petri.target import controller

# Dish 0.3.4 does not publicly export its structured response classes.
# Keep this pinned-version dependency here; never parse its rendered tool text.
from petri_dish._target._types import DishResponseOutput, ScaffoldInjectionNotification

from capability_eval.creation.contracts import identity, load_frozen


def seed_sample(data, expected_sha256):
    bundle = load_frozen(data, expected_sha256)
    return Sample(
        id=expected_sha256,
        input=bundle.auditor_seed,
        metadata={
            "capability_id": bundle.spec.capability_id,
            "repository_url": bundle.spec.repository_url,
            "repository_revision": bundle.spec.repository_revision,
            "spec_sha256": identity(bundle.spec),
            "verifier_lock_sha256": bundle.verifier_lock_sha256,
        },
    )


def frozen_auditor(data, expected_sha256):
    bundle = load_frozen(data, expected_sha256)

    @agent
    def fixed():
        async def run(state):
            await send_message()(bundle.target_instruction)
            for _ in range(24):
                result = await controller().resume()
                if isinstance(result, ScaffoldInjectionNotification):
                    raise RuntimeError(
                        "Unexpected scaffold injection: rewriting is forbidden"
                    )
                if not isinstance(result, DishResponseOutput):
                    raise RuntimeError("Unexpected target response type")
                if result.intercepted_ids:
                    raise RuntimeError(
                        "Unexpected intercepted tool: simulation is forbidden"
                    )
                if not result.output.message.tool_calls:
                    return state
            raise RuntimeError("Frozen auditor resume limit exceeded")

        return run

    return fixed()


def native_audit_solver(data, expected_sha256):
    """Compose public Petri/Dish APIs; caller supplies sandbox/preparation/collection."""
    from inspect_petri import audit_solver
    from inspect_swe import interactive_codex_cli
    from petri_dish import dish_target
    from capability_eval.runtime.phase2 import PASSTHROUGH

    return audit_solver(
        auditor=frozen_auditor(data, expected_sha256),
        target=dish_target(
            interactive_codex_cli,
            passthrough_tools=set(PASSTHROUGH),
            injection_patterns=[],
            cwd="/workspace",
            web_search="disabled",
            goals=False,
        ),
    )
