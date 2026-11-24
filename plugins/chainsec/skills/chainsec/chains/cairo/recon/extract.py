#!/usr/bin/env python3
"""Cairo (Starknet) facts extractor for ChainSec.

Usage:
  extract.py --root DIR --pack PACK_JSON --out FACTS_JSON [--compile ok|failed|unknown]

Parses comment- and string-stripped Cairo 1+ source (mode "regex"); `--compile` records the
result of the optional `scarb build` run by extract.sh. Exit 3 on Cairo 0 source.
Output conforms to engine/facts.schema.json, plus a top-level "compile" field.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
from _common import load_json, scope_files, write_json  # noqa: E402

SYSCALLS = ("call_contract_syscall", "library_call_syscall", "replace_class_syscall",
            "deploy_syscall", "send_message_to_l1_syscall", "storage_write_syscall")
TOKEN_CALLS = ("transfer_from", "transferFrom", "transfer")
UNIT_ATTR = {"contract": "contract", "component": "component", "interface": "interface"}

_STRIP = re.compile(r'//[^\n]*|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'')
CAIRO0 = re.compile(r'^\s*%lang\b|^\s*@(?:external|view|storage_var|l1_handler)\b|^\s*func\s+\w+\s*\{',
                    re.M)
UNIT_RE = re.compile(r'#\[starknet::(contract|component|interface)\]\s*(?:#\[[^\]]*\]\s*)*'
                     r'(?:pub(?:\([^)]*\))?\s+)?(mod|trait)\s+([A-Za-z_]\w*)[^{;]*\{')
COMPONENT_RE = re.compile(r'\bcomponent!\s*\(\s*path\s*:\s*([\w:]+)')
IMPL_RE = re.compile(r'((?:#\[[^\]]*\]\s*)*)(?:pub\s+)?impl\s+([A-Za-z_]\w*)\b[^{;=]*\{')
FN_RE = re.compile(r'((?:#\[[^\]]*\]\s*)*)(?:pub(?:\([^)]*\))?\s+)?fn\s+([A-Za-z_]\w*)\s*(?:<[^>{]*>)?\s*\(')
WRITE_RE = re.compile(r'\bself\.([A-Za-z_]\w*)(?:\.[A-Za-z_]\w*(?:\([^()]*\))?)*\.write\s*\(')
DISPATCH_RE = re.compile(r'\b([A-Za-z_]\w*Dispatcher)\s*\{')
TOKEN_RE = re.compile(r'\.(' + "|".join(TOKEN_CALLS) + r')\s*\(')
SYSCALL_RE = re.compile(r'\b(' + "|".join(SYSCALLS) + r')\b')
ASSERT_ONLY_RE = re.compile(r'\.(assert_only_\w+|only_owner|only_role)\s*\(')
CALLER_CHECK_RE = re.compile(r'get_caller_address\s*\(\s*\)\s*[!=]=|[!=]=\s*get_caller_address\s*\(\s*\)')
FROM_CHECK_RE = re.compile(r'\bfrom_address\b\s*[!=]=|[!=]=\s*from_address\b')
FELT_ARITH_RE = re.compile(r'felt252[^;\n]*[^-=<>!]\s[-+*/]\s')


def strip(src):
    """Blank comments and string literals, keeping offsets and newlines."""
    return _STRIP.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), src)


def block_end(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def attrs_of(attr_text):
    return re.findall(r'#\[([^\]]*)\]', attr_text or "")


def functions(text, start, end):
    """Yield (name, attrs, sig_start, body_start, body_end) for fns in text[start:end]."""
    pos = start
    while True:
        m = FN_RE.search(text, pos, end)
        if not m:
            return
        brace = text.find("{", m.end(), end)
        semi = text.find(";", m.end(), end)
        if brace == -1 or (semi != -1 and semi < brace):
            pos = m.end()
            continue
        close = block_end(text, brace)
        yield m.group(2), attrs_of(m.group(1)), m.start(2), brace, close
        pos = close + 1


def impl_blocks(text, start, end):
    """Return [(attrs, open, close)] for impl blocks directly inside a module body."""
    out = []
    pos = start
    while True:
        m = IMPL_RE.search(text, pos, end)
        if not m:
            return out
        brace = m.end() - 1
        close = block_end(text, brace)
        out.append((attrs_of(m.group(1)), brace, close))
        pos = close + 1


def analyze_body(text, b0, b1):
    body = text[b0:b1]
    return {
        "writes": [(m.group(1), b0 + m.start()) for m in WRITE_RE.finditer(body)],
        "syscalls": [(m.group(1), b0 + m.start()) for m in SYSCALL_RE.finditer(body)],
        "dispatch": [(m.group(1), b0 + m.start()) for m in DISPATCH_RE.finditer(body)],
        "tokens": [(m.group(1), b0 + m.start()) for m in TOKEN_RE.finditer(body)],
        "assert_only": [(m.group(1), b0 + m.start()) for m in ASSERT_ONLY_RE.finditer(body)],
        "caller": [b0 + m.start() for m in CALLER_CHECK_RE.finditer(body)],
        "from": [b0 + m.start() for m in FROM_CHECK_RE.finditer(body)],
    }


def extract_file(rel, src, facts):
    text = strip(src)
    counters = {"loc": src.count("\n"), "external_calls": 0, "state_writers": 0, "syscalls": 0,
                "l1_handlers": 0, "felt_arith": len(FELT_ARITH_RE.findall(text))}
    for um in UNIT_RE.finditer(text):
        kind, name = UNIT_ATTR[um.group(1)], um.group(3)
        u0 = um.end() - 1
        u1 = block_end(text, u0)
        parents = [p.split("::")[-1] for p in COMPONENT_RE.findall(text, u0, u1)]
        facts["units"].append({"name": name, "kind": kind, "file": rel, "line": line_of(text, um.start(3)),
                               "loc": text.count("\n", u0, u1) + 1, "parents": parents})
        if kind == "interface":
            continue
        impls = impl_blocks(text, u0 + 1, u1)

        def impl_for(pos):
            for attrs, i0, i1 in impls:
                if i0 < pos < i1:
                    return attrs
            return None

        for fname, fattrs, fpos, b0, b1 in functions(text, u0 + 1, u1):
            iattrs = impl_for(fpos)
            sig = text[fpos:b0]
            vis = None
            if "constructor" in fattrs:
                vis = "constructor"
            elif "l1_handler" in fattrs:
                vis = "l1_handler"
            elif any(a.startswith("external") for a in fattrs):
                vis = "external"
            elif iattrs is not None and any(a.startswith("abi(embed_v0)") or a.startswith("embeddable_as")
                                            for a in iattrs):
                vis = "external"
            info = analyze_body(text, b0, b1)
            guards = [g for g, _ in info["assert_only"]]
            guards += ["caller-check"] * bool(info["caller"]) + ["from_address-check"] * bool(info["from"])
            for target, p in info["writes"]:
                facts["storage_writes"].append({"unit": name, "function": fname, "file": rel,
                                                "line": line_of(text, p), "target": target})
            for kindc, p in info["syscalls"] + [("dispatcher", p) for _, p in info["dispatch"]]:
                facts["external_calls"].append({"unit": name, "function": fname, "file": rel,
                                                "line": line_of(text, p), "kind": kindc})
                counters["external_calls"] += 1
            counters["syscalls"] += len(info["syscalls"])
            for _, p in info["tokens"]:
                facts["value_transfers"].append({"unit": name, "function": fname, "file": rel,
                                                 "line": line_of(text, p), "asset": "token"})
            for g, p in info["assert_only"]:
                facts["auth_sites"].append({"unit": name, "file": rel, "line": line_of(text, p),
                                            "kind": "assert_only"})
            for p in info["caller"]:
                facts["auth_sites"].append({"unit": name, "file": rel, "line": line_of(text, p),
                                            "kind": "caller-check"})
            for p in info["from"]:
                facts["auth_sites"].append({"unit": name, "file": rel, "line": line_of(text, p),
                                            "kind": "from_address-check"})
            if vis is None:
                continue
            view = re.search(r'\bself\s*:\s*@', sig) is not None
            facts["entry_points"].append({"unit": name, "name": fname, "file": rel,
                                          "line": line_of(text, fpos), "visibility": vis,
                                          "mutability": "view" if view else "external",
                                          "guards": guards})
            if vis == "l1_handler":
                counters["l1_handlers"] += 1
            if info["writes"] and not view:
                counters["state_writers"] += 1
    facts["counters"][rel] = counters


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract Cairo facts")
    ap.add_argument("--root", required=True)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--compile", default="unknown", choices=("ok", "failed", "unknown"))
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    pack = load_json(args.pack)
    facts = {"chain": "cairo", "mode": "regex", "root": root, "compile": args.compile, "units": [],
             "entry_points": [], "auth_sites": [], "storage_writes": [], "external_calls": [],
             "value_transfers": [], "counters": {}}
    for rel in scope_files(root, pack["scope"]):
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            src = f.read()
        if CAIRO0.search(strip(src)):
            print(f"{rel}: Cairo 0 source is not supported (Cairo 1+ only)", file=sys.stderr)
            return 3
        extract_file(rel, src, facts)
    write_json(args.out, facts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
