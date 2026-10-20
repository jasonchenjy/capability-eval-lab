"""Initial public task dispatch and resume only; no model, hints or intervention."""

import asyncio

from inspect_ai.agent import agent
from inspect_petri.tools import send_message
from inspect_petri.target import controller
from petri_dish._target._types import DishResponseOutput


def passive_auditor(instruction, ledger):
    @agent
    def passive():
        async def run(state):
            await send_message()(instruction)
            for _ in range(32):
                result = await controller().resume()
                if not isinstance(result, DishResponseOutput) or result.intercepted_ids:
                    raise RuntimeError("Passive policy forbids injection/simulation")
                calls = result.output.message.tool_calls or []
                for call in calls:
                    ledger.request(call)
                if not calls:
                    # The model bridge and ACP notifications have separate
                    # readers. Drain already-executed command notifications;
                    # never issue another command or advice to fill a gap.
                    for _ in range(100):
                        if ledger.finish()["complete"]:
                            break
                        await asyncio.sleep(0.05)
                    return state
            raise RuntimeError("Passive resume limit")

        return run

    return passive()
