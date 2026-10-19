"""Real Chrome DOM behavior using actual FastAPI responses."""

import json
import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from test_inspection_api import ASGIClient

from living_world.api.inspection import _snapshot_value
from living_world.api.server import create_app
from living_world.core.definition import Definition
from living_world.core.event import Event
from living_world.simulation.simulation_engine import SimulationEngine

playwright = pytest.importorskip(
    "playwright.sync_api",
    reason="Install browser-tests extra for real browser verification",
)
from playwright.sync_api import Page, Route, expect, sync_playwright


@pytest.fixture
def inspector_page() -> Iterator[tuple[Page, SimulationEngine, list[str]]]:
    executable = os.environ.get(
        "LIVING_WORLD_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
    )
    if not Path(executable).is_file():
        pytest.skip("Chrome absent; set LIVING_WORLD_BROWSER_EXECUTABLE")
    engine = SimulationEngine()
    engine.definitions.register(
        Definition("thing", initial_attributes={"resources": {"wood": 7}})
    )
    entity = engine.entities.create(
        definition_key="thing", name="<img src=x onerror=alert(1)>"
    )
    engine.events.add(
        Event(id="evidence_1", tick=0, kind="observed", subject_id=entity.id)
    )
    app = create_app(engine)
    methods: list[str] = []

    def serve(route: Route) -> None:
        methods.append(route.request.method)

        with ThreadPoolExecutor(max_workers=1) as executor:
            response = executor.submit(
                ASGIClient(app).request,
                route.request.method,
                urlsplit(route.request.url).path,
            ).result()
        route.fulfill(
            status=response.status_code,
            headers=dict(response.headers),
            body=response.body,
        )

    with sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=executable, headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.route("**/*", serve)
        yield page, engine, methods
        context.close()
        browser.close()


def test_navigation_literal_text_history_keyboard_and_read_only(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, engine, methods = inspector_page
    before = _snapshot_value(engine.state)
    page.goto("http://inspector.test/inspector")
    expect(page.get_by_role("heading", name="Overview", exact=True)).to_be_visible()
    for view in (
        "Entities",
        "Relationships",
        "Resources",
        "Needs",
        "Goals",
        "Work",
        "External connections",
        "Stages",
        "History",
        "Overview",
    ):
        page.get_by_role("navigation").get_by_role(
            "button", name=view, exact=True
        ).click()
        expect(page.get_by_role("heading", name=view, exact=True)).to_be_visible()
        expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
    page.get_by_role("button", name="Entities", exact=True).click()
    page.get_by_role("button", name="<img src=x onerror=alert(1)>", exact=True).click()
    expect(page.get_by_role("heading", name="Entity detail")).to_be_visible()
    expect(page.locator("#content img")).to_have_count(0)
    page.get_by_role("button", name="View event evidence_1").click()
    expect(page.locator("[data-event-id='evidence_1']")).to_be_visible()
    page.get_by_label("Filter history").fill("absent")
    expect(page.get_by_text("No records match this filter.")).to_be_visible()
    page.get_by_role("button", name="Entities", exact=True).focus()
    page.keyboard.press("Enter")
    expect(page.locator("#view-title")).to_be_focused()
    page.set_viewport_size({"width": 360, "height": 720})
    expect(page.get_by_role("button", name="Refresh", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.get_by_role("button", name="<img src=x onerror=alert(1)>", exact=True).click()
    page.get_by_role("button", name="Back to Entities").click()
    expect(page.get_by_role("heading", name="Entities", exact=True)).to_be_visible()
    assert methods and set(methods) == {"GET"}
    assert _snapshot_value(engine.state) == before


@pytest.mark.parametrize(
    "status,body,message",
    [
        (200, "[]", "No records reported."),
        (404, "{}", "Snapshot not found."),
        (503, "{}", "Snapshot unavailable. Try Refresh."),
        (200, "not json", "Malformed or unsupported snapshot."),
        (200, '[{"id":"bad"}]', "Malformed or unsupported snapshot."),
        (
            200,
            '[{"id":"bad","definition_key":"thing","name":"bad","attributes":{"resources":{"wood":9007199254740993}},"created_tick":0,"destroyed_tick":null}]',
            "Malformed or unsupported snapshot.",
        ),
    ],
)
def test_distinct_snapshot_states(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    status: int,
    body: str,
    message: str,
) -> None:
    page, _, _ = inspector_page
    page.route(
        "**/world/entities",
        lambda route: route.fulfill(
            status=status, body=body, content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Entities", exact=True).click()
    expect(page.get_by_text(message, exact=True)).to_be_visible()


def test_obsolete_response_cannot_replace_new_view(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, _, _ = inspector_page
    pending: list[Route] = []
    page.route("**/world/entities", lambda route: pending.append(route))
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Entities", exact=True).click()
    expect(page.get_by_text("Loading snapshots…", exact=True)).to_be_visible()
    page.get_by_role("button", name="History", exact=True).click()
    expect(page.locator("[data-event-id='evidence_1']")).to_be_visible()
    assert pending
    pending[0].fulfill(body="[]", content_type="application/json")
    expect(page.get_by_role("heading", name="History", exact=True)).to_be_visible()
    expect(page.locator("[data-event-id='evidence_1']")).to_be_visible()


def test_missing_entity_keeps_back_navigation(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, _, _ = inspector_page
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Entities", exact=True).click()
    page.route(
        "**/world/entities/*",
        lambda route: route.fulfill(
            status=404, body=json.dumps({"detail": "untrusted"})
        ),
    )
    page.get_by_role("button", name="<img src=x onerror=alert(1)>", exact=True).click()
    expect(page.get_by_text("Snapshot not found.", exact=True)).to_be_visible()
    page.get_by_role("button", name="Back to Entities").click()
    expect(page.get_by_role("heading", name="Entities", exact=True)).to_be_visible()


@pytest.mark.parametrize(
    "view,path,payload",
    [
        (
            "Needs",
            "needs",
            [
                {
                    "definition": {
                        "id": "n",
                        "owner_id": "e",
                        "kind": "food",
                        "requirement_per_person": 1,
                        "assessment_window_ticks": 1,
                    },
                    "state": {"need_id": "n", "current": None, "history": []},
                }
            ],
        ),
        (
            "Work",
            "work-orders",
            [
                {
                    "definition": {
                        "id": "w",
                        "category": "gather_water",
                        "public_label": "bad",
                        "target": {},
                        "prerequisite_work_ids": [],
                        "deadline_tick": None,
                        "required_progress": 1,
                    },
                    "state": {
                        "work_id": "w",
                        "status": "proposed",
                        "progress": 0,
                        "status_reason": None,
                    },
                    "reservations": [],
                }
            ],
        ),
    ],
)
def test_rejects_incomplete_nested_core_records(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    view: str,
    path: str,
    payload: list[dict[str, object]],
) -> None:
    page, _, _ = inspector_page
    page.route(
        f"**/world/{path}",
        lambda route: route.fulfill(
            body=json.dumps(payload), content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name=view, exact=True).click()
    expect(
        page.get_by_text("Malformed or unsupported snapshot.", exact=True)
    ).to_be_visible()


def test_populated_domain_snapshots_and_goal_evidence(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    from living_world.core.relationship import Relationship
    from living_world.core.resource_definition import ResourceDefinition
    from living_world.external_world.dispatch import (
        DispatchDirection,
        DispatchStatus,
        ExternalDispatch,
    )
    from living_world.external_world.model import ContactState, ExternalWorldReference
    from living_world.goals import (
        GoalDefinition,
        GoalOwnerKind,
        ObjectiveDefinition,
        ProgressEvidence,
        ResourceMinimumCriterion,
    )
    from living_world.goals.model import GoalState, GoalStatus
    from living_world.needs import NeedDefinition, NeedKind
    from living_world.needs.model import ConsumptionPolicy
    from living_world.stages.model import (
        SettlementStage,
        SettlementStageDefinition,
        SettlementStageProgram,
        SettlementStageState,
    )
    from living_world.work import (
        ResourceWorkTarget,
        WorkCategory,
        WorkDefinition,
        WorkState,
    )

    page, engine, _ = inspector_page
    owner = next(iter(engine.state.entities))
    engine.resource_definitions.register(ResourceDefinition("wood"))
    engine.resource_definitions.register(ResourceDefinition("water"))
    engine.relationships.add(Relationship("relation_z", "guards", owner, owner))
    engine.needs.create(
        NeedDefinition("need_food", owner, NeedKind.FOOD, 1, 0.2, 0.5, 3)
    )
    engine.consequences.create_consumption(
        ConsumptionPolicy("consumption_food", owner, 1, 1)
    )
    objective = ObjectiveDefinition(
        "objective_stock",
        "Stock goal",
        "Exact purpose",
        "Gather materials.",
        (ResourceMinimumCriterion("wood", 2),),
        authorized_action_categories=("gather",),
    )
    engine.goals.create(
        GoalDefinition(
            "goal_stock",
            GoalOwnerKind.NPC,
            owner,
            "Stock goal",
            "Exact purpose",
            "Gather materials.",
            (objective.id,),
            authorized_action_categories=("gather",),
        ),
        (objective,),
    )
    engine.state.goal_states["goal_stock"] = GoalState(
        "goal_stock",
        GoalStatus.ACTIVE,
        (ProgressEvidence(0, "Reported evidence", ("evidence_1",)),),
    )
    work = WorkDefinition(
        "work_water",
        WorkCategory.GATHER_WATER,
        ResourceWorkTarget("water", 2),
        "Fetch reported water",
        owner,
        objective.id,
        owner,
        (),
        0,
        (),
        (),
        3,
        1,
        None,
        0,
    )
    engine.state.work_definitions[work.id] = work
    engine.state.work_states[work.id] = WorkState(work.id)
    reference = ExternalWorldReference(
        "reference_port",
        "Port",
        "trade",
        ("wood",),
        ("water",),
        2,
        3,
        1,
        0.9,
        ContactState.UNKNOWN,
        0,
    )
    engine.state.external_world_references[reference.id] = reference
    dispatch = ExternalDispatch(
        "dispatch_port",
        owner,
        reference.id,
        DispatchDirection.INBOUND,
        "wood",
        1,
        0,
        1,
        DispatchStatus.PENDING,
        0,
    )
    engine.state.external_dispatches[dispatch.id] = dispatch
    engine.state.settlement_stage_programs[owner] = SettlementStageProgram(
        owner, (SettlementStageDefinition(SettlementStage.FOUNDING_CAMP, ()),)
    )
    engine.state.settlement_stage_states[owner] = SettlementStageState(
        owner, SettlementStage.FOUNDING_CAMP, 0
    )
    before = _snapshot_value(engine.state)
    page.goto("http://inspector.test/inspector")
    for view, literal in (
        ("Relationships", "guards"),
        ("Needs", "consumption_food"),
        ("Goals", "Reported evidence"),
        ("Work", "Fetch reported water"),
        ("External connections", "reference_port"),
        ("Stages", "founding_camp"),
    ):
        page.get_by_role("navigation").get_by_role(
            "button", name=view, exact=True
        ).click()
        expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
        assert literal in page.locator("#records").inner_text()
        expect(
            page.get_by_text("Malformed or unsupported snapshot.", exact=True)
        ).to_have_count(0)
    page.get_by_role("button", name="Resources", exact=True).click()
    expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
    quantities = page.locator("article").filter(has_text=owner)
    assert "wood" in quantities.inner_text() and "7" in quantities.inner_text()
    assert "water" not in quantities.inner_text()
    page.get_by_role("button", name="Goals", exact=True).click()
    page.get_by_role("button", name="View event evidence_1").click()
    expect(page.locator("[data-event-id='evidence_1']")).to_be_visible()
    assert _snapshot_value(engine.state) == before


def test_network_failure_and_refresh_recovery(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, _, _ = inspector_page
    page.goto("http://inspector.test/inspector")
    page.route("**/world/entities", lambda route: route.abort())
    page.get_by_role("button", name="Entities", exact=True).click()
    expect(
        page.get_by_text("Snapshot unavailable. Try Refresh.", exact=True)
    ).to_be_visible()
    page.unroute("**/world/entities")
    page.get_by_role("button", name="Refresh", exact=True).click()
    expect(
        page.get_by_role("button", name="<img src=x onerror=alert(1)>", exact=True)
    ).to_be_visible()


def test_overview_reports_exact_run_and_replay_binding(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    from living_world.core.run_metadata import RunMetadata
    from living_world.replay.model import ReplayBinding, ReplayState

    page, engine, _ = inspector_page
    engine.state.run_metadata = RunMetadata(
        "reported_scenario", 1, 42, "reported_config"
    )
    engine.state.replay_binding = ReplayBinding(
        "reported_scenario", "a" * 64, "b" * 64, ("Founding actor",), 0
    )
    engine.state.replay_state = ReplayState(2, 0)
    engine.state.scenario_entity_bindings = {
        "Founding actor": next(iter(engine.state.entities))
    }
    page.goto("http://inspector.test/inspector")
    expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
    text = page.locator("#records").inner_text()
    assert "reported_scenario" in text
    assert "reported_config" in text
    assert "next_index" in text and "2" in text
    assert "b" * 64 in text
    expect(page.get_by_text("Reported tick: 0", exact=True)).to_be_visible()


def test_goal_criterion_requires_reported_shape(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, _, _ = inspector_page
    goal = {
        "definition": {
            "id": "goal_bad",
            "owner_id": "entity",
            "label": "Bad criterion",
            "objective_ids": [],
            "completion_criteria": [{}],
            "failure_criteria": [],
        },
        "state": {"goal_id": "goal_bad", "status": "active", "evidence": []},
        "objectives": [],
    }
    page.route(
        "**/world/goals",
        lambda route: route.fulfill(
            body=json.dumps([goal]), content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Goals", exact=True).click()
    expect(
        page.get_by_text("Malformed or unsupported snapshot.", exact=True)
    ).to_be_visible()


@pytest.mark.parametrize(
    "field,entry,valid",
    [
        ("tools", {}, False),
        ("tools", {"tool": "axe", "quantity": "wrong"}, False),
        ("tools", {"tool": "axe", "quantity": 1.5}, False),
        ("resources", {"resource": "wood", "quantity": "wrong"}, False),
        ("resources", {"quantity": 1}, False),
        (
            "tools",
            {"tool": "axe", "quantity": 2, "annotation": "<literal extra>"},
            True,
        ),
        (
            "resources",
            {"resource": "wood", "quantity": 2, "annotation": "<literal extra>"},
            True,
        ),
    ],
)
def test_reservation_requirements_check_missing_invalid_and_valid_fields(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    field: str,
    entry: dict[str, object],
    valid: bool,
) -> None:
    page, engine, _ = inspector_page
    from living_world.api.inspection import EngineWorldInspector
    from living_world.work import (
        ResourceWorkTarget,
        WorkCategory,
        WorkDefinition,
        WorkState,
    )

    owner = next(iter(engine.state.entities))
    definition = WorkDefinition(
        "work_bad",
        WorkCategory.GATHER_WATER,
        ResourceWorkTarget("water", 2),
        "Reported work",
        owner,
        "objective",
        owner,
        (),
        0,
        (),
        (),
        1,
        1,
        None,
        0,
    )
    engine.state.work_definitions[definition.id] = definition
    engine.state.work_states[definition.id] = WorkState(definition.id)
    record = dict(EngineWorldInspector(engine).work_orders()[0])
    reservation = {
        "id": "reservation_bad",
        "work_id": definition.id,
        "labor_entity_ids": [],
        "tools": [],
        "resources": [],
        "created_tick": 0,
        "released_tick": None,
    }
    reservation[field] = [entry]
    record["reservations"] = [reservation]
    page.route(
        "**/world/work-orders",
        lambda route: route.fulfill(
            body=json.dumps([record]), content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Work", exact=True).click()
    message = "Snapshots loaded." if valid else "Malformed or unsupported snapshot."
    expect(page.get_by_text(message, exact=True)).to_be_visible()
    if valid:
        expect(page.get_by_text("<literal extra>", exact=True)).to_be_visible()


@pytest.mark.parametrize(
    "criterion",
    [
        {"resource": None, "minimum": 2},
        {"capability": "well", "count": 1, "minimum_condition": "wrong"},
        {"role": None, "state": "contacted", "minimum": 2},
    ],
)
def test_known_criterion_variant_cannot_fall_back(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    criterion: dict[str, object],
) -> None:
    page, _, _ = inspector_page
    goal = {
        "definition": {
            "id": "goal_bad",
            "owner_id": "entity",
            "label": "Bad criterion",
            "objective_ids": [],
            "completion_criteria": [criterion],
            "failure_criteria": [],
        },
        "state": {"goal_id": "goal_bad", "status": "active", "evidence": []},
        "objectives": [],
    }
    page.route(
        "**/world/goals",
        lambda route: route.fulfill(
            body=json.dumps([goal]), content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Goals", exact=True).click()
    expect(
        page.get_by_text("Malformed or unsupported snapshot.", exact=True)
    ).to_be_visible()


def test_entity_detail_includes_exact_capability_policy_and_event_references(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    from living_world.needs import MaintenancePolicy, MaintenanceRequirement

    page, engine, _ = inspector_page
    owner = next(iter(engine.state.entities))
    well = engine.entities.create(
        definition_key="thing",
        name="Well",
        attributes={"is_constructed": True, "resources": {}},
    )
    other = engine.entities.create(
        definition_key="thing",
        name="Other Well",
        attributes={"is_constructed": True, "resources": {}},
    )
    engine.relationships.create(kind="owns", source_id=owner, target_id=well.id)
    engine.relationships.create(kind="owns", source_id=owner, target_id=other.id)
    for capability, policy_id in (
        (well, "maintenance_well"),
        (other, "maintenance_other"),
    ):
        engine.consequences.create_maintenance(
            MaintenancePolicy(
                policy_id,
                owner,
                capability.id,
                "Reported well",
                (MaintenanceRequirement("wood", 1),),
                2,
                3,
                1,
                1,
            )
        )
    engine.events.add(
        Event(
            "capability_notice",
            0,
            "capability_reported",
            attributes={"capability_id": well.id},
        )
    )
    before = _snapshot_value(engine.state)
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Entities", exact=True).click()
    page.get_by_role("button", name="Well", exact=True).click()
    expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
    text = page.locator("#records").inner_text()
    assert "maintenance_well" in text
    assert "maintenance_other" not in text
    assert "capability_notice" in text
    assert _snapshot_value(engine.state) == before


def test_narrow_nested_labels_are_readable_and_container_scrolls(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, engine, _ = inspector_page
    next(iter(engine.state.entities.values())).attributes.update(
        {"population": 2, "resources": {"food": 12, "water": 8, "timber": 10}}
    )
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Entities", exact=True).click()
    expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
    for label in ("population", "resources", "food", "water", "timber"):
        heading = page.get_by_role("rowheader", name=label, exact=True)
        line_count = heading.evaluate(
            "element => { const range = document.createRange(); range.selectNodeContents(element); return range.getClientRects().length; }"
        )
        assert line_count == 1, f"{label} wraps into {line_count} lines"
        heading.scroll_into_view_if_needed()
        expect(heading).to_be_in_viewport()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.locator(".table-scroll").evaluate_all(
        "elements => elements.some(element => { if (element.scrollWidth <= element.clientWidth) return false; element.scrollLeft = 80; return element.scrollLeft > 0; })"
    )
    scroller = page.locator(".table-scroll").first
    scroller.evaluate("element => { element.scrollLeft = 0; }")
    scroller.focus()
    expect(scroller).to_be_focused()
    page.keyboard.press("ArrowRight")
    page.wait_for_function("document.querySelector('.table-scroll').scrollLeft > 0")


@pytest.mark.parametrize(
    "criterion",
    [
        {"minimum": 2, "annotation": "<literal extra>"},
        {"resource": "wood", "minimum": 2, "annotation": "<literal extra>"},
        {"capability": "well", "count": 1, "annotation": "<literal extra>"},
        {
            "capability": "well",
            "count": 1,
            "minimum_condition": 2,
            "annotation": "<literal extra>",
        },
    ],
)
def test_valid_criterion_variants_preserve_unrelated_literal_extras(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    criterion: dict[str, object],
) -> None:
    page, _, _ = inspector_page
    goal = {
        "definition": {
            "id": "goal_valid",
            "owner_id": "entity",
            "label": "Reported criterion",
            "objective_ids": [],
            "completion_criteria": [criterion],
            "failure_criteria": [],
        },
        "state": {"goal_id": "goal_valid", "status": "active", "evidence": []},
        "objectives": [],
    }
    page.route(
        "**/world/goals",
        lambda route: route.fulfill(
            body=json.dumps([goal]), content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Goals", exact=True).click()
    expect(page.get_by_text("Snapshots loaded.", exact=True)).to_be_visible()
    expect(page.get_by_text("<literal extra>", exact=True)).to_be_visible()
    expect(page.locator("#records literal")).to_have_count(0)


def _spatial_payload(page: Page, entity_id: str, geometry: object) -> None:
    payload = [
        {
            "entity_id": entity_id,
            "geometry": geometry,
            "containing_entity_id": None,
            "bounds_kind": (
                "area"
                if isinstance(geometry, dict) and geometry.get("kind") == "bounds"
                else None
            ),
            "overlap_policy": "reject",
        }
    ]
    page.route(
        "**/world/placements",
        lambda route: route.fulfill(
            body=json.dumps(payload), content_type="application/json"
        ),
    )


def test_spatial_projection_resize_keyboard_and_return(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    from living_world.api.inspection import EngineWorldInspector
    from living_world.spatial.model import Bounds, BoundsKind, Point

    page, engine, methods = inspector_page
    area = next(iter(engine.state.entities.values()))
    point = engine.entities.create(definition_key="thing", name="North point")
    absent = engine.entities.create(definition_key="thing", name="Missing record")
    engine.spatial.place(
        entity_id=area.id, geometry=Bounds(-10, -5, 20, 15), bounds_kind=BoundsKind.AREA
    )
    engine.spatial.place(
        entity_id=point.id, geometry=Point(3, 4), containing_entity_id=area.id
    )
    before = _snapshot_value(engine.state)
    expected = [p["entity_id"] for p in EngineWorldInspector(engine).placements()]
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    expect(page.get_by_text("Snapshots loaded.", exact=True)).to_be_visible()
    svg = page.locator("#spatial-map")
    expect(svg).to_have_attribute("viewBox", "-12 -12 24 19")
    expect(svg).to_have_attribute("preserveAspectRatio", "xMidYMid meet")
    assert (
        svg.locator("[data-entity-id]").evaluate_all(
            "els => els.map(e => e.dataset.entityId)"
        )
        == expected
    )
    expect(svg.locator("rect")).to_have_attribute("y", "-10")
    expect(svg.locator("circle")).to_have_attribute("cx", "3")
    expect(svg.locator("circle")).to_have_attribute("cy", "-4")
    assert (
        "No placement record"
        in page.locator(f"article[data-entity-id='{absent.id}']").inner_text()
    )
    expect(svg.locator("img")).to_have_count(0)
    expect(svg.locator("text").first).to_have_text(area.name)
    page.set_viewport_size({"width": 390, "height": 844})
    expect(svg).to_have_attribute("viewBox", "-12 -12 24 19")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    mark = svg.locator("[data-entity-id]").first
    mark.focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Back to Spatial")).to_be_visible()
    expect(page.get_by_role("button", name="Spatial", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    page.get_by_role("button", name="Refresh", exact=True).click()
    expect(page.get_by_role("button", name="Back to Spatial")).to_be_visible()
    page.get_by_role("button", name="Back to Spatial").click()
    expect(svg).to_be_visible()
    assert set(methods) == {"GET"}
    assert _snapshot_value(engine.state) == before


@pytest.mark.parametrize(
    "geometry,viewbox,message",
    [
        ({"kind": "point", "x": 0, "y": 0}, "-0.6 -0.6 1.2 1.2", None),
        ({"kind": "point", "x": -4, "y": -3}, "-4.6 2.4 1.2 1.2", None),
        (None, None, "No placed geometry reported."),
        (
            {"kind": "point", "x": 1.5, "y": 0},
            None,
            "Malformed or unsupported snapshot.",
        ),
        (
            {"kind": "point", "x": 9007199254740992, "y": 0},
            None,
            "Unsupported spatial numeric range.",
        ),
        (
            {"kind": "bounds", "x": 9007199254740991, "y": 0, "width": 1, "height": 1},
            None,
            "Unsupported spatial numeric range.",
        ),
        (
            {"kind": "point", "x": 9007199254740991, "y": 0},
            None,
            "Unsupported spatial numeric range.",
        ),
        ({"kind": "road", "x": 0, "y": 0}, None, "Malformed or unsupported snapshot."),
    ],
)
def test_spatial_degenerate_and_invalid_projection(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    geometry: object,
    viewbox: str | None,
    message: str | None,
) -> None:
    page, engine, _ = inspector_page
    _spatial_payload(page, next(iter(engine.state.entities)), geometry)
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    if message:
        expect(page.get_by_text(message, exact=True)).to_be_visible()
        expect(page.locator("#spatial-map")).to_have_count(0)
    else:
        assert viewbox is not None
        expect(page.locator("#spatial-map")).to_have_attribute("viewBox", viewbox)


def test_spatial_overlap_unplaced_order_and_each_record_reachable(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    from living_world.api.inspection import EngineWorldInspector
    from living_world.spatial.model import Bounds, BoundsKind, OverlapPolicy, Point

    page, engine, methods = inspector_page
    area = next(iter(engine.state.entities.values()))
    west = engine.entities.create(definition_key="thing", name="West")
    first = engine.entities.create(definition_key="thing", name="First structure")
    second = engine.entities.create(definition_key="thing", name="Second structure")
    unplaced = engine.entities.create(definition_key="thing", name="Explicit unplaced")
    missing = engine.entities.create(definition_key="thing", name="No record")
    engine.spatial.place(
        entity_id=area.id, geometry=Bounds(-10, -5, 20, 15), bounds_kind=BoundsKind.AREA
    )
    engine.spatial.place(entity_id=west.id, geometry=Point(-20, -10))
    for entity in (first, second):
        engine.spatial.place(
            entity_id=entity.id,
            geometry=Bounds(0, 0, 4, 3),
            containing_entity_id=area.id,
            bounds_kind=BoundsKind.STRUCTURE,
            overlap_policy=OverlapPolicy.ALLOW_SIBLING_OVERLAP,
        )
    engine.spatial.place(entity_id=unplaced.id, geometry=Point(40, 40))
    engine.spatial.unplace(unplaced.id)
    engine.entities.mark_destroyed(second.id, engine.state.tick)
    before = _snapshot_value(engine.state)
    placements = EngineWorldInspector(engine).placements()
    placed_ids = [p["entity_id"] for p in placements if p["geometry"] is not None]
    assert placed_ids != sorted(placed_ids)
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    expect(page.get_by_text("Snapshots loaded.", exact=True)).to_be_visible()
    svg = page.locator("#spatial-map")
    expect(svg).to_have_attribute("viewBox", "-23 -13 36 26")
    assert (
        svg.locator("[data-entity-id]").evaluate_all(
            "els => els.map(e => e.dataset.entityId)"
        )
        == placed_ids
    )
    assert page.locator("article[data-entity-id]").evaluate_all(
        "els => els.map(e => e.dataset.entityId)"
    ) == [*placed_ids, unplaced.id, missing.id]
    explicit = page.locator(f"article[data-entity-id='{unplaced.id}']")
    expect(explicit.get_by_text("Unplaced", exact=True)).to_be_visible()
    expect(
        page.locator(f"article[data-entity-id='{missing.id}']").get_by_text(
            "No placement record", exact=True
        )
    ).to_be_visible()
    assert (
        "allow_sibling_overlap"
        in page.locator(f"article[data-entity-id='{first.id}']").inner_text()
    )
    destroyed = page.locator(f"article[data-entity-id='{second.id}']")
    expect(
        destroyed.get_by_role("rowheader", name="destroyed_tick", exact=True)
    ).to_be_visible()
    assert (
        destroyed.get_by_role("rowheader", name="destroyed_tick", exact=True)
        .locator("..")
        .inner_text()
        .endswith("0")
    )
    page.set_viewport_size({"width": 390, "height": 844})
    # Test actual projected text size, not only the declared SVG font attribute.
    label_height = svg.locator("text").first.evaluate(
        "el => el.getBoundingClientRect().height"
    )
    assert label_height >= 12
    for entity in (area, west, first, second, unplaced, missing):
        page.locator(f"article[data-entity-id='{entity.id}']").get_by_role(
            "button"
        ).click()
        expect(
            page.get_by_role("heading", name="Entity detail", exact=True)
        ).to_be_visible()
        page.get_by_role("button", name="Back to Spatial").click()
        expect(svg).to_be_visible()
    assert set(methods) == {"GET"}
    assert _snapshot_value(engine.state) == before


def test_spatial_entity_missing_refresh_retains_return_target(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, engine, _ = inspector_page
    _spatial_payload(
        page, next(iter(engine.state.entities)), {"kind": "point", "x": 2, "y": 3}
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    page.route(
        "**/world/entities/*", lambda route: route.fulfill(status=404, body="{}")
    )
    page.locator("#spatial-map circle").click()
    expect(page.get_by_text("Snapshot not found.", exact=True)).to_be_visible()
    page.get_by_role("button", name="Refresh", exact=True).click()
    expect(page.get_by_text("Snapshot not found.", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="Spatial", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    page.get_by_role("button", name="Back to Spatial").click()
    expect(page.locator("#spatial-map")).to_be_visible()


@pytest.mark.parametrize(
    "status,body,message",
    [
        (200, "[]", "No placed geometry reported."),
        (404, "{}", "Snapshot not found."),
        (503, "{}", "Snapshot unavailable. Try Refresh."),
        (200, "not json", "Malformed or unsupported snapshot."),
        (200, "[{}]", "Malformed or unsupported snapshot."),
    ],
)
def test_spatial_snapshot_error_states(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    status: int,
    body: str,
    message: str,
) -> None:
    page, _, _ = inspector_page
    page.route(
        "**/world/placements",
        lambda route: route.fulfill(
            status=status, body=body, content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    expect(page.get_by_text(message, exact=True)).to_be_visible()
    expect(page.locator("#spatial-map")).to_have_count(0)


def test_spatial_loading_race_and_refresh_recovery(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    page, _, _ = inspector_page
    pending: list[Route] = []
    page.route("**/world/placements", lambda route: pending.append(route))
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    expect(page.get_by_text("Loading snapshots…", exact=True)).to_be_visible()
    expect(page.locator("#content")).to_have_attribute("aria-busy", "true")
    page.get_by_role("button", name="History", exact=True).click()
    expect(page.locator("[data-event-id='evidence_1']")).to_be_visible()
    assert pending
    pending[0].fulfill(status=503, body="{}")
    expect(page.get_by_role("heading", name="History", exact=True)).to_be_visible()
    expect(page.get_by_text("Snapshots loaded.", exact=True)).to_be_visible()
    page.unroute("**/world/placements")
    page.route("**/world/placements", lambda route: route.abort())
    page.get_by_role("button", name="Spatial", exact=True).click()
    expect(
        page.get_by_text("Snapshot unavailable. Try Refresh.", exact=True)
    ).to_be_visible()
    page.unroute("**/world/placements")
    page.get_by_role("button", name="Refresh", exact=True).click()
    expect(page.get_by_text("No placed geometry reported.", exact=True)).to_be_visible()


@pytest.mark.parametrize(
    "change",
    [
        {"entity_id": "unknown"},
        {"containing_entity_id": "unknown"},
        {"geometry": None, "containing_entity_id": "unknown"},
        {"geometry": None, "bounds_kind": "area"},
        {"geometry": None, "overlap_policy": "allow_sibling_overlap"},
        {"geometry": {"kind": "point", "x": 0}},
        {"geometry": {"kind": "point", "x": True, "y": 0}},
        {"geometry": {"kind": "point", "x": "0", "y": 0}},
        {"bounds_kind": "area"},
        {"overlap_policy": "allow_sibling_overlap"},
        {"overlap_policy": "guess"},
        {"geometry": {"kind": "bounds", "x": 0, "y": 0, "width": 1, "height": 1}},
        {
            "geometry": {"kind": "bounds", "x": 0, "y": 0, "width": 0, "height": 1},
            "bounds_kind": "area",
        },
        {
            "geometry": {"kind": "bounds", "x": 0, "y": 0, "width": 1, "height": -1},
            "bounds_kind": "area",
        },
        {"bounds_kind": "road"},
    ],
)
def test_spatial_rejects_malformed_core_combinations(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    change: dict[str, object],
) -> None:
    page, engine, _ = inspector_page
    record: dict[str, object] = {
        "entity_id": next(iter(engine.state.entities)),
        "geometry": {"kind": "point", "x": 0, "y": 0},
        "containing_entity_id": None,
        "bounds_kind": None,
        "overlap_policy": "reject",
    }
    record.update(change)
    page.route(
        "**/world/placements",
        lambda route: route.fulfill(
            body=json.dumps([record]), content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    expect(
        page.get_by_text("Malformed or unsupported snapshot.", exact=True)
    ).to_be_visible()
    expect(page.locator("#records article, #spatial-map")).to_have_count(0)


@pytest.mark.parametrize(
    "mode", ["duplicate", "extent_x", "extent_y", "center_y", "endpoint_y", "dimension"]
)
def test_spatial_rejects_duplicate_or_unsafe_arithmetic(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    mode: str,
) -> None:
    page, engine, _ = inspector_page
    other = engine.entities.create(definition_key="thing", name="Other")
    owner = next(iter(engine.state.entities))
    records: list[dict[str, object]] = [
        {
            "entity_id": owner,
            "geometry": {"kind": "point", "x": 0, "y": 0},
            "containing_entity_id": None,
            "bounds_kind": None,
            "overlap_policy": "reject",
        }
    ]
    if mode == "duplicate":
        records.append(dict(records[0]))
    elif mode.startswith("extent"):
        axis = mode[-1]
        records[0]["geometry"] = {
            "kind": "point",
            "x": 0,
            "y": 0,
            axis: -9007199254740991,
        }
        records.append(
            {
                **records[0],
                "entity_id": other.id,
                "geometry": {"kind": "point", "x": 0, "y": 0, axis: 9007199254740991},
            }
        )
    elif mode == "center_y":
        records[0]["geometry"] = {"kind": "point", "x": 0, "y": -9007199254740991}
    else:
        records[0].update(
            {
                "geometry": {
                    "kind": "bounds",
                    "x": 0,
                    "y": 9007199254740991 if mode == "endpoint_y" else 0,
                    "width": 9007199254740992 if mode == "dimension" else 1,
                    "height": 1,
                },
                "bounds_kind": "structure",
            }
        )
    page.route(
        "**/world/placements",
        lambda route: route.fulfill(
            body=json.dumps(records), content_type="application/json"
        ),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    message = (
        "Malformed or unsupported snapshot."
        if mode == "duplicate"
        else "Unsupported spatial numeric range."
    )
    expect(page.get_by_text(message, exact=True)).to_be_visible()
    expect(page.locator("#records article, #spatial-map")).to_have_count(0)


def test_spatial_empty_world_and_colocated_points(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
) -> None:
    from living_world.spatial.model import Point

    page, engine, _ = inspector_page
    page.route(
        "**/world/entities",
        lambda route: route.fulfill(body="[]", content_type="application/json"),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    expect(page.get_by_text("No placed geometry reported.", exact=True)).to_be_visible()
    expect(page.locator("#records article, #spatial-map")).to_have_count(0)
    page.unroute("**/world/entities")
    other = engine.entities.create(definition_key="thing", name="Co-located")
    for entity in engine.state.entities.values():
        engine.spatial.place(entity_id=entity.id, geometry=Point(-4, -3))
    page.get_by_role("button", name="Refresh", exact=True).click()
    svg = page.locator("#spatial-map")
    expect(svg).to_have_attribute("viewBox", "-4.6 2.4 1.2 1.2")
    expect(svg.locator("circle")).to_have_count(2)
    for mark in svg.locator("[data-entity-id]").all():
        mark.focus()
        expect(mark).to_be_focused()
    svg.locator(f"[data-entity-id='{other.id}']").press("Space")
    expect(page.get_by_role("button", name="Back to Spatial")).to_be_visible()


@pytest.mark.parametrize(
    "extra_json,valid",
    [
        ('{"nested":[{"quantity":9007199254740993}]}', False),
        ('{"nested":[{"quantity":1e500}]}', False),
        ('{"nested":[{"quantity":7,"annotation":"<literal extra>"}]}', True),
    ],
)
def test_spatial_nested_extra_fields_preserve_numeric_and_literal_safety(
    inspector_page: tuple[Page, SimulationEngine, list[str]],
    extra_json: str,
    valid: bool,
) -> None:
    page, engine, _ = inspector_page
    record = {
        "entity_id": next(iter(engine.state.entities)),
        "geometry": {"kind": "point", "x": 2, "y": 3},
        "containing_entity_id": None,
        "bounds_kind": None,
        "overlap_policy": "reject",
    }
    # Keep the raw numeric JSON token so Chrome, rather than Python, parses it.
    body = "[" + json.dumps(record)[:-1] + ',"extra":' + extra_json + "}]"
    page.route(
        "**/world/placements",
        lambda route: route.fulfill(body=body, content_type="application/json"),
    )
    page.goto("http://inspector.test/inspector")
    page.get_by_role("button", name="Spatial", exact=True).click()
    if valid:
        expect(page.get_by_text("Snapshots loaded.", exact=True)).to_be_visible()
        expect(page.locator("#spatial-map")).to_be_visible()
        expect(page.get_by_text("<literal extra>", exact=True)).to_be_visible()
        expect(page.locator("#records literal")).to_have_count(0)
    else:
        expect(
            page.get_by_text("Malformed or unsupported snapshot.", exact=True)
        ).to_be_visible()
        expect(page.locator("#records article, #spatial-map")).to_have_count(0)


@pytest.mark.parametrize("outcome", ["success", "stall", "failure"])
def test_founders_saved_snapshot_views_are_get_only(
    tmp_path: Path, outcome: str
) -> None:
    from living_world.cli import main
    from living_world.founders import (
        load_inspection_engine,
        materialize_founders_assets,
    )

    executable = os.environ.get(
        "LIVING_WORLD_BROWSER_EXECUTABLE", "/usr/bin/google-chrome"
    )
    if not Path(executable).is_file():
        pytest.skip("Chrome absent; set LIVING_WORLD_BROWSER_EXECUTABLE")
    database = tmp_path / f"{outcome}.sqlite3"
    assert main(["run", "--founders", outcome, "--database", str(database)]) == 0
    before = database.read_bytes()
    with materialize_founders_assets() as assets:
        engine = load_inspection_engine(assets.scenario, database)
    state = _snapshot_value(engine.state)
    app = create_app(engine)
    methods: list[str] = []

    def serve(route: Route) -> None:
        methods.append(route.request.method)
        with ThreadPoolExecutor(max_workers=1) as executor:
            response = executor.submit(
                ASGIClient(app).request,
                route.request.method,
                urlsplit(route.request.url).path,
            ).result()
        route.fulfill(
            status=response.status_code,
            headers=dict(response.headers),
            body=response.body,
        )

    with sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=executable, headless=True)
        page = browser.new_page()
        page.route("**/*", serve)
        page.goto("http://inspector.test/inspector")
        for view in (
            "Needs",
            "Work",
            "Goals",
            "Stages",
            "External connections",
            "History",
            "Spatial",
        ):
            page.get_by_role("navigation").get_by_role(
                "button", name=view, exact=True
            ).click()
            expect(
                page.get_by_role("heading", name=view, level=2, exact=True)
            ).to_be_visible()
            expect(page.get_by_text("Snapshots loaded.", exact=True)).to_be_visible()
            records = page.locator("#records")
            if view == "Needs":
                expect(records).to_contain_text("need_founders_food")
                expect(records).to_contain_text("need_founders_water")
            elif view == "Work" and outcome != "failure":
                expect(records).to_contain_text("gather_water")
                expect(records).to_contain_text("build_shelter")
            elif view == "Goals":
                expect(records).to_contain_text("goal_founding")
                expect(records).to_contain_text(
                    {"success": "completed", "stall": "active", "failure": "failed"}[
                        outcome
                    ]
                )
            elif view == "Stages":
                expect(records).to_contain_text(
                    "settlement" if outcome == "success" else "founding_camp"
                )
            elif view == "External connections" and outcome == "success":
                expect(records).to_contain_text("arrived")
            elif view == "History":
                expect(records).to_contain_text("canonical_setup_completed")
                expect(records).to_contain_text("replay_proposal_resolved")
        camp = engine.state.scenario_entity_bindings["camp"]
        page.locator(f"article[data-entity-id='{camp}']").get_by_role("button").click()
        expect(
            page.get_by_role("heading", name="Entity detail", exact=True)
        ).to_be_visible()
        expect(
            page.get_by_role("button", name="Back to Spatial", exact=True)
        ).to_be_visible()
        browser.close()
    assert methods and set(methods) == {"GET"}
    assert _snapshot_value(engine.state) == state
    assert database.read_bytes() == before
