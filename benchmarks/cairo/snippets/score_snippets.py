#!/usr/bin/env python3
"""Score the Cairo snippet suite. Usage: score_snippets.py MANIFEST OUT

Reads OUT/<project>/.audit/findings.json (final, report-level findings). A case is detected when
any finding has a location in its file; a clean case with a finding is flagged-clean (an FP).
A project without findings.json is reported as missing and its cases are not scored.
"""
import json
import os
import sys


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    manifest_path, out = argv[0], argv[1]
    manifest = json.load(open(manifest_path, encoding="utf-8"))
    per_class, missing = {}, []
    for proj, cases in sorted(manifest.items()):
        path = os.path.join(out, proj, ".audit", "findings.json")
        if not os.path.isfile(path):
            missing.append(proj)
            continue
        hit = {loc.get("file") for f in json.load(open(path, encoding="utf-8"))
               for loc in (f.get("locations") or []) if isinstance(loc, dict)}
        for c in cases:
            row = per_class.setdefault(c["class_id"], {"detected": 0, "missed": 0, "flagged_clean": 0, "clean_ok": 0})
            flagged = c["file"] in hit
            if c["expected_detect"]:
                row["detected" if flagged else "missed"] += 1
            else:
                row["flagged_clean" if flagged else "clean_ok"] += 1
    total = {k: sum(r[k] for r in per_class.values()) for k in ("detected", "missed", "flagged_clean", "clean_ok")}
    print(json.dumps({"total": total, "per_class": per_class, "missing_projects": missing}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
