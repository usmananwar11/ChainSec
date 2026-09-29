#!/usr/bin/env python3
# Usage: slither-summary.py [slither-json] [out.md]  (called during recon when slither is installed; defaults .audit/slither-results.json, .audit/slither-summary.md)
# Reads Slither JSON output, filters to High/Medium, writes markdown summary.
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
from _common import load_json  # noqa: E402


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    input_file = argv[0] if len(argv) > 0 else ".audit/slither-results.json"
    output_file = argv[1] if len(argv) > 1 else ".audit/slither-summary.md"

    if not os.path.isfile(input_file):
        print(f"No Slither results found at {input_file}", file=sys.stderr)
        return 1

    try:
        data = load_json(input_file)
        detectors = data["results"]["detectors"]
        # Check if detectors is a list (empty list is OK, null/false/missing is error)
        if not isinstance(detectors, list):
            raise TypeError("detectors must be a list")
        filtered = [d for d in detectors if d.get("impact") in ("High", "Medium")]
    except (OSError, ValueError, KeyError, TypeError):
        print("Invalid Slither JSON or no detectors found", file=sys.stderr)
        return 1

    lines = [
        "# Slither Pre-Scan Summary",
        f"> Source: {input_file}",
        "> Filtered to: High and Medium severity only",
        "",
        "| # | Detector | Severity | File:Line | Description |",
        "|---|----------|----------|-----------|-------------|",
    ]

    for i, d in enumerate(filtered, start=1):
        elements = d.get("elements") or []
        elem = elements[0] if elements else {}
        # Treat non-dict element as empty
        if not isinstance(elem, dict):
            elem = {}
        source_mapping = elem.get("source_mapping", {})
        # Treat non-dict source_mapping as empty
        if not isinstance(source_mapping, dict):
            source_mapping = {}
        file_ = source_mapping.get("filename_relative") or "unknown"
        elem_lines = source_mapping.get("lines") or []
        line = elem_lines[0] if elem_lines else "?"
        short_desc = (d.get("description") or "").split("\n")[0][:120]
        lines.append(f"| {i} | {d.get('check')} | {d.get('impact')} | {file_}:{line} | {short_desc} |")

    high = sum(1 for d in filtered if d.get("impact") == "High")
    med = sum(1 for d in filtered if d.get("impact") == "Medium")

    lines.append("")
    lines.append(f"**Total**: {len(filtered)} findings ({high} High, {med} Medium)")
    lines.append("")
    lines.append("These findings are ADDITIONAL SIGNAL for ChainSec's detection phase — they are NOT auto-reported.")

    parent = os.path.dirname(output_file)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Slither summary written to {output_file}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
