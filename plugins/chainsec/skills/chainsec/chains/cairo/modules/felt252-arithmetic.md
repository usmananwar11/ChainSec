# felt252 & Integer Arithmetic Module

> **Trigger**: Value or index math on `felt252`, narrowing conversions (`try_into`), manual `u256` limbs, or bit-packing into `felt252`
> **Inject into**: Lens D (Edge/Math/Standards) + Lens B (Value/Economic)
> **Priority**: HIGH — felt252 wraps silently; it is the most Cairo-specific arithmetic failure
> <!-- Ported from keep-starknet-strange cairo-auditor (MIT): felt252/integer notes, UNSAFE-TYPE-CONVERSION, PRECISION-LOSS and attack vectors 44, 45, 53-55, 60, 104, 107, 108, 115, 145, 146, 169, 170; see ATTRIBUTION.md -->

## 1. Type Semantics

| Type | Overflow / underflow | Division | Use for |
|---|---|---|---|
| `felt252` | Wraps modulo P = 2^251 + 17·2^192 + 1, no panic | Field division (modular inverse) | Hashes, selectors, class hashes, storage keys, signatures |
| `u8`…`u128`, `u256` | Panics | Floor division, panics on zero | Balances, amounts, prices, fees, timestamps, counters |
| `i8`…`i128` | Panics | Integer division (check the sign convention) | Signed deltas, ticks, funding |
| `wrapping_*` / `overflowing_*` / `saturating_*` | Wrap / report / clamp | — | Deliberate opt-outs: justify each |

## 2. felt252 in Value Math

List every `felt252` operand in arithmetic (`A/facts.json` counter `felt_arith`, then read):

| Location | Expression | Represents | Can it wrap? | Impact |
|---|---|---|---|---|

- A subtraction that can go "negative" wraps to ~P: balance checks after the fact pass (FELT-01, AV-45).
- `felt252_div` in pricing/shares is wrong for any non-exact division (FELT-02).
- Ordering comparisons on wrapped values; conversions of wrapped values into `u256` (FELT-03).
- Packing: sum of field widths ≤ 251 bits, each field asserted before packing (FELT-04); parameters fed into hashes or bit operations range-checked (AV-145).

## 3. Conversions

For every `try_into()` / `into()`:
- Widening (`into`) is total. Narrowing returns `Option`: `unwrap()`/`expect()` → panic DoS (who can force it, on whose path? UNSAFE-TYPE-CONVERSION); `unwrap_or(default)` → silent wrong value.
- `u256 → felt252` fails at ≥ P; `felt252 → ContractAddress` requires < 2^251; 32-byte external ids do not fit (AV-169).
- Counts narrowed into small types (`u8`) misjudge quorums (AV-170); signed ↔ unsigned tick/price casts (AV-55).
- Manual `u256 { low, high }` construction and limb order in decoders (U256-01).

## 4. Panics as Denial of Service

Checked arithmetic turns bugs into reverts. For each panic site on a core path (liquidation, withdrawal, settlement, epoch close, `#[l1_handler]`):
- Can an unprivileged attacker make it panic for someone else (AV-60)? That is the engine's DoS exception, not an FP-7 kill.
- Unsigned loop counters decremented past zero; index wraparound in ring buffers (AV-115, AV-146).

## 5. Precision

- Division before multiplication (AV-53); intermediate multiply overflow before a safe divide (AV-108).
- Scale mismatches: WAD/RAY (AV-54), bps denominators (AV-104), per-asset decimals (AV-107); fixed-point helpers tested with low-decimal tokens (Opus H-02: Wad truncation for < 18 decimals).
- Low scale factors (PRECISION-LOSS); rounding direction favors the protocol on every division (zkLend: truncation plus accumulator manipulation in an empty market).
- Trace the three most complex arithmetic functions with concrete values (normal, boundary, adversarial), as Lens D requires.
