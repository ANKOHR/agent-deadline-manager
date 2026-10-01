"""Reports with explicit, author-declared provenance."""
import json

def banner(result):
    p = result["provenance"]
    return (f"Data provenance: {p['synthetic']} synthetic fixture tasks; "
            f"{p['real_declared']} tasks declared real by the input author (Henry's own data only if entered by him). "
            "Provenance is declared, not independently verified.")

def render(result, format="md"):
    if format == "json":
        return json.dumps({"banner": banner(result), **result}, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if format != "md":
        raise ValueError("format: expected md or json")
    lines = ["# Agent Deadline Manager", "", banner(result), "", f"As of: {result['as_of']}", f"Total tasks: {result['total']}", "", result["savings"], "", "| Category | Count |", "| --- | ---: |"]
    lines.extend(f"| {b} | {n} |" for b, n in result["counts"].items())
    lines.extend(["", "## Ranked tasks", "", "Each remaining duration is deadline minus as_of, in exact microseconds.", ""])
    for task in result["tasks"]:
        # JSON escaping preserves Unicode and prevents markdown input from becoming markup.
        label = json.dumps({"id": task["id"], "title": task["title"]}, ensure_ascii=False)
        label = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("`", "&#96;")
        lines.append(f"- {task['bucket']}: `{label}`; remaining_microseconds={task['remaining_microseconds']}; synthetic={str(task['synthetic']).lower()}")
    return "\n".join(lines) + "\n"
