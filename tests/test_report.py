import json
from agent_deadline_manager.fixtures import fixture_documents
from agent_deadline_manager.core import prioritize
from agent_deadline_manager.report import render

def result():
    doc, expected = fixture_documents()
    return prioritize(doc["tasks"], doc["as_of"]), expected

def test_report_matches_ground_truth_exact():
    value, expected = result()
    report = json.loads(render(value, "json"))
    assert report["counts"] == expected["counts"]
    assert report["total"] == expected["total"]
    assert sum(report["counts"].values()) == report["total"]
    md = render(value)
    for bucket, count in expected["counts"].items():
        assert f"| {bucket} | {count} |" in md

def test_report_zero_false_positives():
    value, expected = result()
    report = json.loads(render(value, "json"))
    for bucket, ids in expected["ids_by_bucket"].items():
        assert set(ids) == {t["id"] for t in report["tasks"] if t["bucket"] == bucket}

def test_report_carries_provenance_banner():
    value, _ = result()
    for fmt in ("md", "json"):
        assert "200 synthetic fixture tasks" in render(value, fmt)
        assert "0 tasks declared real" in render(value, fmt)

def test_hypothetical_figures_labelled():
    value, _ = result()
    for fmt in ("md", "json"):
        assert "Not measured: no time or money savings claimed." in render(value, fmt)

def test_no_em_dashes_in_outputs():
    value, _ = result()
    for fmt in ("md", "json"):
        assert chr(0x2014) not in render(value, fmt)

def test_corrupted_fixture_changes_computed_report():
    doc, expected = fixture_documents()
    doc["tasks"][0]["deadline"] = "2099-01-01T00:00:00Z"
    value = json.loads(render(prioritize(doc["tasks"], doc["as_of"]), "json"))
    assert value["counts"]["overdue"] == 24
    assert value["counts"]["later"] == 26
    assert value["counts"] != expected["counts"]
