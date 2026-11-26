#!/usr/bin/env python3
# Usage: scout-summary.py [scout-output] [out.md]
# Called during recon when cargo-scout-audit is installed. The input is Scout's SARIF 2.1.0 output
# (exact command: heuristics.md "Recon additions"). Rows are capped; the full file stays on disk.
import json
import os
import sys

MAX_ROWS = 200


def results(data):
    for run in data.get("runs") or []:
        for r in run.get("results") or []:
            phys = ((r.get("locations") or [{}])[0] or {}).get("physicalLocation") or {}
            uri = (phys.get("artifactLocation") or {}).get("uri", "?")
            line = (phys.get("region") or {}).get("startLine", "?")
            text = ((r.get("message") or {}).get("text") or "").strip().splitlines()
            msg = (text[0] if text else "").replace("|", "\\|")
            yield r.get("ruleId") or "?", r.get("level") or "warning", f"{uri}:{line}", msg


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    src = argv[0] if argv else ".audit/soroban/analyzers/scout.json"
    out = argv[1] if len(argv) > 1 else ".audit/soroban/analyzers/scout.md"
    if not os.path.isfile(src):
        print(f"No Scout results found at {src}", file=sys.stderr)
        return 1
    try:
        with open(src, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Scout output at {src} is not SARIF JSON: {e}", file=sys.stderr)
        return 1
    rows = sorted(set(results(data)))
    rules = sorted({r[0] for r in rows})
    md = ["# Scout summary", "",
          f"Results: {len(rows)} from {len(rules)} detectors. Signal only: every item still needs a "
          "ChainSec trace and the kill gates. A detector ID upper-cased is its `patterns/` class.", ""]
    if not rows:
        md.append("Scout reported nothing.")
    else:
        md += ["| Detector | Level | Location | Message |", "|---|---|---|---|"]
        md += [f"| {r} | {lvl} | {loc} | {msg} |" for r, lvl, loc, msg in rows[:MAX_ROWS]]
        if len(rows) > MAX_ROWS:
            md.append(f"\n(truncated: {len(rows) - MAX_ROWS} more results in {src})")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
