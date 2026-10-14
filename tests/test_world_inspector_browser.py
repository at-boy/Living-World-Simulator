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
