#!/usr/bin/env python3
"""Score the Soroban snippet suite. Usage: score_snippets.py MANIFEST OUT

Reads OUT/<project>/.audit/findings.json (final, report-level findings). A case is detected when
any finding has a location under its crate dir; a fixed case with a finding is flagged-clean (an
FP). Totals are reported per tier ("security", "quality") and per class. A project without
findings.json is reported as missing and its cases are not scored.
"""
import json
import os
import sys

KEYS = ("detected", "missed", "flagged_clean", "clean_ok")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    manifest_path, out = argv[0], argv[1]
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    per_class, per_tier, missing = {}, {}, []
    for proj, cases in sorted(manifest.items()):
        path = os.path.join(out, proj, ".audit", "findings.json")
        if not os.path.isfile(path):
            missing.append(proj)
            continue
        files = [loc.get("file") or "" for f in json.load(open(path, encoding="utf-8"))
                 for loc in (f.get("locations") or []) if isinstance(loc, dict)]
        for c in cases:
            flagged = any(f.startswith(c["dir"]) for f in files)
            key = ("detected" if flagged else "missed") if c["expected_detect"] else \
                  ("flagged_clean" if flagged else "clean_ok")
            for table, name in ((per_class, c["class_id"]), (per_tier, c["tier"])):
                table.setdefault(name, dict.fromkeys(KEYS, 0))[key] += 1
    total = {k: sum(r[k] for r in per_class.values()) for k in KEYS}
    print(json.dumps({"total": total, "per_tier": per_tier, "per_class": per_class,
                      "missing_projects": missing}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
