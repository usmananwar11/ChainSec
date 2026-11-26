#!/usr/bin/env python3
"""Build cases.jsonl from CoinFabrik scout-soroban test cases (MIT).

Usage: import_scout.py SCOUT_DIR OUT_JSONL

One case per vulnerable/remediated example crate. Each case keeps Cargo.toml and src/**/*.rs with
everything that would leak the answer removed: comments, `#[cfg(test)]` modules and the package name
(which says "vulnerable" or "remediated"). `{ workspace = true }` dependencies are resolved from the
class workspace so each crate stands alone. `soroban-version` is skipped: its cases differ only in
the shared workspace pin.
"""
import json
import os
import re
import subprocess
import sys

SKIP = {"soroban-version"}
QUALITY = {"unsafe-unwrap", "unsafe-expect", "avoid-panic-error", "avoid-unsafe-block", "avoid-core-mem-forget",
           "iterators-over-indexing", "vec-could-be-mapping", "assert-violation"}
TOKENS = re.compile(r'(?<![\w])b?r(#*)".*?"\1|(?<![\w])b?"(?:\\.|[^"\\])*"'
                    r"|(?<![\w])b?'(?:\\(?:u\{[0-9a-fA-F]+\}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'"
                    r'|//[^\n]*|/\*.*?\*/', re.S)
CFG_TEST = re.compile(r'#\[cfg\(test\)\]\s*(?:pub\s+)?mod\s+\w+\s*\{')
WS_DEP = re.compile(r'^(\s*soroban-sdk\s*=\s*\{)\s*workspace\s*=\s*true\s*(,?)', re.M)
LEAK = re.compile(r'(?i)_?(?:vulnerable|remediated)(?:_example)?_?')
SDK_PIN = re.compile(r'soroban-sdk\s*=\s*(?:"([^"]+)"|\{[^}\n]*?version\s*=\s*"([^"]+)")')


def strip_comments(src):
    out = TOKENS.sub(lambda m: m.group(0) if m.group(0)[:2] not in ("//", "/*") else "", src)
    return re.sub(r'[ \t]+\n', '\n', out)


def drop_test_mods(src):
    while True:
        m = CFG_TEST.search(src)
        if not m:
            return src
        depth, i = 0, m.end() - 1
        for i in range(m.end() - 1, len(src)):
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            if depth == 0:
                break
        src = src[:m.start()] + src[i + 1:]


def scrub(text):
    """Remove the words that reveal the expected answer from identifiers and names."""
    return LEAK.sub(lambda m: "_" if m.group(0)[:1] == "_" and m.group(0)[-1:] == "_" else "", text)


def clean_toml(text, pin):
    text = re.sub(r'(?m)^\s*#.*\n', '', text)
    text = re.sub(r'(?m)^name\s*=\s*"[^"]*"', 'name = "case"', text, count=1)
    return WS_DEP.sub(lambda m: f'{m.group(1)} version = "{pin}"{m.group(2)}', text)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    scout, out_path = argv[0], argv[1]
    commit = subprocess.run(["git", "-C", scout, "rev-parse", "HEAD"], capture_output=True,
                            text=True).stdout.strip() or "unknown"
    base = os.path.join(scout, "test-cases")
    rows = []
    for cls in sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))):
        if cls in SKIP:
            continue
        ws = os.path.join(base, cls, "Cargo.toml")
        m = SDK_PIN.search(open(ws, encoding="utf-8").read()) if os.path.isfile(ws) else None
        pin = (m.group(1) or m.group(2)) if m else "=20.0.0"
        for case in sorted(d for d in os.listdir(os.path.join(base, cls)) if d.startswith(cls + "-")):
            for kind, vuln in (("vulnerable-example", True), ("remediated-example", False)):
                crate = os.path.join(base, cls, case, kind)
                if not os.path.isdir(crate):
                    continue
                files = {"Cargo.toml": clean_toml(open(os.path.join(crate, "Cargo.toml"), encoding="utf-8").read(), pin)}
                for dirpath, _, names in os.walk(os.path.join(crate, "src")):
                    for n in sorted(names):
                        if n.endswith(".rs"):
                            p = os.path.join(dirpath, n)
                            src = open(p, encoding="utf-8").read()
                            files[os.path.relpath(p, crate).replace(os.sep, "/")] = scrub(drop_test_mods(strip_comments(src)))
                rows.append({"case_id": f"{case}-{'vuln' if vuln else 'fixed'}", "class_id": cls.upper(),
                             "expected_detect": vuln, "tier": "quality" if cls in QUALITY else "security",
                             "source_url": f"https://github.com/CoinFabrik/scout-soroban/tree/{commit}/test-cases/{cls}/{case}/{kind}",
                             "files": files})
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    print(json.dumps({"cases": len(rows), "classes": len({r["class_id"] for r in rows}), "commit": commit}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
