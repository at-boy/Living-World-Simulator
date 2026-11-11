"""Acceptance adapter exercises the ordinary archive owner and HTTP broker."""

import importlib.util
import json
import multiprocessing
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from uuid import uuid4

import pytest
from test_runtime_cli import provider

from living_world.archives import RunCatalog
from living_world.cli import build_parser

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(EXAMPLES))


def modules():
    path = EXAMPLES / "manual" / "local_founders_runtime.py"
    assert path.is_file(), "the bounded archived experiment helper is missing"
    from manual import local_founders_runtime

    spec = importlib.util.spec_from_file_location(
        "acceptance_demo", EXAMPLES / "040_live_npc_runtime.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return local_founders_runtime, module


def test_real_archived_steps_and_offline_replay(tmp_path):
    helper, demo = modules()
    with demo.synthetic_ollama_provider() as url:
        arguments = build_parser().parse_args(demo.fresh_options(tmp_path, url))
        result = helper.run_experiment(arguments, steps=3, timeout_seconds=20)
    assert result.exit_code == 0
    assert (result.start_tick, result.end_tick, result.steps_completed) == (0, 3, 3)
    replay = helper.run_experiment(
        build_parser().parse_args(
            [
                "run",
                "--replay-attempt",
                result.attempt_id,
                "--archive-root",
                str(tmp_path),
            ]
        ),
        steps=3,
        timeout_seconds=20,
    )
    assert replay.exit_code == 0
    assert replay.end_tick == 3


def fixture_options(demo, root, url):
    options = demo.fresh_options(root, url)
    options[options.index("--model") + 1] = "tiny"
    return options


@pytest.mark.parametrize(
    "overrides",
    [
        {"steps": True},
        {"steps": 0},
        {"steps": 21},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": True},
        {"timeout_seconds": 0.01},
        {"stop_requested": None},
        {"disturbance": "bad"},
    ],
)
def test_invalid_helper_inputs_create_nothing(tmp_path, overrides):
    helper, demo = modules()
    root = tmp_path / "absent"
    result = helper.run_experiment(
        build_parser().parse_args(demo.fresh_options(root, "http://127.0.0.1:1")),
        **overrides,
    )
    assert (result.exit_code, result.error_code, result.attempt_id) == (
        2,
        "invalid_configuration",
        None,
    )
    assert not root.exists()


@pytest.mark.parametrize(
    "options",
    [
        ["run", "--founders", "success"],
        ["run", "scenario.yaml"],
        ["analyze"],
    ],
)
def test_non_archived_routes_create_nothing(tmp_path, options):
    helper, _ = modules()
    root = tmp_path / "absent"
    result = helper.run_experiment(
        build_parser().parse_args([*options, "--archive-root", str(root)])
    )
    assert result.exit_code == 2
    assert not root.exists()


@pytest.mark.parametrize("block", ["GET", "POST"])
@pytest.mark.parametrize("cancel", [False, True])
def test_stop_during_startup_or_inference_closes_owned_threads(tmp_path, block, cancel):
    helper, demo = modules()
    baseline = {t.ident for t in threading.enumerate()}
    children = {p.pid for p in multiprocessing.active_children()}
    with provider(block=block) as (url, _, entered):
        result = helper.run_experiment(
            build_parser().parse_args(fixture_options(demo, tmp_path, url)),
            timeout_seconds=20 if cancel else (4 if block == "POST" else 0.3),
            stop_requested=(lambda: entered.is_set()) if cancel else (lambda: False),
        )
    if block == "POST":
        assert entered.is_set(), "the inference request must actually be in flight"
    assert result.exit_code == (130 if cancel else 124)
    assert result.error_code == ("cancelled" if cancel else "experiment_deadline")
    assert result.attempt_id is not None
    assert result.steps_completed == 0
    assert {p.pid for p in multiprocessing.active_children()} <= children
    assert not [
        t for t in threading.enumerate() if t.ident not in baseline and not t.daemon
    ]


def test_callback_failure_is_closed_and_preserves_identity(tmp_path):
    helper, demo = modules()

    def broken():
        raise RuntimeError("sensitive callback text")

    with provider(block="GET") as (url, _, _):
        result = helper.run_experiment(
            build_parser().parse_args(fixture_options(demo, tmp_path, url)),
            stop_requested=broken,
        )
    assert (result.exit_code, result.error_code) == (5, "service_failed")
    assert result.attempt_id is not None
    assert "sensitive" not in str(result)


def test_failed_provider_retains_error_and_attempt(tmp_path):
    helper, demo = modules()
    with provider(fail=True) as (url, _, _):
        result = helper.run_experiment(
            build_parser().parse_args(fixture_options(demo, tmp_path, url))
        )
    assert result.exit_code == 6
    assert result.steps_completed == 0
    assert result.error_code == "http_error"
    assert result.start_tick == result.end_tick == 0
    assert RunCatalog(tmp_path).attempts()[0].ref.attempt_id == result.attempt_id


def test_missing_source_retains_uninitialized_failure(tmp_path):
    helper, _ = modules()
    result = helper.run_experiment(
        build_parser().parse_args(
            [
                "run",
                "--resume-attempt",
                uuid4().hex,
                "--archive-root",
                str(tmp_path),
            ]
        )
    )
    assert result.exit_code == 4 and result.error_code == "archive_failed"
    assert result.attempt_id is not None
    assert result.start_tick is None and result.end_tick is None
    assert RunCatalog(tmp_path).attempts()[0].last_revision is None


def test_request_budget_stop_is_not_a_completed_step(tmp_path):
    helper, demo = modules()
    with demo.synthetic_ollama_provider() as url:
        options = demo.fresh_options(tmp_path, url)
        options[options.index("--max-requests") + 1] = "1"
        result = helper.run_experiment(
            build_parser().parse_args(options), steps=3, timeout_seconds=20
        )
    assert (
        result.exit_code,
        result.state,
        result.steps_completed,
        result.end_tick,
    ) == (0, "stopped", 0, 0)


@pytest.mark.parametrize(
    "policy,outcome",
    [("resource_loss", "applied"), ("work_blockage", "no_eligible_work")],
)
def test_cold_children_inherit_exact_checkpoint_and_policy_without_repeating_tick2(
    tmp_path, policy, outcome
):
    helper, demo = modules()
    catalog = RunCatalog(tmp_path)
    with demo.synthetic_ollama_provider() as url:
        source_result = helper.run_experiment(
            build_parser().parse_args(demo.fresh_options(tmp_path, url)),
            disturbance=policy,
            steps=2,
            timeout_seconds=20,
        )
        assert source_result.exit_code == 0
        with catalog.open_attempt(source_result.attempt_id) as source:
            checkpoint = source.checkpoint()
            config = source.config
            directory = source.ref.directory
            rows = [e for e in source.entries() if e.kind == "boundary_disturbance"]
            assert len(rows) == 1 and rows[0].payload["outcome"] == outcome
        before = demo.source_files(directory)
        for mode in ("resume", "fork"):
            child_result = helper.run_experiment(
                build_parser().parse_args(
                    [
                        "run",
                        f"--{mode}-attempt",
                        source_result.attempt_id,
                        "--archive-root",
                        str(tmp_path),
                    ]
                ),
                steps=1,
                timeout_seconds=20,
            )
            assert (
                child_result.exit_code,
                child_result.start_tick,
                child_result.end_tick,
                child_result.steps_completed,
            ) == (0, 2, 3, 1)
            with catalog.open_attempt(child_result.attempt_id) as child:
                assert child.config == config
                initial = child.checkpoint(0)
                assert initial.snapshot == checkpoint.snapshot
                assert initial.driver_cursor == checkpoint.driver_cursor
                assert initial.feedback_cursor == checkpoint.feedback_cursor
                assert not [
                    e for e in child.entries() if e.kind == "boundary_disturbance"
                ]
        assert demo.source_files(directory) == before


def test_numbered_example_is_import_inert_and_runs_in_subprocess(tmp_path):
    before = {t.ident for t in threading.enumerate()}
    modules()
    assert {t.ident for t in threading.enumerate()} == before
    env = {**os.environ, "PYTHONPATH": "src", "TMPDIR": str(tmp_path)}
    process = subprocess.run(
        [sys.executable, str(EXAMPLES / "040_live_npc_runtime.py")],
        env=env,
        capture_output=True,
        text=True,
        timeout=35,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout.startswith("PASS: synthetic HTTP broker")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize("block", ["GET", "POST"])
def test_manual_subprocess_signals_are_cooperative_and_sanitized(tmp_path, sig, block):
    _, demo = modules()
    with provider(block=block) as (url, _, entered):
        options = fixture_options(demo, tmp_path, url)[1:]
        process = subprocess.Popen(
            [
                sys.executable,
                str(EXAMPLES / "manual" / "local_founders_runtime.py"),
                "--timeout-seconds",
                "20",
                "--",
                *options,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONPATH": "src"},
        )
        try:
            assert entered.wait(12)
            process.send_signal(sig)
            stdout, stderr = process.communicate(timeout=12)
            result = json.loads(stdout)
            assert process.returncode == result["exit_code"] == 130
            assert result["error_code"] == "cancelled" and result["attempt_id"]
            assert result["steps_completed"] == 0
            assert stderr.count("attempt=") == 1
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)


def test_main_separator_and_malformed_options_never_create_catalog(tmp_path, capsys):
    helper, _ = modules()
    for options in (
        ["--steps", "1"],
        ["--"],
        ["--", "--preset", "founders", "--archive-root", str(tmp_path / "absent")],
    ):
        assert helper.main(options) == 2
        result = json.loads(capsys.readouterr().out)
        assert result["format"] == "living-world-native-experiment-v1"
        assert result["error_code"] == "invalid_configuration"
    assert not (tmp_path / "absent").exists()


def test_known_preflight_failure_and_first_failure_survive_cleanup(
    tmp_path, monkeypatch
):
    helper, demo = modules()
    real_prepare = helper.prepare_archived_launch

    def prepare(*args, **kwargs):
        prepared = real_prepare(*args, **kwargs)
        shutdown = prepared.service.shutdown

        def failed_cleanup(*args, **kwargs):
            shutdown(*args, **kwargs)
            raise RuntimeError("private cleanup diagnostic")

        monkeypatch.setattr(prepared.service, "shutdown", failed_cleanup)
        return prepared

    monkeypatch.setattr(helper, "prepare_archived_launch", prepare)
    with demo.synthetic_ollama_provider() as url:
        options = demo.fresh_options(tmp_path, url)
        options[options.index("--model") + 1] = "missing"
        result = helper.run_experiment(build_parser().parse_args(options))
    assert (result.exit_code, result.error_code) == (6, "model_missing")
    assert result.attempt_id is not None
    assert result.start_tick is None and result.end_tick is None
    assert "private" not in str(result)


def test_cleanup_failure_after_success_is_reported(tmp_path, monkeypatch):
    helper, demo = modules()
    real_prepare = helper.prepare_archived_launch

    def prepare(*args, **kwargs):
        prepared = real_prepare(*args, **kwargs)
        shutdown = prepared.service.shutdown

        def failed_cleanup(*args, **kwargs):
            shutdown(*args, **kwargs)
            raise RuntimeError("private cleanup diagnostic")

        monkeypatch.setattr(prepared.service, "shutdown", failed_cleanup)
        return prepared

    monkeypatch.setattr(helper, "prepare_archived_launch", prepare)
    with demo.synthetic_ollama_provider() as url:
        result = helper.run_experiment(
            build_parser().parse_args(demo.fresh_options(tmp_path, url)),
            steps=1,
            timeout_seconds=20,
        )
    assert (result.exit_code, result.error_code) == (5, "service_failed")
    assert result.steps_completed == 1


def test_failed_initial_mirror_preserves_durable_checkpoint_summary(tmp_path):
    helper, demo = modules()
    mirror = tmp_path / "mirror-directory"
    mirror.mkdir()
    with demo.synthetic_ollama_provider() as url:
        result = helper.run_experiment(
            build_parser().parse_args(
                [*demo.fresh_options(tmp_path / "runs", url), "--database", str(mirror)]
            ),
            timeout_seconds=20,
        )
    assert result.exit_code == 4 and result.error_code == "mirror_failed"
    assert result.attempt_id is not None
    assert (
        result.start_tick,
        result.end_tick,
        result.start_revision,
        result.end_revision,
    ) == (0, 0, 0, 0)
    assert result.steps_completed == 0


@pytest.mark.parametrize(
    "timeout", [10**1000, -(10**1000)], ids=["huge_positive", "huge_negative"]
)
def test_oversized_integer_timeout_is_invalid_without_allocation(tmp_path, timeout):
    helper, demo = modules()
    root = tmp_path / "absent"
    result = helper.run_experiment(
        build_parser().parse_args(demo.fresh_options(root, "http://127.0.0.1:1")),
        timeout_seconds=timeout,
    )
    assert (result.exit_code, result.error_code, result.attempt_id) == (
        2,
        "invalid_configuration",
        None,
    )
    assert not root.exists()


@pytest.mark.parametrize("help_flag", ["--help", "-h"])
@pytest.mark.parametrize("separator", [False, True])
def test_mixed_helper_help_exits_success_without_summary_or_allocation(
    tmp_path,
    capsys,
    help_flag,
    separator,
):
    helper, _ = modules()
    root = tmp_path / "absent"
    options = ["--steps", "1", help_flag]
    if separator:
        options.extend(["--", "--preset", "founders", "--archive-root", str(root)])
    assert helper.main(options) == 0
    captured = capsys.readouterr()
    assert "--disturbance" in captured.out
    assert "living-world-native-experiment-v1" not in captured.out
    assert not captured.err
    assert not root.exists()


@pytest.mark.parametrize("help_flag", ["--help", "-h"])
def test_help_after_separator_uses_production_run_parser(tmp_path, capsys, help_flag):
    helper, _ = modules()
    root = tmp_path / "absent"
    assert (
        helper.main(
            [
                "--steps",
                "1",
                "--",
                "--archive-root",
                str(root),
                help_flag,
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert "usage: living-world run" in captured.out
    assert "--disturbance" not in captured.out
    assert "living-world-native-experiment-v1" not in captured.out
    assert not captured.err
    assert not root.exists()


def test_malformed_helper_arguments_remain_invalid_with_help(tmp_path, capsys):
    helper, _ = modules()
    root = tmp_path / "absent"
    assert (
        helper.main(
            [
                "--steps",
                "invalid",
                "--help",
                "--",
                "--archive-root",
                str(root),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["error_code"] == "invalid_configuration"
    assert not root.exists()
