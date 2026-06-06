# Risk-scoring v0 — methodology

> ⚠️ **v0 is a stubbed, illustrative score. It is NOT insurer-grade.** The weights and
> component curves below are placeholders chosen for a demonstrable single-satellite path,
> pending review by an aerospace-insurance actuary before any number is shown to an insurer
> or regulator. Documented per ROADMAP Phase 2 and ADR-0002 (defensible, citable methodology).

## Purpose

Combine the L3 signals available in this slice into a single 0–100 **risk score** (higher =
riskier) with a coarse band (low / medium / high) and a transparent per-component breakdown,
so the operator portal can show not just the score but *why*.

## Inputs

| Input | Source | Meaning |
|---|---|---|
| `min_miss_distance_km` | Orekit `conjunction` (M2) | closest approach over the screening window |
| `filing_maturity` | ITU compliance (M5) | `early_stage` / `late_stage` / `brought_into_use` / `suspended` |
| `itu_compliant` | ITU compliance (M5) | whether a protecting filing covers the satellite's slot |
| `disposal_compliant` | placeholder (v0) | end-of-life / disposal-plan compliance — not yet wired |

## Components (each 0–100, higher = riskier)

- **Conjunction risk** — linear decay from a co-located approach to a "safe" separation:
  `clamp(100 · (1 − min_miss_distance_km / SAFE_KM), 0, 100)`, with `SAFE_KM = 50`.
  0 km → 100, 25 km → 50, ≥ 50 km → 0. Monotonic: a closer approach never lowers the risk.
- **Maturity risk** — an unprotected or lapsed filing is riskier:
  `brought_into_use → 0`, `late_stage → 30`, `early_stage → 60`, `suspended → 80`.
  An unknown value is treated conservatively as `early_stage` (60).
- **Compliance risk** — `itu_compliant → 0`, otherwise `50`.
- **Disposal risk** — `disposal_compliant → 0`, otherwise `100` (placeholder until wired).

## Weighting

```
score = 0.50 · conjunction + 0.20 · maturity + 0.15 · compliance + 0.15 · disposal
```

Conjunction dominates because a near-miss is the most immediate, defensible risk signal in
v0. The weights sum to 1, so `score ∈ [0, 100]`.

## Bands

| Band | Score |
|---|---|
| low | `< 34` |
| medium | `34 – 66` |
| high | `≥ 67` |

## Explicitly deferred

Operator track record, covariance-based probability-of-collision (v0 uses geometric
min-miss-distance only — ADR-0013), disposal/EOL data wiring, administration-match and
due-diligence scoring, and any actuarial calibration of the weights.
