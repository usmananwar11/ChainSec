# Preflight — Readiness Check

Reads: `chains/<chain>/pack.json` and the files under ROOT (no `A/` inputs)
Writes: `A/preflight.json` (gate mode only)

Shared readiness check used by both `chainsec-audit` (gate mode, pipeline phase 1) and
`chainsec-init` (report mode). `A` = `TARGET/.audit/<chain>/`; the pack manifest is
`chains/<chain>/pack.json`.

## Modes

The caller specifies one of two modes:

- **gate** (used by the pipeline before recon): run the hard checks only, plus the
  `tools.optional` checks needed to fill `tools` and `mode` in `A/preflight.json`. If anything hard
  fails, abort with a one-line message pointing the user at `chainsec-init` for details. Stay
  silent on success — the audit continues.
- **report** (used by `chainsec-init`): run every check, print the full summary table, never
  abort. Output is the verdict. Do not write `.audit/` files in report mode.

## Hard vs soft checks

| Check | Hard (gate-fails the audit) | Why |
|-------|------------------------------|-----|
| every `tools.required` entry of the pack | yes | the pack's extractor, PoC and fuzz steps depend on them (each entry's `purpose` says why) |
| ≥ 1 source file with a pack `extensions` suffix under ROOT | yes | nothing to audit otherwise |
| every `tools.optional` entry of the pack | no | optional signal, skipped silently if absent; the audit runs in `degraded` mode |
| the core folder is reachable | no | warn; the entry skill resolves CORE, a broken install shows up here |
| `.audit/` in `.gitignore` | no | cosmetic; warn |

## Step 1 — Required tooling

Read `chains/<chain>/pack.json`. For every entry in `tools.required` and `tools.optional`, run its
`check` command. Run the checks in parallel via Bash.

For each, capture `OK <version>` or `MISSING`. Do not speculate on install commands for platforms
you can't detect — use the entry's `install` value; if it has none, say "consult the project's docs."

Install hints (only mention when relevant) come from each entry's `install` field in `pack.json`.

## Step 2 — Project shape

Verify the target looks like a project for this chain: a source file with one of the pack's
`extensions` exists somewhere under ROOT. For each extension use:

```
find ROOT -type f -name '*<ext>' -not -path '*/node_modules/*' -not -path '*/lib/*' -not -path '*/target/*' | head -20
```

Count the matching files (the same `find` piped to `wc -l`) and record the count as
`scope_files`. Report the approximate source-file count. Zero source files → hard fail.

## Step 3 — Core folder and output hygiene (soft)

- **Core folder**: `CORE/engine/pipeline.md` and `CORE/chains/<chain>/pack.json` exist. If not, warn
  that the ChainSec skills must be installed together.
- **`.gitignore`**: Read `<target>/.gitignore` (read-only). ChainSec writes to `.audit/`; it
  should be gitignored.

If `.audit/` is missing from `.gitignore`, **tell** the user what to add but **do not edit** the file:

```
.audit/
```

If there is no `.gitignore` at all, say so and suggest creating one — don't create it.

In report mode every failed soft check becomes one line in `warnings`. Gate mode does not run the
soft checks, so they never appear in `A/preflight.json`.

---

## Output

### gate mode (for `chainsec-audit`)

If ALL hard checks pass: write `A/preflight.json`, emit one short line such as `Preflight OK.`
and continue with the next phase. Do not print the full table.

`A/preflight.json` fields:

- `chain`: the pack name.
- `mode`: `full` when every `tools.optional` entry is OK, otherwise `degraded`.
- `tools`: one key per required and optional tool name, value `OK <version>` or `MISSING`.
- `scope_files`: the source-file count from Step 2.
- `warnings`: `[]`; gate mode runs no soft checks. Later phases append one string per note meant
  for the report (e.g. per-unit's unclustered files).
- `incomplete_phases`: `[]`; the pipeline appends phases that could not complete.

```json
{"chain":"<chain>","mode":"degraded","tools":{"python3":"OK Python 3.12.4","<required-tool>":"OK 1.7.1","<optional-tool>":"MISSING"},"scope_files":12,"warnings":[],"incomplete_phases":[]}
```

If ANY hard check fails: do not write `A/preflight.json` (the pipeline's resume rule treats an
existing file as a passed preflight). Emit a single block, then STOP:

```
Preflight failed — cannot start audit:
  - <required-tool>: MISSING (install: <install from pack.json>)
  - source files in scope: none with extensions <extensions>

Run chainsec-init for the full readiness report.
```

Do not proceed to recon in gate mode if any hard check fails.

### report mode (for `chainsec-init`)

Build the same fields as `A/preflight.json` (without writing it) and emit the full summary table
from them:

```
| Check                 | Status              | Action                                          |
|-----------------------|---------------------|-------------------------------------------------|
| python3               | OK 3.12.4           | —                                               |
| <required-tool>       | OK 1.7.1            | —                                               |
| <optional-tool>       | MISSING             | optional; install: <install from pack.json>     |
| source files in scope | OK 47 files         | —                                               |
| core folder           | OK                  | —                                               |
| .audit/ in .gitignore | MISSING             | add line: .audit/                               |
```

Then a one-line verdict:

- `READY` — all checks OK.
- `READY (warnings)` — only soft checks failed; `chainsec-audit` will run.
- `NOT READY — fix the MISSING hard items above` — at least one hard check failed; `chainsec-audit` will refuse to start.

## Non-goals

- This phase does NOT install anything.
- This phase does NOT modify `.gitignore` or any source file.
- This phase does NOT validate the source code — that's the audit's job.
- Krait's MCP-wiring check (its Step 4) and Claude-home skills sync check (its Step 5) are dropped: ChainSec uses no MCP servers, and the entry skill resolves the core folder itself.
