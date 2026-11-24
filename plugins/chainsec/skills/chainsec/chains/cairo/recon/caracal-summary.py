#!/usr/bin/env python3
# Usage: caracal-summary.py [caracal-output] [out.md]
# Called during recon when caracal is installed. The input is Caracal's text output, either raw
# or wrapped as JSON {"output": "<text>"} (see heuristics.md "Recon additions"). Caracal reports
# are text, so this keeps the detector blocks verbatim (capped) rather than re-parsing them.
import json
import os
import sys

MAX_LINES = 300


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    src = argv[0] if argv else ".audit/cairo/analyzers/caracal.json"
    out = argv[1] if len(argv) > 1 else ".audit/cairo/analyzers/caracal.md"
    if not os.path.isfile(src):
        print(f"No Caracal results found at {src}", file=sys.stderr)
        return 1
    with open(src, encoding="utf-8", errors="replace") as f:
        text = f.read()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("output"), str):
            text = data["output"]
    except json.JSONDecodeError:
        pass
    lines = [l.rstrip() for l in text.splitlines() if l.strip()]
    flagged = sum(1 for l in lines if l.lower().startswith("impact:") and
                  any(s in l.lower() for s in ("high", "medium")))
    body = lines[:MAX_LINES]
    md = ["# Caracal summary", "",
          f"High/Medium impact blocks: {flagged}. Signal only: every item still needs a ChainSec "
          "trace and the kill gates.", ""]
    if not lines:
        md.append("Caracal reported nothing.")
    else:
        md += ["```", *body, "```"]
        if len(lines) > MAX_LINES:
            md.append(f"(truncated: {len(lines) - MAX_LINES} more lines in {src})")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
