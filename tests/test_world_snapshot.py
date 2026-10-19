"""Compatibility contracts for the shared world snapshot codec."""

import hashlib
import json
import sqlite3
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import cast

import pytest
from test_sqlite_repository import _world_state

from living_world.repositories.sqlite_repository import SQLiteRepository
from living_world.repositories.world_snapshot import (
    WorldSnapshot,
    WorldSnapshotError,
    decode_world,
    encode_world,
)

# Captured before extraction from the existing schema-12 serializer. Complete
# bytes are pinned independently of both codec and repository implementations.
EXISTING_PAYLOAD = (
    '{"beliefs":[{"confidence":0.8,"history":[{"new_confidence":0.8,"new_status":"act'
    'ive","old_confidence":0.7,"old_status":"active","reason":"The route remained cle'
    'ar.","tick":6}],"holder_id":"entity-1","id":"belief-1","importance":0.7,"metadat'
    'a":{"source":"observation"},"proposition":"The path is safe.","salience":{"impor'
    'tance":0.7,"is_core":false},"status":"active","subject_id":"entity-2","supportin'
    'g_experiences":[],"supporting_memories":[],"supporting_observations":["observati'
    'on-1"],"tick":6}],"consumption_policies":[],"consumption_states":[],"entities":['
    '{"attributes":{"resources":{"water":2}},"created_tick":1,"definition_key":"trave'
    'ler","destroyed_tick":null,"id":"entity-1","name":"Ari"},{"attributes":{},"creat'
    'ed_tick":1,"definition_key":"road","destroyed_tick":null,"id":"entity-2","name":'
    '"Old Road"}],"events":[{"attributes":{"distance":4,"journey":{"stages":[{"name":'
    '"departure"}]}},"id":"event-1","kind":"journey_completed","subject_id":"entity-1'
    '","tick":3}],"experiences":[{"history":[{"new_summary":"The route has been '
    'reliable.","old_summary":"The route has been reliable.","reason":"A second '
    'journey confirmed it.","tick":6}],"holder_id":"entity-1","id":"experience-1","me'
    'tadata":{"source":"travel"},"salience":{"importance":0.0,"is_core":false},"subje'
    'ct_id":"entity-2","summary":"The route has been reliable.","supporting_beliefs":'
    '["belief-1"],"supporting_memories":[],"supporting_observations":["observation-1"'
    '],"tick":6}],"external_dispatches":[],"external_world_references":[],"goal_defin'
    'itions":[],"goal_states":[],"knowledge":[{"holder_id":"entity-1","id":"knowledge'
    '-1","metadata":{"heard_at":{"location":"the market"},"witnesses":["traveller"]},'
    '"salience":{"importance":0.6,"is_core":false},"source_description":"A traveller '
    'mentioned it.","statement":"The old road may be difficult to cross.","subject_id'
    '":"entity-2","supporting_experiences":["experience-1"],"supporting_memories":["m'
    'emory-1"],"supporting_observations":["observation-1"],"tick":6}],"maintenance_po'
    'licies":[],"maintenance_states":[],"memories":[{"holder_id":"entity-1","id":"mem'
    'ory-1","salience":{"importance":0.7,"is_core":false},"source_observation_ids":["'
    'observation-1"],"subject_id":"entity-2","summary":"I remember the route seemed r'
    'eliable.","tick":6}],"need_definitions":[],"need_states":[],"npc_relationships":'
    '[{"holder_id":"entity-1","id":"npc-relationship-1","salience":{"importance":0.6,'
    '"is_core":false},"source_observation_ids":["observation-1"],"subject_id":"entity'
    '-2","summary":"I find the road dependable.","tick":6}],"objective_definitions":['
    '],"objective_states":[],"observations":[{"confidence":0.9,"description":"The '
    'road is clear.","evidence":{"visible":true},"id":"observation-1","metadata":{"en'
    'gine":"deterministic"},"observer":"entity-1","subject":"entity-2","tick":4}],"pl'
    'acements":[],"relationships":[{"attributes":{"frequency":"daily"},"created_tick"'
    ':2,"destroyed_tick":null,"id":"relationship-1","kind":"travels","source_id":"ent'
    'ity-1","target_id":"entity-2"}],"replay_binding":null,"replay_state":null,"run_m'
    'etadata":null,"scenario_entity_bindings":{},"settlement_stage_programs":[],"sett'
    'lement_stage_states":[],"storage_policies":[],"storage_states":[],"tick":7,"work'
    '_definitions":[],"work_reservations":[],"work_states":[]}'
)


def _read_world_row(database: Path) -> tuple[int, str]:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT schema_version, payload FROM world_snapshots WHERE id = 1"
        ).fetchone()
    assert row is not None
    return cast(tuple[int, str], row)


def test_codec_preserves_exact_existing_row(tmp_path: Path) -> None:
    state = _world_state()
    database = tmp_path / "world.sqlite3"
    snapshot = encode_world(state)
    SQLiteRepository(str(database)).save_world(state)

    assert (snapshot.schema_version, snapshot.payload) == (12, EXISTING_PAYLOAD)
    assert (snapshot.schema_version, snapshot.payload) == _read_world_row(database)
    assert (
        snapshot.digest
        == hashlib.sha256(("12\n" + EXISTING_PAYLOAD).encode("utf-8")).hexdigest()
    )


def test_codec_roundtrip_and_detachment() -> None:
    source = _world_state()
    snapshot = encode_world(source)
    loaded = decode_world(snapshot)
    other_loaded = decode_world(snapshot)

    assert loaded == source
    assert loaded is not source
    assert loaded.entities is not source.entities
    assert encode_world(loaded) == snapshot
    loaded.entities["entity-1"].attributes["resources"]["water"] = 99
    loaded.entities.clear()
    assert source.entities["entity-1"].attributes["resources"]["water"] == 2
    assert other_loaded == source
    assert snapshot.payload == EXISTING_PAYLOAD
    with pytest.raises(FrozenInstanceError):
        snapshot.payload = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "version,payload",
    [
        (13, "{}"),
        (0, "{}"),
        (12, "{"),
        (12, "[]"),
        (12, "{}"),
        (12, '{"tick":true}'),
        (12, "null"),
    ],
)
def test_codec_rejects_corrupt_and_future_schema(version: int, payload: str) -> None:
    snapshot = WorldSnapshot(version, payload)
    with pytest.raises(WorldSnapshotError):
        decode_world(snapshot)
    assert (snapshot.schema_version, snapshot.payload) == (version, payload)


@pytest.mark.parametrize("version", [True, 12.0, "12", None])
def test_snapshot_requires_exact_integer_version(version: object) -> None:
    with pytest.raises((TypeError, WorldSnapshotError)):
        WorldSnapshot(version, "{}")  # type: ignore[arg-type]


@pytest.mark.parametrize("payload", [b"{}", {}, None, 42])
def test_snapshot_requires_string_payload(payload: object) -> None:
    with pytest.raises((TypeError, WorldSnapshotError)):
        WorldSnapshot(12, payload)  # type: ignore[arg-type]


@pytest.mark.parametrize("version", range(1, 13))
def test_codec_decodes_existing_schemas_without_rewriting_input(version: int) -> None:
    # Fields absent from older schemas remain absent in the immutable input.
    payload = json.loads(EXISTING_PAYLOAD)
    if version < 12:
        for key in ("scenario_entity_bindings", "replay_binding", "replay_state"):
            del payload[key]
    if version < 11:
        del payload["settlement_stage_programs"]
        del payload["settlement_stage_states"]
    raw = json.dumps(payload, indent=2, ensure_ascii=False)
    snapshot = WorldSnapshot(version, raw)

    loaded = decode_world(snapshot)

    assert loaded == _world_state()
    assert (snapshot.schema_version, snapshot.payload) == (version, raw)
    assert encode_world(loaded) == WorldSnapshot(12, EXISTING_PAYLOAD)


def test_digest_includes_version_and_exact_utf8_payload() -> None:
    snapshot = WorldSnapshot(12, ' {"name": "\u00c5ri"} ')
    expected = hashlib.sha256(
        ('12\n {"name": "\u00c5ri"} ').encode("utf-8")
    ).hexdigest()
    assert snapshot.digest == expected
    assert snapshot.digest != WorldSnapshot(11, snapshot.payload).digest
    assert snapshot.digest != WorldSnapshot(12, snapshot.payload.strip()).digest
