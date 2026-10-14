"""Strict safe YAML loading with payload-free diagnostics."""

from pathlib import Path
from typing import cast

import yaml
from yaml.nodes import MappingNode

from living_world.cognition.npc_cognition_client import ActionRequest, NPCDecision
from living_world.replay.model import ProposalTape, ProposalTapeEntry, ProposalTapeError


class _Loader(yaml.SafeLoader):
    def construct_mapping(
        self, node: MappingNode, deep: bool = False
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key_node, value_node in node.value:
            key: object = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ProposalTapeError("invalid_tape")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def mapping(
    value: object, required: set[str], optional: set[str] | None = None
) -> dict[str, object]:
    if (
        not isinstance(value, dict)
        or not all(isinstance(key, str) for key in value)
        or not required <= value.keys()
        or value.keys() - required - (optional or set())
    ):
        raise ProposalTapeError("invalid_tape")
    return cast(dict[str, object], value)


class YAMLProposalTapeLoader:
    def load(self, path: Path) -> ProposalTape:
        try:
            value: object = yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)
            top = mapping(
                value,
                {"schema_version", "scenario_key", "scenario_fingerprint", "entries"},
            )
            if not isinstance(top["entries"], list):
                raise ProposalTapeError("invalid_tape")
            entries: list[ProposalTapeEntry] = []
            for raw in top["entries"]:
                entry = mapping(
                    raw, {"sequence", "actor_label", "action", "rationale"}, {"speech"}
                )
                action = entry["action"]
                request: ActionRequest | None = None
                if action is not None:
                    action_map = mapping(action, {"key", "target_label", "arguments"})
                    arguments = action_map["arguments"]
                    if not isinstance(arguments, dict):
                        raise ProposalTapeError("invalid_tape")
                    request = ActionRequest(
                        cast(str, action_map["key"]),
                        cast(str | None, action_map["target_label"]),
                        cast(str, entry["rationale"]),
                        cast(dict[str, str], arguments),
                    )
                entries.append(
                    ProposalTapeEntry(
                        cast(int, entry["sequence"]),
                        cast(str, entry["actor_label"]),
                        NPCDecision(cast(str | None, entry.get("speech")), request),
                        cast(str, entry["rationale"]),
                    )
                )
            return ProposalTape(
                cast(int, top["schema_version"]),
                cast(str, top["scenario_key"]),
                cast(str, top["scenario_fingerprint"]),
                tuple(entries),
            )
        except (
            OSError,
            UnicodeError,
            yaml.YAMLError,
            ValueError,
            TypeError,
            RecursionError,
        ):
            raise ProposalTapeError("invalid_tape") from None
