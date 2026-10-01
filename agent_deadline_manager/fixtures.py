"""Labelled synthetic fixtures with independently enumerated ground truth."""
import json
from pathlib import Path
from .core import BUCKETS

AS_OF = "2026-09-30T12:00:00Z"
# Each of 25 groups has these eight hand-classified cases. No randomness or seed.
CASES = (
    ("2026-09-29T12:00:00Z", "open", "overdue"),
    (AS_OF, "open", "due_now"),
    ("2026-10-01T12:00:00Z", "open", "urgent"),
    ("2026-10-03T12:00:00Z", "open", "soon"),
    ("2026-10-04T12:00:00Z", "open", "later"),
    (None, "open", "undated"),
    ("2026-09-29T12:00:00Z", "completed", "completed"),
    (AS_OF, "cancelled", "cancelled"),
)

def fixture_documents():
    tasks = []
    ids = {bucket: [] for bucket in BUCKETS}
    for group in range(25):
        for case, (deadline, status, bucket) in enumerate(CASES):
            ident = f"task-{group:02d}-{case}"
            tasks.append(dict(id=ident, title=f"Synthetic agent task {group}/{case}", deadline=deadline, status=status, importance=3, synthetic=True))
            ids[bucket].append(ident)
    return ({"_comment": "SYNTHETIC fixture, not Henry's real data", "synthetic": True, "as_of": AS_OF, "tasks": tasks},
            {"_comment": "SYNTHETIC hand-computed expectations: 25 groups times eight cases", "synthetic": True, "total": 200, "counts": {b: 25 for b in BUCKETS}, "ids_by_bucket": ids})

def generate(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    documents = fixture_documents()
    for name, document in zip(("tasks.json", "expectations.json"), documents):
        (out / name).write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return documents
