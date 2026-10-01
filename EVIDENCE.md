# Build evidence

Measured locally on 2026-10-01, Windows, Python 3.12.10, CPU only.

- pytest: 41 passed in 0.42 seconds.
- Installed adm end-to-end: fixtures, run, report --format md completed in 0.609177 seconds, including three process launches and captured full report rendering. All exited 0 without tracebacks. Acceptance limit: under 5 seconds.
- A separate measured run writing Markdown to disk completed in 0.670080 seconds.
- Input: 200 labelled synthetic tasks. Expected counts: 25 each in overdue, due_now, urgent, soon, later, undated, completed and cancelled. Observed counts matched exactly, total 200.
- Tests compare each category's exact ID set to independent expectations: zero false positives and zero missing planted cases. Repeated state and report writes are byte-identical.
- Altered input experiment: moving one overdue task to 2099 gives overdue 24 and later 26 without altering the expectation file. Figures are computed from tasks.
- Saved-summary corruption experiment: total and overdue count of 999 still render computed total 200 and overdue 25. This motivated report-time recomputation.
- Five-task hand-written synthetic input yields audit, review, renew, backup, research ordering.

Captured full synthetic report: evidence/synthetic-report.md. These are synthetic experiments, not real-use accuracy or time savings. No baseline savings measurement or two-week trial exists. Verdict pending, see VERDICT.md.
