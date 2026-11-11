"""Actual offline CLI ZIP output and cooperative owned-process cancellation."""

import signal
import subprocess
import sys
import time

import pytest
from test_trace_analysis_reader import create, fail, snapshot, start

from living_world.cli import main


def args(root, archive, output):
    return [
        "export-traces",
        "--archive-root",
        str(root),
        "--attempt-id",
        archive.ref.attempt_id,
        "--output",
        str(output),
    ]


def test_actual_cli_and_runtime_bypass(tmp_path, monkeypatch, capsys):
    from living_world import cli
    from living_world.archives import RunCatalog

    root = tmp_path / "runs"
    archive = create(root)
    start(archive)
    fail(archive, b"\x00\xff")
    before = snapshot(root)

    def forbidden(*a, **kw):
        raise AssertionError("runtime reached")

    monkeypatch.setattr(cli, "validate_archived_options", forbidden)
    monkeypatch.setattr(RunCatalog, "attempts", forbidden)
    output = tmp_path / "one.zip"
    assert main(args(root, archive, output), engine_factory=forbidden) == 0
    assert capsys.readouterr().out == "trace_export=complete calls=1 bodies=2\n"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "living_world.cli",
            *args(root, archive, tmp_path / "two.zip"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=8,
    )
    assert result.returncode == 0 and not result.stderr
    assert output.read_bytes() == (tmp_path / "two.zip").read_bytes()
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "extra,code,error",
    [
        (["--max-calls", "0"], 2, "export_invalid"),
        (["--max-output-bytes", "1024"], 4, "export_limit_exceeded"),
        (["--attempt-id", "invalid"], 2, "export_invalid"),
    ],
)
def test_closed_errors(tmp_path, capsys, extra, code, error):
    archive = create(tmp_path / "runs")
    start(archive)
    assert main([*args(tmp_path / "runs", archive, tmp_path / "out"), *extra]) == code
    assert capsys.readouterr().err == f"error: {error}\n"


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_actual_signal_cancels_before_publication(tmp_path, signum):
    root = tmp_path / "runs"
    archive = create(root)
    start(archive)
    ready = tmp_path / "ready"
    # Hold at the real reader seam after CLI signal handlers are installed.
    script = """import time,sys
from pathlib import Path
from living_world import cli
from living_world.archives import trace_export
original = trace_export.read_trace_page
def held(*args, **kwargs):
    Path(sys.argv[1]).write_text('ready')
    time.sleep(0.5)
    return original(*args, **kwargs)
trace_export.read_trace_page = held
raise SystemExit(cli.main(sys.argv[2:]))
"""
    output = tmp_path / "out.zip"
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(ready), *args(root, archive, output)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 8
        while (
            not ready.exists()
            and process.poll() is None
            and time.monotonic() < deadline
        ):
            time.sleep(0.01)
        assert ready.exists()
        process.send_signal(signum)
        stdout, stderr = process.communicate(timeout=8)
        assert process.returncode == 130
        assert stdout == "" and stderr == "error: export_cancelled\n"
        assert not output.exists() and not list(tmp_path.glob(".trace-export-*"))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(3)
        process.stdout.close()
        process.stderr.close()


def test_catalog_construction_error_closed(tmp_path, capsys):
    root = tmp_path / "PRIVATE-root"
    root.symlink_to(tmp_path / "missing")
    assert (
        main(
            [
                "export-traces",
                "--archive-root",
                str(root),
                "--attempt-id",
                "invalid",
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 4
    )
    assert capsys.readouterr().err == "error: trace_unavailable\n"


@pytest.mark.parametrize(
    "extra",
    [
        ["--model", "PRIVATE"],
        ["--admin-token-file", "PRIVATE"],
        ["--scenario", "PRIVATE"],
    ],
)
def test_runtime_flags_unsupported(tmp_path, extra):
    archive = create(tmp_path / "runs")
    assert main([*args(tmp_path / "runs", archive, tmp_path / "out"), *extra]) == 2
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "case",
    [
        "calls",
        "bytes",
        "unknown",
        "leading_unknown",
        "missing_required",
        "missing_value",
    ],
)
def test_export_parse_errors_are_closed(tmp_path, capsys, case):
    sentinel = "PRIVATE_PARSE_MARKER"
    arguments = [
        "export-traces",
        "--attempt-id",
        sentinel,
        "--output",
        str(tmp_path / sentinel),
    ]
    if case == "calls":
        arguments += ["--max-calls", sentinel]
    elif case == "bytes":
        arguments += ["--max-output-bytes", sentinel]
    elif case == "unknown":
        arguments += ["--unknown", sentinel]
    elif case == "leading_unknown":
        arguments = ["--unknown", *arguments]
    elif case == "missing_required":
        arguments = ["export-traces", "--attempt-id", sentinel]
    else:
        arguments += ["--max-calls"]
    assert main(arguments) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "error: export_invalid\n"
    assert sentinel not in captured.out + captured.err
    assert list(tmp_path.iterdir()) == []


def test_export_help_and_legacy_diagnostics_preserved(capsys):
    with pytest.raises(SystemExit) as error:
        main(["export-traces", "--help"])
    assert error.value.code == 0
    assert "--max-calls" in capsys.readouterr().out
    # A legacy option value equal to the command name is not export dispatch.
    with pytest.raises(SystemExit) as error:
        main(["run", "--model", "export-traces", "--max-ticks", "PRIVATE_PARSE_MARKER"])
    assert error.value.code == 2
    assert "PRIVATE_PARSE_MARKER" in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--max-calls", "--max-output-bytes", "--unknown"])
def test_actual_cli_parse_redaction(tmp_path, option):
    sentinel = "PRIVATE_PARSE_MARKER"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "living_world.cli",
            "export-traces",
            "--attempt-id",
            sentinel,
            "--output",
            str(tmp_path / sentinel),
            option,
            sentinel,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=8,
    )
    assert result.returncode == 2
    assert result.stdout == "" and result.stderr == "error: export_invalid\n"
    assert list(tmp_path.iterdir()) == []
