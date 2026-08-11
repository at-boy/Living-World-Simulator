from living_world.cognition.action_resolution import ActionResolution, NPCActionResolver
from living_world.cognition.npc_cognition_client import ActionOption, ActionRequest
from living_world.simulation.simulation_engine import SimulationEngine


def test_engine_delegates_npc_action_without_cognition_or_llm_input() -> None:
    resolver = NPCActionResolver((ActionOption("wait", "Wait quietly."),))

    result = SimulationEngine().resolve_npc_action(
        resolver=resolver,
        actor_id="entity_000001",
        request=ActionRequest("wait", None, "I should pause."),
    )

    assert result == ActionResolution(
        False, "No handler supports the requested action."
    )
