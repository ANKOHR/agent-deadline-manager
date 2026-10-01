"""Local CLI with atomic result writes and named errors."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import SchemaError, prioritize
from .fixtures import generate
from .report import render, banner

class InputError(ValueError):
    pass

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise InputError(f"ParseError: {path}: line {exc.lineno}: {exc.msg}") from None
    except UnicodeError:
        raise InputError(f"ParseError: {path}: line 1: invalid UTF-8") from None

def load_input(directory, as_of=None):
    directory = Path(directory)
    if not directory.is_dir():
        raise InputError(f"MissingInput: {directory}; use adm fixtures --out demo or supply an input directory")
    tasks, references = [], set()
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.name == "expectations.json" or path.suffix.lower() == ".md":
            continue
        if path.suffix.lower() != ".json":
            raise InputError(f"ParseError: {path}: line 1: unsupported format; use documented JSON input")
        document = read_json(path)
        try:
            if not isinstance(document, dict):
                raise SchemaError("document: expected object")
            allowed = {"_comment", "synthetic", "as_of", "tasks"}
            if document.keys() - allowed:
                raise SchemaError(f"fields: unknown {sorted(document.keys() - allowed)}")
            for field in ("synthetic", "as_of", "tasks"):
                if field not in document:
                    raise SchemaError(f"{field}: missing field")
            if type(document["synthetic"]) is not bool:
                raise SchemaError("synthetic: expected boolean")
            if not isinstance(document["tasks"], list):
                raise SchemaError("tasks: expected array")
            if any(not isinstance(t, dict) or t.get("synthetic") != document["synthetic"] or type(t.get("synthetic")) is not bool for t in document["tasks"]):
                raise SchemaError("synthetic: each task must match document provenance")
            prioritize(document["tasks"], document["as_of"])
            references.add(document["as_of"])
            tasks.extend(document["tasks"])
        except (SchemaError, TypeError) as exc:
            raise InputError(f"SchemaError: {path}: line 1 (document validation): {exc}") from None
    if as_of is None:
        if len(references) > 1:
            raise InputError("SchemaError: as_of: input files disagree; supply --as-of")
        as_of = next(iter(references), "1970-01-01T00:00:00Z")
    try:
        result = prioritize(tasks, as_of)
    except SchemaError as exc:
        raise InputError(f"SchemaError: {directory}: {exc}") from None
    result["inputs"] = sorted(p.name for p in directory.iterdir() if p.is_file() and p.suffix == ".json" and p.name != "expectations.json")
    return result

def atomic_write(path, content):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, path)
    except OSError as exc:
        raise InputError(f"ReportWriteError: {path}: {exc.strerror or str(exc)}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

def parser():
    p = argparse.ArgumentParser(description="Prioritize tasks from explicit deadlines. No predictions or estimated savings.")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fixtures", help="Generate 200 labelled synthetic tasks", epilog="Example: adm fixtures --out demo")
    f.add_argument("--out", required=True)
    for name, help_text in (("run", "Compute and save deadline rankings"), ("rank", "Print all tasks in deadline priority order"), ("due", "Show open tasks due within a supplied horizon, including overdue tasks")):
        c = sub.add_parser(name, help=help_text, description=help_text, epilog=f"Example: adm {name} --input demo")
        c.add_argument("--input", required=True)
        c.add_argument("--as-of", help="Explicit timezone-aware timestamp override")
        c.add_argument("--state", default=".adm/result.json", help="Local computed result file")
        if name == "due":
            c.add_argument("--within-hours", type=int, default=24, help="Nonnegative integer horizon, default 24")
    r = sub.add_parser("report", help="Render saved computed results with provenance", epilog="Example: adm report --format md")
    r.add_argument("--format", choices=("md", "json"), default="md")
    r.add_argument("--state", default=".adm/result.json")
    r.add_argument("--out", help="Atomically write report to a local file")
    return p

def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            generate(args.out)
            print("Generated 200 SYNTHETIC fixture tasks and hand-computed expectations.")
        elif args.command == "report":
            if not Path(args.state).is_file():
                raise InputError(f"MissingInput: {args.state}; run adm run --input <dir> first")
            result = read_json(Path(args.state))
            if not isinstance(result, dict) or not isinstance(result.get("tasks"), list) or "as_of" not in result:
                raise InputError(f"SchemaError: {args.state}: invalid saved result")
            # Recompute to avoid trusting stale or tampered summary figures.
            tasks = [{k: t[k] for k in ("id", "title", "deadline", "status", "importance", "synthetic")} for t in result["tasks"]]
            computed = prioritize(tasks, result["as_of"])
            computed["inputs"] = result.get("inputs", [])
            output = render(computed, args.format)
            if args.out:
                atomic_write(args.out, output)
            else:
                print(output, end="")
        else:
            result = load_input(args.input, args.as_of)
            if args.command == "run":
                atomic_write(args.state, render(result, "json"))
                print(f"Computed {result['total']} tasks. {banner(result)}")
            else:
                if args.command == "due":
                    if args.within_hours < 0:
                        raise InputError("SchemaError: within-hours: must be nonnegative")
                    selected = [t for t in result["tasks"] if t["status"] == "open" and t["remaining_microseconds"] is not None and t["remaining_microseconds"] <= args.within_hours * 3600000000]
                    result = prioritize([{k: t[k] for k in ("id", "title", "deadline", "status", "importance", "synthetic")} for t in selected], result["as_of"])
                print(render(result, "json"), end="")
        return 0
    except (InputError, SchemaError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"InputError: {getattr(args, 'input', getattr(args, 'state', getattr(args, 'out', 'input')))}: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
