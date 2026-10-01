import pytest
from agent_deadline_manager.core import prioritize, SchemaError
from agent_deadline_manager.fixtures import AS_OF

def task(**changes):
    value = dict(id="a", title="Task", deadline=AS_OF, status="open", importance=3, synthetic=False)
    return {**value, **changes}

@pytest.mark.parametrize("changes", [{"importance": -1}, {"importance": True}, {"importance": 6}, {"deadline": "bad"}, {"deadline": "2026-01-01"}, {"status": "unknown"}, {"synthetic": "true"}, {"title": ""}, {"id": "x" * 257}, {"title": "x" * 100001}, {"amount": -1}])
def test_rejects_adversarial_values(changes):
    with pytest.raises(SchemaError):
        prioritize([task(**changes)], AS_OF)

def test_duplicate_ids():
    with pytest.raises(SchemaError, match="duplicate"):
        prioritize([task(), task()], AS_OF)

def test_handles_unicode_and_long_inputs():
    title = "代理 café 🕒 C:\\Users\\henry " + "a" * 50000
    assert prioritize([task(title=title)], AS_OF)["tasks"][0]["title"] == title

def test_future_dates_are_valid():
    assert prioritize([task(deadline="2099-01-01T00:00:00Z")], AS_OF)["counts"]["later"] == 1

@pytest.mark.parametrize("deadline,bucket", [("2026-09-30T11:59:59.999999Z", "overdue"), (AS_OF, "due_now"), ("2026-10-01T12:00:00.000001Z", "soon"), ("2026-10-03T12:00:00.000001Z", "later")])
def test_boundaries(deadline, bucket):
    assert prioritize([task(deadline=deadline)], AS_OF)["counts"][bucket] == 1

def test_tie_breaks_and_timezone():
    tasks = [task(id="b", importance=1), task(id="a", importance=5, deadline="2026-09-30T13:00:00+01:00")]
    assert [t["id"] for t in prioritize(tasks, AS_OF)["tasks"]] == ["a", "b"]
