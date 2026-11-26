#!/usr/bin/env python3
"""Soroban (Stellar) facts extractor for ChainSec.

Usage:
  extract.py --root DIR --pack PACK_JSON --out FACTS_JSON [--compile ok|failed|unknown]

Parses comment- and string-stripped Rust source of soroban-sdk contracts (mode "regex");
`--compile` records the result of the optional `cargo check` run by extract.sh.
Output conforms to engine/facts.schema.json, plus top-level "compile" and "sdk" fields.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "scripts")))
from _common import load_json, scope_files, write_json  # noqa: E402

TOKEN_CALLS = ("transfer_from", "transfer", "burn_from", "burn", "mint", "clawback")
AUTH_MACROS = ("only_owner", "only_admin", "only_role", "only_any_role", "has_role", "has_any_role")

_STRIP = re.compile(
    r'//[^\n]*|/\*.*?\*/'
    r'|(?<![\w])b?r(#*)".*?"\1'
    r'|(?<![\w])b?"(?:\\.|[^"\\])*"'
    r"|(?<![\w])b?'(?:\\(?:u\{[0-9a-fA-F]+\}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'", re.S)
ATTR = r'#\[[^\]]*\]'
VIS = r'(?:pub(?:\([^)]*\))?\s+)?'
CFG_RE = re.compile(r'#\[cfg\(([^\]]*)\)\]\s*(?:' + ATTR + r'\s*)*' + VIS + r'mod\s+\w+\s*\{')
CONTRACT_RE = re.compile(r'#\[(?:soroban_sdk::)?contract\]\s*(?:' + ATTR + r'\s*)*' + VIS + r'struct\s+([A-Za-z_]\w*)')
IMPL_RE = re.compile(r'#\[(?:soroban_sdk::)?contractimpl(?:\s*\(([^\]]*)\))?\]\s*(?:' + ATTR + r'\s*)*'
                     r'impl(?:\s*<[^>{]*>)?\s+(?:([A-Za-z_][\w:]*)(?:<[^>{]*>)?\s+for\s+)?'
                     r'([A-Za-z_]\w*)[^{;]*\{')
IFACE_RE = re.compile(r'#\[(?:soroban_sdk::)?(?:contractclient|contracttrait)\b[^\]]*\]\s*(?:' + ATTR + r'\s*)*' + VIS +
                      r'trait\s+([A-Za-z_]\w*)[^{;]*\{')
FN_RE = re.compile(r'((?:' + ATTR + r'\s*)*)(pub(?:\([^)]*\))?\s+)?(?:(?:const|unsafe|async|extern)\s+)*'
                   r'fn\s+([A-Za-z_]\w*)\s*(?:<[^>{]*>)?\s*\(')
WRITE_RE = re.compile(r'\.storage\(\)\s*\.\s*(instance|persistent|temporary)\(\)\s*\.\s*'
                      r'(set|remove|update|try_update)\s*(?:::\s*<[^>]*>)?\s*\(\s*&?\s*(?:mut\s+)?([\w:]+)')
HANDLE_RE = re.compile(r'\blet\s+(?:mut\s+)?([A-Za-z_]\w*)\s*(?::[^=;]+)?=\s*[^;]*?\.storage\(\)\s*\.\s*'
                       r'(instance|persistent|temporary)\(\)\s*;')
CLIENT_RE = re.compile(r'\b(?:[A-Za-z_]\w*::)*[A-Za-z_]*Client\s*::\s*new\s*\(')
EXT_RE = re.compile(r'\.(try_invoke_contract|invoke_contract)\b|\.(deployer)\s*\(\s*\)'
                    r'(?!\s*\.\s*update_current_contract_wasm)|\b(update_current_contract_wasm)\s*\(')
TOKEN_RE = re.compile(r'\.(' + "|".join(TOKEN_CALLS) + r')\s*\(')
AUTH_RE = re.compile(r'([A-Za-z_][\w.]*)(\s*\([^()]*\))?\s*\.\s*(require_auth_for_args|require_auth)\s*\(')
AS_CONTRACT_RE = re.compile(r'\.authorize_as_current_contract\s*\(')
UNCHECKED_RE = re.compile(r'\.(?:wrapping|overflowing|unchecked)_\w+\s*\(|\bas\s+[iu](?:8|16|32|64|128)\b')
CALL_RE = re.compile(r'(?<![\w.:])(?:[A-Za-z_]\w*::)*([a-z_]\w*)\s*\(')
SDK_LOCK_RE = re.compile(r'name\s*=\s*"soroban-sdk"\s*\nversion\s*=\s*"([^"]+)"')
SDK_TOML_RE = re.compile(r'soroban-sdk\s*=\s*(?:"([^"]+)"|\{[^}\n]*?version\s*=\s*"([^"]+)")')


def strip(src):
    """Blank comments, strings and char literals, keeping offsets and newlines."""
    return _STRIP.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), src)


def paren_end(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return open_idx


def blank(text, a, b):
    return text[:a] + re.sub(r'[^\n]', ' ', text[a:b + 1]) + text[b + 1:]


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


def blank_test_mods(text):
    """Blank `#[cfg(test)] mod x { ... }` (and cfg(any(test, ..))) blocks; keep cfg(not(test))."""
    while True:
        m = next((m for m in CFG_RE.finditer(text)
                  if re.search(r'\btest\b', m.group(1)) and "not(" not in m.group(1)), None)
        if not m:
            return text
        text = blank(text, m.start(), block_end(text, m.end() - 1))


def line_of(text, idx):
    return text.count("\n", 0, idx) + 1


def attrs_of(attr_text):
    return [a.strip() for a in re.findall(r'#\[([^\]]*)\]', attr_text or "")]


def functions(text, start, end):
    """Yield (name, attrs, is_pub, name_pos, body_open, body_close) for fns with bodies."""
    pos = start
    while True:
        m = FN_RE.search(text, pos, end)
        if not m:
            return
        params_end = paren_end(text, m.end() - 1)
        brace = text.find("{", params_end, end)
        semi = text.find(";", params_end, end)
        if brace == -1 or (semi != -1 and semi < brace):
            pos = m.end()
            continue
        close = block_end(text, brace)
        yield m.group(3), attrs_of(m.group(1)), bool(m.group(2)), m.start(3), brace, close
        pos = close + 1


def analyze(text, b0, b1):
    body = text[b0:b1]
    ext = []
    for m in CLIENT_RE.finditer(body):
        ext.append(("client", b0 + m.start()))
    for m in EXT_RE.finditer(body):
        ext.append((m.group(1) or m.group(2) or "upgrade", b0 + m.start()))
    auth = [(m.group(3), m.group(1) + ("()" if m.group(2) else ""), b0 + m.start())
            for m in AUTH_RE.finditer(body)]
    writes = [(f"{m.group(1)}:{m.group(3)}", b0 + m.start()) for m in WRITE_RE.finditer(body)]
    for h in HANDLE_RE.finditer(body):
        handle_re = re.compile(r'(?<![\w.])' + re.escape(h.group(1)) + r'\s*\.\s*(?:set|remove|update|try_update)\s*'
                               r'(?:::\s*<[^>]*>)?\s*\(\s*&?\s*(?:mut\s+)?([\w:]+)')
        writes += [(f"{h.group(2)}:{m.group(1)}", b0 + m.start()) for m in handle_re.finditer(body, h.end())]
    return {"writes": sorted(writes, key=lambda w: w[1]),
            "ext": ext, "auth": auth,
            "as_contract": [b0 + m.start() for m in AS_CONTRACT_RE.finditer(body)],
            "tokens": [b0 + m.start() for m in TOKEN_RE.finditer(body)],
            "callees": {m.group(1) for m in CALL_RE.finditer(body)}}


def crate_of(root, rel):
    d = os.path.dirname(rel)
    while True:
        if os.path.isfile(os.path.join(root, d, "Cargo.toml")):
            return d
        if not d:
            return ""
        d = os.path.dirname(d)


def sdk_version(root):
    lock = os.path.join(root, "Cargo.lock")
    if os.path.isfile(lock):
        m = SDK_LOCK_RE.search(open(lock, encoding="utf-8", errors="replace").read())
        if m:
            return m.group(1)
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in {"target", ".git", ".audit", "node_modules"})
        if "Cargo.toml" in files:
            m = SDK_TOML_RE.search(open(os.path.join(dirpath, "Cargo.toml"), encoding="utf-8",
                                        errors="replace").read())
            if m:
                return (m.group(1) or m.group(2)).lstrip("=^~ ")
    return None


def parse_file(rel, src):
    text = blank_test_mods(strip(src))
    contracts = [(m.group(1), line_of(text, m.start(1))) for m in CONTRACT_RE.finditer(text)]
    impls = []
    for m in IMPL_RE.finditer(text):
        close = block_end(text, m.end() - 1)
        impls.append({"args": m.group(1) or "", "trait": m.group(2), "type": m.group(3),
                      "open": m.end() - 1, "close": close})
    ifaces = []
    for m in IFACE_RE.finditer(text):
        close = block_end(text, m.end() - 1)
        ifaces.append((m.group(1), line_of(text, m.start(1)), text.count("\n", m.end() - 1, close) + 1))
    fns = []
    for name, attrs, is_pub, npos, b0, b1 in functions(text, 0, len(text)):
        impl = next((i for i in impls if i["open"] < npos < i["close"]), None)
        entry = impl is not None and (impl["trait"] is not None or is_pub)
        fns.append({"name": name, "attrs": attrs, "pos": npos, "impl": impl, "entry": entry,
                    **analyze(text, b0, b1)})
    return {"rel": rel, "src": src, "text": text, "contracts": contracts, "impls": impls,
            "ifaces": ifaces, "fns": fns}


def resolve(parsed):
    """Transitive effects and auth guards through helper functions defined in the same crate.

    Same-name candidates: effects are unioned, guards intersected (no guard unless all provide it)."""
    by_name = {}
    for p in parsed:
        for f in p["fns"]:
            by_name.setdefault((p["crate"], f["name"]), []).append(f)
    for f in (f for p in parsed for f in p["fns"]):
        f["effects"] = bool(f["writes"] or f["ext"] or f["tokens"])
        f["writes_t"] = bool(f["writes"])
        f["guards_t"] = {f"{k}({r})" for k, r, _ in f["auth"]}
    changed = True
    while changed:
        changed = False
        for p in parsed:
            for f in p["fns"]:
                for callee in f["callees"]:
                    cands = [g for g in by_name.get((p["crate"], callee), []) if g is not f]
                    if not cands:
                        continue
                    if any(g["effects"] for g in cands) and not f["effects"]:
                        f["effects"] = changed = True
                    if any(g["writes_t"] for g in cands) and not f["writes_t"]:
                        f["writes_t"] = changed = True
                    for guard in set.intersection(*(g["guards_t"] for g in cands)):
                        via = guard if " via " in guard else f"{guard} via {callee}"
                        if guard not in f["guards_t"] and via not in f["guards_t"]:
                            f["guards_t"].add(via)
                            changed = True


def build_facts(root, rels, facts):
    parsed = []
    for rel in rels:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            parsed.append(parse_file(rel, fh.read()))
        parsed[-1]["crate"] = crate_of(root, rel)
    resolve(parsed)
    crate_contracts = {}
    for p in parsed:
        for name, _ in p["contracts"]:
            crate_contracts.setdefault(crate_of(root, p["rel"]), []).append(name)
    units = {}
    for p in parsed:
        for name, line in p["contracts"]:
            units[name] = {"name": name, "kind": "contract", "file": p["rel"], "line": line, "loc": 1,
                           "parents": []}
    for p in parsed:
        for i in p["impls"]:
            u = units.get(i["type"])
            if u is None:
                continue
            u["loc"] += p["text"].count("\n", i["open"], i["close"]) + 1
            if i["trait"]:
                parent = i["trait"].split("::")[-1]
                if parent not in u["parents"]:
                    u["parents"].append(parent)
        for name, line, loc in p["ifaces"]:
            units.setdefault(name, {"name": name, "kind": "interface", "file": p["rel"], "line": line,
                                    "loc": loc, "parents": []})
    facts["units"] = sorted(units.values(), key=lambda u: (u["file"], u["line"]))
    for p in parsed:
        rel, text = p["rel"], p["text"]
        owners = crate_contracts.get(crate_of(root, rel), [])
        default_unit = owners[0] if len(owners) == 1 else os.path.splitext(os.path.basename(rel))[0]
        c = {"loc": p["src"].count("\n"), "external_calls": 0, "state_writers": 0, "upgrades": 0,
             "token_transfers": 0, "unchecked_math": len(UNCHECKED_RE.findall(text)), "unguarded_mutators": 0}
        for f in p["fns"]:
            unit, fname = (f["impl"]["type"] if f["impl"] else default_unit), f["name"]
            for target, pos in f["writes"]:
                facts["storage_writes"].append({"unit": unit, "function": fname, "file": rel,
                                                "line": line_of(text, pos), "target": target})
            for kind, pos in f["ext"]:
                facts["external_calls"].append({"unit": unit, "function": fname, "file": rel,
                                                "line": line_of(text, pos), "kind": kind})
                c["external_calls"] += 1
                c["upgrades"] += kind == "upgrade"
            for pos in f["tokens"]:
                facts["value_transfers"].append({"unit": unit, "function": fname, "file": rel,
                                                 "line": line_of(text, pos), "asset": "token"})
                c["token_transfers"] += 1
            for kind, _, pos in f["auth"]:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, pos), "kind": kind})
            for pos in f["as_contract"]:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, pos),
                                            "kind": "authorize_as_current_contract"})
            macros = [a.split("(")[0].strip() for a in f["attrs"] if a.split("(")[0].strip() in AUTH_MACROS]
            for _ in macros:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, f["pos"]),
                                            "kind": "auth_macro"})
            if fname == "__check_auth" and f["entry"]:
                facts["auth_sites"].append({"unit": unit, "file": rel, "line": line_of(text, f["pos"]),
                                            "kind": "check_auth"})
            if not f["entry"]:
                continue
            vis = {"__constructor": "constructor", "__check_auth": "check_auth"}.get(fname, "external")
            guards = macros + sorted(f["guards_t"])
            mutating = f["effects"]
            facts["entry_points"].append({"unit": unit, "name": fname, "file": rel,
                                          "line": line_of(text, f["pos"]), "visibility": vis,
                                          "mutability": "mutating" if mutating else "view",
                                          "guards": guards})
            c["state_writers"] += f["writes_t"]
            c["unguarded_mutators"] += mutating and not guards and vis == "external"
        facts["counters"][rel] = c


def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract Soroban facts")
    ap.add_argument("--root", required=True)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--compile", default="unknown", choices=("ok", "failed", "unknown"))
    args = ap.parse_args(argv)
    root = os.path.abspath(args.root)
    pack = load_json(args.pack)
    facts = {"chain": "soroban", "mode": "regex", "root": root, "compile": args.compile,
             "sdk": sdk_version(root), "units": [], "entry_points": [], "auth_sites": [],
             "storage_writes": [], "external_calls": [], "value_transfers": [], "counters": {}}
    build_facts(root, scope_files(root, pack["scope"]), facts)
    write_json(args.out, facts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
