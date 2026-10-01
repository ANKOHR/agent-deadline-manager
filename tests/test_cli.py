import json
import time
from pathlib import Path
import pytest
from agent_deadline_manager.cli import main, load_input, atomic_write, InputError
from agent_deadline_manager.fixtures import generate

def test_run_completes_on_fixture(tmp_path, capsys):
    generate(tmp_path / "input")
    start = time.perf_counter()
    assert main(["run", "--input", str(tmp_path / "input"), "--state", str(tmp_path / "result.json")]) == 0
    assert main(["report", "--state", str(tmp_path / "result.json")]) == 0
    assert time.perf_counter() - start < 5
    assert "200 synthetic" in capsys.readouterr().out

def test_empty_input_renders_without_traceback(tmp_path, capsys):
    state = tmp_path / "result.json"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert main(["run", "--input", str(empty), "--state", str(state)]) == 0
    assert main(["report", "--state", str(state)]) == 0
    assert "Total tasks: 0" in capsys.readouterr().out

@pytest.mark.parametrize("suffix,content,line", [("json", '{\n"bad": }', 2), ("csv", "broken,csv", 1), ("yaml", "broken: [", 1)])
def test_malformed_input_named_error(tmp_path, capsys, suffix, content, line):
    path = tmp_path / f"bad.{suffix}"
    path.write_text(content)
    assert main(["run", "--input", str(tmp_path)]) == 2
    err = capsys.readouterr().err
    assert "ParseError" in err and str(path) in err and f"line {line}" in err
    assert "Traceback" not in err

def test_determinism_byte_identical(tmp_path):
    generate(tmp_path / "input")
    state = tmp_path / "state.json"
    args = ["run", "--input", str(tmp_path / "input"), "--state", str(state)]
    assert main(args) == 0
    first = state.read_bytes()
    assert main(args) == 0
    assert state.read_bytes() == first
    for fmt in ("md", "json"):
        out = tmp_path / f"report.{fmt}"
        command = ["report", "--state", str(state), "--format", fmt, "--out", str(out)]
        assert main(command) == 0
        first = out.read_bytes()
        assert main(command) == 0
        assert out.read_bytes() == first

def test_cli_smoke_all_subcommands(tmp_path, capsys):
    source, state = tmp_path / "input", tmp_path / "state.json"
    assert main(["fixtures", "--out", str(source)]) == 0
    for cmd in ("run", "rank", "due"):
        assert main([cmd, "--input", str(source), "--state", str(state)]) == 0
    assert main(["report", "--state", str(state), "--format", "json"]) == 0
    for cmd in ("fixtures", "run", "rank", "due", "report"):
        with pytest.raises(SystemExit) as exc:
            main([cmd, "--help"])
        assert exc.value.code == 0
    assert chr(0x2014) not in capsys.readouterr().out

def test_missing_input(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err

def test_report_write_failure_no_partial_files(tmp_path, capsys):
    generate(tmp_path / "input")
    state = tmp_path / "state.json"
    main(["run", "--input", str(tmp_path / "input"), "--state", str(state)])
    blocked = tmp_path / "blocked"
    blocked.write_text("keep")
    assert main(["report", "--state", str(state), "--out", str(blocked / "report.md")]) == 2
    assert "ReportWriteError" in capsys.readouterr().err
    assert blocked.read_text() == "keep"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["blocked", "input", "state.json"]

def test_due_horizon_and_provenance(tmp_path, capsys):
    generate(tmp_path)
    assert main(["due", "--input", str(tmp_path), "--within-hours", "0"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["total"] == 50 and value["provenance"]["synthetic"] == 50
    assert main(["due", "--input", str(tmp_path), "--within-hours", "-1"]) == 2

def test_schema_drift_names_field(tmp_path, capsys):
    generate(tmp_path)
    path = tmp_path / "tasks.json"
    doc = json.loads(path.read_text())
    doc["tasks"][0]["amount"] = -1
    path.write_text(json.dumps(doc))
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "amount" in capsys.readouterr().err

def test_real_and_synthetic_provenance(tmp_path):
    doc, _ = generate(tmp_path)
    real = dict(doc, synthetic=False, tasks=[dict(doc["tasks"][0], id="real", synthetic=False)])
    (tmp_path / "real.json").write_text(json.dumps(real))
    result = load_input(tmp_path)
    assert result["provenance"] == {"synthetic": 200, "real_declared": 1}


def test_tampered_summary_recomputed(tmp_path, capsys):
    generate(tmp_path / "input")
    state = tmp_path / "state.json"
    assert main(["run", "--input", str(tmp_path / "input"), "--state", str(state)]) == 0
    capsys.readouterr()
    doc = json.loads(state.read_text())
    doc["total"] = 999
    doc["counts"]["overdue"] = 999
    state.write_text(json.dumps(doc))
    assert main(["report", "--state", str(state), "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["total"] == 200 and report["counts"]["overdue"] == 25


def test_hand_written_tiny_example():
    result = load_input(Path(__file__).resolve().parents[1] / "examples" / "tiny")
    assert result["total"] == 5
    assert [t["id"] for t in result["tasks"]] == ["audit", "review", "renew", "backup", "research"]
