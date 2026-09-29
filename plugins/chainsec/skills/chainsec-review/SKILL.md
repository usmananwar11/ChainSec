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
   regenerate the report. Say that the report is rebuilt from `verdicts.json` and `review.json`, so
   final ids can shift and PoC results recorded by chainsec-poc (`verdict.evidence_tag` in
   `findings.json`, `poc/<id>/` folders) are not carried over. On yes, for each reviewed chain
   whose `TARGET/.audit/<chain>/report.md` exists, re-run the report phase:
   `../chainsec/engine/phases/report.md` via the reporter template `../chainsec/prompts/reporter.md`
   (dispatched as in step 3), which reads `review.json`. Then re-run the "After all chains"
   section of `../chainsec/engine/pipeline.md` (with TARGET and CORE) so `TARGET/.audit/report.md`
   and `TARGET/.audit/findings.json` match the regenerated chain reports.
