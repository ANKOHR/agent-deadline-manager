# Agent Deadline Manager

`adm` prioritizes tasks using entered deadlines and an explicit reference timestamp. CPU only, standard-library runtime, local JSON files, no network calls, no models, no predictions.

Hypothesis: deterministic deadline classification and traceable reports can provide trustworthy task prioritization. The synthetic acceptance experiment validates implementation accuracy, not usefulness in real operations.

## Quickstart

Python 3.10 or newer and setuptools are required. In an environment with local packaging tools available:

```powershell
python -m pip install --no-index --disable-pip-version-check --no-deps --no-build-isolation -e .
adm fixtures --out demo
adm run --input demo
adm report --format md
python -m pytest -q
```

On Windows, if pip reports that its Scripts directory is outside PATH, add the exact directory printed by pip to your session PATH before using `adm`. Alternatively use the module invocation below.

No dependencies are downloaded by these commands. pytest is a development prerequisite. An uninstalled fallback is `python -m agent_deadline_manager.cli` followed by the same arguments.

The generated fixture contains 200 tasks. A separate hand-written five-task example is committed at `examples/tiny/tasks.json`:

```powershell
adm run --input examples/tiny
adm report --format json --out tiny-report.json
```

## Input format

An input directory contains UTF-8 JSON documents. Each document has `as_of`, `synthetic`, and `tasks`. An optional `_comment` labels the document. JSON does not allow header comments, so synthetic files carry a leading `_comment` field and `synthetic: true`. Each task must match its document's synthetic flag. Separate documents can mix real and synthetic data in one directory.

```json
{
  "_comment": "Real tasks entered by Henry; example below is illustrative, not shipped trial data",
  "synthetic": false,
  "as_of": "2026-09-30T12:00:00Z",
  "tasks": [
    {"id": "review", "title": "Review agent logs", "deadline": "2026-10-01T12:00:00Z", "status": "open", "importance": 3, "synthetic": false}
  ]
}
```

This README example is hypothetical. Set `synthetic: false` only for your own real, hand-entered tasks. Actual trial results are recorded privately and not shipped.

Required task fields:

| Field | Rule |
| --- | --- |
| id | Unique across all input files, nonblank string, at most 256 characters |
| title | Nonblank Unicode string, at most 100,000 characters |
| deadline | Timezone-aware ISO 8601 timestamp or null |
| status | open, completed, or cancelled |
| importance | Integer 0 to 5 inclusive, never boolean |
| synthetic | Boolean author declaration |

Unknown fields are schema errors. Negative amounts are not meaningful in this schema and an `amount` field is rejected. Future deadlines are valid and classified normally. Duplicate IDs are rejected. Excessive strings and em dash characters in task text are rejected. Unicode and Windows paths in title strings are supported with normal JSON escaping. Null deadlines are explicitly undated, never guessed. Conflicting `as_of` values require `--as-of`; every entered timestamp is still validated. An empty directory uses the documented neutral reference `1970-01-01T00:00:00+00:00` and reports zeros. Supply `--as-of` to choose another reference.

Only JSON is supported. CSV, YAML, JSONL and other input formats produce a named parse error at line 1, rather than being silently ignored. Markdown files and the reserved `expectations.json` are ignored. Use a dedicated directory containing only input documents. Paths and input file names are not used to infer provenance.

## Ranking rules

Deadline differences are exact integer microseconds. Reference time never comes from the wall clock.

| Priority | Classification for open tasks |
| --- | --- |
| overdue | deadline before as_of |
| due_now | deadline exactly at as_of |
| urgent | after as_of, within 24 hours inclusive |
| soon | more than 24 hours, within 72 hours inclusive |
| later | more than 72 hours |
| undated | null deadline |
| completed | status completed, irrespective of deadline |
| cancelled | status cancelled, irrespective of deadline |

Within each category: earliest deadline first, then highest entered importance, then ID in Unicode code point order. Input order does not affect the ranking. This policy is a declared rule, not a prediction of business value. Counts include completed and cancelled tasks. Remaining durations for them are still arithmetic differences, not actionable warnings.

## Subcommands

| Command | Example | Behavior |
| --- | --- | --- |
| fixtures | `adm fixtures --out demo` | Writes labelled synthetic tasks and independent expected counts/IDs |
| run | `adm run --input demo --state .adm/result.json` | Validates, ranks, saves computed results atomically |
| rank | `adm rank --input demo --as-of 2026-09-30T12:00:00Z` | Prints ranked JSON with provenance, does not save state |
| due | `adm due --input demo --within-hours 24` | Prints open overdue and upcoming tasks within the inclusive nonnegative integer horizon |
| report | `adm report --format md --out report.md` | Recomputes saved task inputs and renders Markdown or JSON |

All commands provide `--help` and examples. `run` and `report` default to `.adm/result.json` in the working directory. `due` reports counts and provenance for the selected subset. Report writes use a temporary sibling file and atomic replacement; failures remove the temporary file and preserve an existing target. Fixture generation is not a multi-file transaction and should target a fresh directory.

## Architecture

```text
JSON documents -> cli.load_input -> core.prioritize -> local result JSON
                                             |
                                             +-> report.render -> Markdown / JSON
fixtures.generate -> labelled tasks + independent expectations
```

`core.py` has pure schema validation and arithmetic. `cli.py` owns file I/O, named errors and dispatch. `fixtures.py` defines a hand-classified eight-case pattern repeated 25 times with unique IDs. `report.py` owns provenance and rendering. No randomness is used; there is no seed to configure.

## Honesty boundary

All counts, membership and deadline differences are computed from explicit input. The tool cannot discover deadlines, verify author-declared provenance, predict missed deadlines or estimate effort. Every report states synthetic counts and real-declared counts. A real flag means the author declared it real, not that the tool independently verified Henry entered it. Synthetic accuracy evidence does not establish real-world effectiveness. Time and money savings are not measured and are explicitly not claimed. No savings estimator exists.

The 200-record fixture and the five-record example are synthetic inside their files and every report banner. Their expectations are not loaded by the engine. Altering a deadline changes report figures even if the expectations file stays unchanged. Run duration in `EVIDENCE.md` is locally measured; it is not time saved against a baseline.

## Failure modes

Malformed JSON: `ParseError` includes filename and actual parser line. Unsupported formats and invalid UTF-8 name the file and line 1. Schema validation names the offending field and file with line 1 labelled document validation, not an asserted exact token location. Missing directories or state: `MissingInput` with usage hint. Schema drift and duplicates: `SchemaError`. Failed report writes: `ReportWriteError` with target path and cleanup. Expected failures return exit code 2 without tracebacks. No tasks are silently dropped on validation failure. Run failure preserves previous state; use the exit code before reporting so you do not mistake previous results for a successful new run.

## Evidence and two-week improvement hook

See `EVIDENCE.md` for the synthetic acceptance results and `LESSONS.md` for lessons. One improvement grounded in the tampered-data test is recomputing summaries from saved task inputs during report rendering, preventing stale summary figures from being reported.

For the first real-use trial, record start date and fourteen-day review date in a private trial log. At each actual run, hand-check bucket classification and ranking against entered deadlines. Metric: number of incorrect task classifications or ranking positions divided by number checked. Record numerator, denominator, IDs checked, reference timestamp, corrected input errors, run count and days used. The tool does not automatically collect telemetry. Do not substitute synthetic accuracy for this metric.

After fourteen days, if measured error exceeds 10 percent, fix the largest evidenced failure cause or kill with a recorded reason. If never used, kill. Otherwise choose: expand for daily use or revenue, integrate for heavy sibling overlap, commercialise if a buyer would pay as-is, maintain as portfolio evidence. Record the decision and evidence in `VERDICT.md`. No real-use trial has yet occurred, so the verdict remains explicitly pending rather than inventing a two-week result.
