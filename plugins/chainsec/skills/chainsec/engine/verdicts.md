# Statuses, verdicts and evidence

Every finding carries exactly one `status` (see `engine/finding.schema.json`):

| status | Meaning | Reported? |
|---|---|---|
| `candidate` | Produced by a detection phase, not yet verified | No |
| `verified` | Exploitable; concrete exploit trace and harm statement present | Yes |
| `verified-conditional` | Mechanism confirmed but depends on stated conditions (listed in `preconditions`) | Yes |
| `downgraded` | Real issue, severity lowered (`verdict.original_severity` keeps the old one) | Yes, at the new severity |
| `killed` | Disproven, excluded by a kill gate, or insufficient evidence | No (reviewable by chainsec-review) |

`verdict.gate` records why a finding was killed: a gate letter `A`–`H`, `impact-premise`,
`fp-pattern:<id>`, or `insufficient-evidence`.

## Mapping from Krait's vocabularies

| Krait critic | Krait orchestrator | Krait reporter | ChainSec `status` |
|---|---|---|---|
| TRUE POSITIVE (TP) | VERIFIED | TRUE POSITIVE | `verified` |
| LIKELY TRUE (LT) | VERIFIED-CONDITIONAL | LIKELY TRUE | `verified-conditional` |
| DOWNGRADE | DOWNGRADE | — | `downgraded` |
| FALSE POSITIVE (FP) | KILLED | — | `killed` (gate = FP pattern or gate letter) |
| INSUFFICIENT EVIDENCE (IE) | KILLED | — | `killed` (gate = `insufficient-evidence`) |

## Evidence tags (`verdict.evidence_tag`)

Every finding carries an **Evidence** line saying how strongly it was verified. This is the
payoff of the opt-in PoC pass: a client can see at a glance which findings have mechanical
proof versus expert reasoning. Derive it from the finding's evidence tag (from the critic,
or from a `chainsec-poc` run if one was done):

| Evidence line | When | Meaning |
|---------------|------|---------|
| `PROVEN — executed PoC [POC-PASS]` | A `chainsec-poc` run reproduced the harm AND the finding survived the falsification gate (the defective line, corrected, kills the exploit; the fix also kills it) | Ground truth. Attach the passing harm assertion, the defect-mutation that pinned it, and the verified fix diff. |
| `PROVEN — fix insufficient [POC-PASS · FIX-INSUFFICIENT]` | Pinned and real, but the recommended fix does NOT close the exploit | The bug is confirmed; the *remediation* is flagged. Report the exploit surviving the proposed fix and note a correct fix is pending human review. **Not** a weaker finding — often a more important one. |
| `REASONED — code trace [CODE-TRACE]` | Verified by the critic's trace, no PoC run, un-PoC-able by nature, OR a PoC reproduced but was **not pinned** to the defect (`[POC-UNPINNED]`) | A real finding held on reasoning. **NOT** "unverified." An `[POC-UNPINNED]` finding is here because its test did not prove the cited line caused the harm — the mechanism may still be real, so it is flagged for human review, never dropped on the PoC's say-so. |
| `DISPUTED — PoC did not reproduce [POC-FAIL]` | A PoC was attempted and the harm did not materialize | Should normally have been dropped by the critic; if it still appears, flag it loudly for human review. |

Rules:

- **`REASONED` is not a weaker finding, just a differently-evidenced one.** Never imply a
  finding is doubtful because it lacks a PoC — some of the highest-value findings (trusted-
  actor, off-chain, cross-chain) are un-PoC-able by construction.
- A `PROVEN` finding SHOULD carry its harm assertion in the PoC block and its verified fix in
  the Recommendation — that is the concrete value of having run the PoC.
- If no PoC pass was run at all, every finding is `REASONED` — that is the normal default
  audit, and it is fine.
