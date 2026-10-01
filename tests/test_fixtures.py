import json
from agent_deadline_manager.fixtures import generate
from agent_deadline_manager.core import prioritize

def test_fixtures_labelled_synthetic(tmp_path):
    generate(tmp_path)
    for path in tmp_path.iterdir():
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["synthetic"] is True
        assert "SYNTHETIC" in doc["_comment"]
    tasks = json.loads((tmp_path / "tasks.json").read_text())["tasks"]
    assert len(tasks) == 200 and all(t["synthetic"] for t in tasks)

def test_fixture_ground_truth_matches_hand_computed(tmp_path):
    doc, expected = generate(tmp_path)
    result = prioritize(doc["tasks"], doc["as_of"])
    assert result["total"] == expected["total"] == 200
    assert result["counts"] == expected["counts"]
    for bucket, ids in expected["ids_by_bucket"].items():
        assert [t["id"] for t in result["tasks"] if t["bucket"] == bucket] == ids
