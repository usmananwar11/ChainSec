#!/usr/bin/env python3
# Usage: scout-summary.py [scout-output] [out.md]
# Called during recon when cargo-scout-audit is installed. The input is Scout's SARIF 2.1.0 output
# written by recon/run-scout.sh (heuristics.md "Recon additions"). Each result's ruleId is mapped to the
# pack's pattern ID and tier (patterns/README.md): security-tier rows come first and are the
# High/Medium signal; quality-tier rows are QA and capped separately. The full file stays on disk.
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATTERNS_README = os.path.join(HERE, "..", "patterns", "README.md")
TIER_ORDER = ("security", "unknown", "quality")
MAX_ROWS = {"security": 200, "unknown": 200, "quality": 50}
# Scout lint names that differ from the detector (pattern) name at the pinned scout-soroban commit.
ALIASES = {"UNEXPECTED-REVERT-WARN": "DOS-UNEXPECTED-REVERT-WITH-VECTOR",
           "INTEGER-OVERFLOW-UNDERFLOW": "INTEGER-OVERFLOW-OR-UNDERFLOW",
           "ITERATOR-OVER-INDEXING": "ITERATORS-OVER-INDEXING"}
ROW_RE = re.compile(r'^\|\s*\[([A-Z0-9-]+)\]\([^)]*\)\s*\|(.*)$')


def load_tiers(path=PATTERNS_README):
    """Pattern ID -> tier, from the `| [ID](ID.md) | ... | Tier | ... |` rows of patterns/README.md."""
    tiers = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                m = ROW_RE.match(line.strip())
                if not m:
                    continue
                cells = [c.strip() for c in m.group(2).split("|")]
                tier = next((c for c in cells if c in ("security", "quality")), None)
                if tier:
                    tiers.setdefault(m.group(1), tier)
    except OSError:
        pass
    return tiers


def pattern_id(rule):
    """`scout::unsafe_unwrap`, `UNSAFE_UNWRAP` and `unsafe-unwrap` all map to UNSAFE-UNWRAP."""
    pid = re.split(r'::|/', rule)[-1].strip().replace("_", "-").upper()
    return ALIASES.get(pid, pid)


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
    tiers = load_tiers()
    rows = []
    for rule, lvl, loc, msg in set(results(data)):
        pid = pattern_id(rule)
        rows.append((pid, tiers.get(pid, "unknown"), rule, lvl, loc, msg))
    rows.sort(key=lambda r: (TIER_ORDER.index(r[1]), r[0], r[4], r[2], r[3], r[5]))
    by_tier = {t: [r for r in rows if r[1] == t] for t in TIER_ORDER}
    md = ["# Scout summary", "",
          f"Results: {len(rows)} from {len({r[2] for r in rows})} detectors "
          f"({', '.join(f'{len(by_tier[t])} {t}' for t in TIER_ORDER)}). Signal only: every item still "
          "needs a ChainSec trace and the kill gates. Pattern is the `patterns/` class; security-tier "
          "classes are the High/Medium signal, quality-tier classes are QA/Low, unknown IDs are not in "
          "`patterns/README.md` (read the detector before ranking).", ""]
    if not rows:
        md.append("Scout reported nothing.")
    else:
        md += ["| Pattern | Tier | Detector | Level | Location | Message |", "|---|---|---|---|---|---|"]
        notes = []
        for t in TIER_ORDER:
            md += [f"| {p} | {tier} | {r} | {lvl} | {loc} | {msg} |"
                   for p, tier, r, lvl, loc, msg in by_tier[t][:MAX_ROWS[t]]]
            if len(by_tier[t]) > MAX_ROWS[t]:
                notes.append(f"(truncated: {len(by_tier[t]) - MAX_ROWS[t]} more {t}-tier results in {src})")
        if notes:
            md += [""] + notes
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
