"""Pure deadline calculations. No inferred durations or savings."""
from datetime import datetime, timezone

BUCKETS = ("overdue", "due_now", "urgent", "soon", "later", "undated", "completed", "cancelled")

class SchemaError(ValueError):
    """An input field violates the documented schema."""

def timestamp(value, field):
    if not isinstance(value, str):
        raise SchemaError(f"{field}: expected ISO timestamp with timezone")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError()
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise SchemaError(f"{field}: expected valid ISO timestamp with timezone") from None

def validate_task(task):
    if not isinstance(task, dict):
        raise SchemaError("task: expected object")
    required = {"id", "title", "deadline", "status", "importance", "synthetic"}
    missing, extra = required - task.keys(), task.keys() - required
    if missing or extra:
        raise SchemaError(f"fields: missing {sorted(missing)}, unknown {sorted(extra)}")
    for field, limit in (("id", 256), ("title", 100000)):
        if not isinstance(task[field], str) or not task[field].strip() or len(task[field]) > limit:
            raise SchemaError(f"{field}: expected nonempty string up to {limit} characters")
        if chr(0x2014) in task[field]:
            raise SchemaError(f"{field}: em dash is prohibited; use a hyphen")
    if task["status"] not in ("open", "completed", "cancelled"):
        raise SchemaError("status: expected open, completed or cancelled")
    if type(task["importance"]) is not int or not 0 <= task["importance"] <= 5:
        raise SchemaError("importance: expected integer from 0 to 5")
    if type(task["synthetic"]) is not bool:
        raise SchemaError("synthetic: expected boolean declared by input author")
    if task["deadline"] is not None:
        timestamp(task["deadline"], "deadline")

def prioritize(tasks, as_of):
    reference = timestamp(as_of, "as_of")
    seen, ranked = set(), []
    for task in tasks:
        validate_task(task)
        if task["id"] in seen:
            raise SchemaError(f"id: duplicate {task['id']!r}")
        seen.add(task["id"])
        remaining = None
        if task["deadline"] is not None:
            delta = timestamp(task["deadline"], "deadline") - reference
            remaining = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        if task["status"] != "open":
            bucket = task["status"]
        elif remaining is None:
            bucket = "undated"
        elif remaining < 0:
            bucket = "overdue"
        elif remaining == 0:
            bucket = "due_now"
        elif remaining <= 86400 * 1000000:
            bucket = "urgent"
        elif remaining <= 259200 * 1000000:
            bucket = "soon"
        else:
            bucket = "later"
        ranked.append({**task, "bucket": bucket, "remaining_microseconds": remaining})
    ranked.sort(key=lambda t: (BUCKETS.index(t["bucket"]), t["remaining_microseconds"] if t["remaining_microseconds"] is not None else float("inf"), -t["importance"], t["id"]))
    counts = {bucket: sum(t["bucket"] == bucket for t in ranked) for bucket in BUCKETS}
    return {"as_of": reference.isoformat(), "total": len(ranked), "counts": counts,
            "provenance": {"synthetic": sum(t["synthetic"] for t in ranked), "real_declared": sum(not t["synthetic"] for t in ranked)},
            "tasks": ranked, "savings": "Not measured: no time or money savings claimed."}
