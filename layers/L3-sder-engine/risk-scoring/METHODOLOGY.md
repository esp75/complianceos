# Risk-scoring v0.1 — methodology

> ⚠️ **This is a stubbed, illustrative score. It is NOT insurer-grade.** The weights and
> component curves below are placeholders chosen for a demonstrable single-satellite path,
> pending review by an aerospace-insurance actuary before any number is shown to an insurer
> or regulator. Documented per ROADMAP Phase 2 and ADR-0002 (defensible, citable methodology).

> **v0.1 (post-review):** the conjunction component was changed from a linear ramp with a
> 50 km cutoff to an **exponential decay** at a few-km characteristic distance (collision
> risk is not linear in miss distance, and operational screening volumes are km-scale), and
> now folds in **relative speed** as a consequence multiplier. The conjunction component is
> still the largest weight despite being the least-calibrated input — flagged for the
> actuarial review.

## Purpose

Combine the L3 signals available in this slice into a single 0–100 **risk score** (higher =
riskier) with a coarse band (low / medium / high) and a transparent per-component breakdown,
so the operator portal can show not just the score but *why*.

## Inputs

| Input | Source | Meaning |
|---|---|---|
| `min_miss_distance_km` | Orekit `conjunction` (M2) | closest approach over the screening window |
| `relative_speed_km_s` | Orekit `conjunction` (M2) | relative speed at the closest flagged approach (optional) |
| `filing_maturity` | ITU compliance (M5) | `early_stage` / `late_stage` / `brought_into_use` / `suspended` |
| `itu_compliant` | ITU compliance (M5) | whether a protecting filing covers the satellite's slot |
| `disposal_compliant` | placeholder (v0) | end-of-life / disposal-plan compliance — not yet wired |

## Components (each 0–100, higher = riskier)

- **Conjunction risk** — `geometry · speed_factor`, where:
  - `geometry = 100 · exp(−min_miss_distance_km / CHAR_KM)`, with `CHAR_KM = 2.0` km.
    100 at a direct hit, ~37 at 2 km, ~0.7 at 10 km, ~0 by 20 km. Monotonic: a closer
    approach never lowers the risk. This replaces the v0 linear ramp, which mis-scored a
    routine 25 km pass at 50/100.
  - `speed_factor = clamp(relative_speed_km_s / 10.0, 0.3, 1.0)`; unknown speed → 1.0 (no
    discount, conservative). A fast head-on LEO pass is higher-consequence than a slow
    co-planar one.
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
