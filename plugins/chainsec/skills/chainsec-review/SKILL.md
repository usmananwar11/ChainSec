---
name: chainsec-review
description: Second opinion on findings a ChainSec audit killed; re-examines over-kill-prone gates and chains killed findings into new attack paths. Needs a finished chainsec-audit run.
argument-hint: "[path] [--chain <name>]"
---

# ChainSec review

1. Resolve CORE as in chainsec-audit (`cd ../chainsec && pwd`; stop with the INSTALL.md message if
   `../chainsec/engine/phases/review.md` is missing).
2. TARGET = first non-flag argument or the current directory. For each `TARGET/.audit/<chain>/verdicts.json`
   (or only `--chain`'s): if none exist, tell the user to run chainsec-audit first and stop.
3. Follow `../chainsec/engine/phases/review.md` for that chain (dispatch per `../chainsec/engine/pipeline.md`
   "Dispatch", template `../chainsec/prompts/reviewer.md`, output `TARGET/.audit/<chain>/review.json`).
4. Present the results exactly as review.md's "Presentation to User" section describes.
5. If `review.json` has revived findings (status `verified-conditional` or `downgraded`), offer to
   regenerate the report. On yes, re-run the report phase: `../chainsec/engine/phases/report.md`
   via the reporter template `../chainsec/prompts/reporter.md` (dispatched as in step 3), which
   reads `review.json`.
