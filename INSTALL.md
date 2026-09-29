# Installing ChainSec

ChainSec is one core skill (`chainsec`) plus five entry skills (`chainsec-audit`,
`chainsec-review`, `chainsec-poc`, `chainsec-fuzz`, `chainsec-init`). The entry skills
load the core with `../chainsec`, so **all six folders must be installed side by side**
in the same skills directory.

## Claude Code (plugin, recommended)

```
/plugin marketplace add usmananwar11/ChainSec
/plugin install chainsec@chainsec
```

Commands:

- `/chainsec:chainsec-audit`
- `/chainsec:chainsec-review`
- `/chainsec:chainsec-poc <ID>`
- `/chainsec:chainsec-fuzz`
- `/chainsec:chainsec-init`

## Codex

```
codex plugin marketplace add usmananwar11/ChainSec
```

**Unverified:** the `codex plugin marketplace add` command and Codex reading the Claude plugin
manifest have not been confirmed yet (pending the Codex smoke test). Or, in your project:

```
git clone https://github.com/usmananwar11/ChainSec
ChainSec/install.sh --tool agents
```

Invoke with `$chainsec-audit`.

## OpenCode

```
ChainSec/install.sh --tool opencode
```

or, to install for every project: `ChainSec/install.sh --tool opencode --global`.
OpenCode also reads `.agents/skills` and `.claude/skills`. Ask: "use the chainsec-audit skill".

## Antigravity

```
ChainSec/install.sh --tool antigravity
```

installs to the project's `.agents/skills`; `--global` installs to `~/.gemini/config/skills`
instead. Invoke `/chainsec-audit`.

**Unverified:** the Antigravity paths are not yet confirmed by the smoke tests — whether the
workspace folder is `.agents/skills` or `.agent/skills`, and the global path. Treat them as
best-effort until confirmed.

## Cursor / Gemini CLI

```
install.sh --tool agents
```

## Requirements

- `python3` ≥ 3.11.
- The tools `chainsec-init` reports for your chain. For Solidity: `forge` (required), `slither`
  (optional).

## Updating

Re-run `install.sh` — it replaces only ChainSec's own folders, leaving everything else in your
skills directory untouched. In Claude Code, `/plugin update` does the same for the plugin install.

## Limitations

One root per chain (v0.1): with several roots for one chain, the audit stops and asks you to run
`chainsec-audit <TARGET>/<root>` for each root.

## Important

The six `chainsec*` folders must be installed side by side in the same directory. Moving or
renaming only some of them will break the entry skills' `../chainsec` references.
