# Counterfactual Simulator Summary
Generated: 2026-04-20T23:43:53

---

## Headline finding (must read before interpreting recommendations)

The optimizer frequently binds at the upper price guardrail: **98.5% of eligible cells recommend the maximum allowed price**. This is a **diagnostic result**, not evidence that the optimizer is production-ready. Under constant-elasticity demand, \(Q=A p^\varepsilon\), single-product profit maximization implies a Lerner condition \((p-c)/p=-1/\varepsilon\). With β_own ≈ -1.73, the implied unconstrained margin is about 58%, so the AAC-derived cost proxy and log-linear demand curve mechanically push many cells above historical support and into the guardrail.

These rows should be interpreted as **candidate price increases that require controlled validation**, not direct deployment recommendations.

**Why we will not deploy these directly:**
1. No competitor response (rival prices held at historical mean)
2. No within-brand cross-size cannibalization adjustment yet (raising 18oz price may shift demand to 12oz)
3. No loss-leader role in category traffic
4. No nonlinear elasticity near price extremes (log-linear assumed everywhere in the grid)
5. Historical observational estimates, not causal effects

**Correct framing**: every cell in `top_recommendations*.csv` is a **raise-and-test candidate**, designed to feed the experiment-design step in `05_ab_testing_design.ipynb`.

---


## 1. Load
- main model = baseline_with_cross
- β_own = -1.7276, β_cross = 0.6449, θ_promo = 0.4269 (conditional sale-code effect; `exp(θ)-1` ≈ 53.2%), S = 1.1395
- modeling dataset rows: 2,585,593
## 2. Cell baselines + eligibility
- raw cells (brand-size-store): 16,969
- failure counts (any cell can fail multiple):
    · fail_n_weeks_lt_52: 5,873
    · fail_cost_le_0: 0
    · fail_outside_IQR: 7,872
    · fail_cv_gt_0.5: 0
    · fail_mean_q_lt_5: 630
- eligible cells: 5,896 (34.7%)
## 3. Demand function
- sanity (anchor → anchor): predicted Q = 10.945 vs mean_q = 10.945  (no S multiplier)
## 4. Calibration
- observed Σ Q                 = 42,931,019
- cell-anchor predicted (S=1)  = 45,688,169  ratio = 1.0642
- cell-anchor × S=1.14         = 52,059,975  ratio = 1.2126
  → S=1.0 is the right choice for anchor-based prediction (no double counting).
## 5. Baseline economics
- mean baseline profit per cell: $14.19
- total baseline revenue across eligible cells: $482,876
- total baseline profit across eligible cells: $83,638
## 6. Constraints
- price grid len (sample cell): 21, range [2.307, 3.484]
- margin floor: price ≥ 1.05 × cost
## 7. Grid search
- cells optimized: 5,896
- mean profit lift: $22.69/cell (median 14.43)
- cells with non-trivial lift (≥5%): 5,896
- cells at status quo already optimal: 0
- cells whose recommendation pegs the upper price grid bound: 5,810 (98.5%) — flagged as extrapolation risk
## 8. Top-10 recommendations
- saved: data/processed/top_recommendations.csv (raw) + top_recommendations_diverse.csv

### Top-10 (raw, by profit lift)
| brand | size | store | mean_p → opt_p | promo→ | Q×↑ | Δprofit | upper-bound? |
|---|---|---|---|---|---|---|---|
| Kellogg's | 15.00 | 102 | 3.03 → 4.30 | 0→1 | 0.72× | $311.31 (166.8%) | ⚠ yes |
| Kellogg's | 15.00 | 73 | 3.02 → 4.29 | 0→1 | 0.72× | $294.90 (174.6%) | ⚠ yes |
| Kellogg's | 15.00 | 122 | 3.04 → 4.28 | 0→1 | 0.75× | $289.23 (176.7%) | ⚠ yes |
| Kellogg's | 15.00 | 8 | 3.06 → 4.38 | 0→1 | 0.72× | $285.29 (155.6%) | ⚠ yes |
| Kellogg's | 15.00 | 114 | 3.07 → 4.35 | 0→1 | 0.72× | $258.23 (163.9%) | ⚠ yes |
| Kellogg's | 15.00 | 132 | 3.04 → 4.26 | 0→1 | 0.73× | $241.58 (165.2%) | ⚠ yes |
| Kellogg's | 15.00 | 126 | 3.05 → 4.27 | 0→1 | 0.77× | $230.00 (164.3%) | ⚠ yes |
| Kellogg's | 15.00 | 86 | 3.08 → 4.46 | 0→1 | 0.70× | $224.06 (151.8%) | ⚠ yes |
| Kellogg's | 15.00 | 98 | 3.03 → 4.30 | 0→1 | 0.73× | $218.91 (173.1%) | ⚠ yes |
| Kellogg's | 15.00 | 112 | 3.05 → 4.28 | 0→1 | 0.74× | $218.69 (169.4%) | ⚠ yes |

### Top-10 (one per brand-size, portfolio view)
| brand | size | store | mean_p → opt_p | promo→ | Q×↑ | Δprofit | upper-bound? |
|---|---|---|---|---|---|---|---|
| Kellogg's | 15.00 | 102 | 3.03 → 4.30 | 0→1 | 0.72× | $311.31 (166.8%) | ⚠ yes |
| General Mills | 20.00 | 126 | 4.02 → 5.16 | 0→1 | 0.97× | $195.17 (186.5%) | ⚠ yes |
| General Mills | 12.00 | 102 | 2.95 → 3.91 | 0→1 | 0.89× | $160.73 (169.6%) | ⚠ yes |
| Kellogg's | 20.00 | 80 | 3.54 → 5.11 | 0→1 | 0.75× | $150.93 (200.3%) | ⚠ yes |
| General Mills | 14.00 | 126 | 3.25 → 4.32 | 0→1 | 0.91× | $143.47 (168.7%) | ⚠ yes |
| Kellogg's | 18.00 | 74 | 3.15 → 5.23 | 0→1 | 0.61× | $141.41 (208.1%) | ⚠ yes |
| General Mills | 18.00 | 126 | 3.66 → 5.20 | 0→1 | 0.81× | $139.12 (199.1%) | ⚠ yes |
| Kellogg's | 12.00 | 18 | 2.50 → 3.77 | 0→1 | 0.72× | $128.78 (223.6%) | ⚠ yes |
| General Mills | 15.00 | 126 | 3.12 → 4.11 | 0→1 | 0.91× | $121.58 (168.1%) | ⚠ yes |
| Post | 16.00 | 126 | 2.85 → 4.05 | 0→1 | 0.78× | $115.42 (172.1%) | ⚠ yes |
## 9. Sensitivity
- grid: 3 × 3 × 3 = 27 param combos
- saved: data/processed/sensitivity_grid.csv

Top-10 sensitivity range (per cell):
| brand | size | store | price [min, med, max] | lift [min, med, max] |
|---|---|---|---|---|
| General Mills | 12.00 | 102 | [3.91, 3.91, 3.91] | [$123.0, $167.0, $217.9] |
| General Mills | 14.00 | 126 | [4.32, 4.32, 4.32] | [$108.6, $149.9, $195.7] |
| General Mills | 15.00 | 126 | [4.11, 4.11, 4.11] | [$92.7, $126.9, $165.1] |
| General Mills | 18.00 | 126 | [5.20, 5.20, 5.20] | [$104.7, $144.7, $191.3] |
| General Mills | 20.00 | 126 | [5.16, 5.16, 5.16] | [$150.3, $205.8, $261.6] |
| Kellogg's | 12.00 | 18 | [3.77, 3.77, 3.77] | [$97.0, $136.9, $178.0] |
| Kellogg's | 15.00 | 102 | [4.30, 4.30, 4.30] | [$243.8, $334.3, $422.0] |
| Kellogg's | 18.00 | 74 | [5.23, 5.23, 5.23] | [$103.4, $152.4, $202.1] |
| Kellogg's | 20.00 | 80 | [5.11, 5.11, 5.11] | [$116.3, $161.4, $205.4] |
| Post | 16.00 | 126 | [4.05, 4.05, 4.05] | [$87.6, $122.9, $158.8] |
## 10. Artifacts saved
- data/processed/cell_baselines.parquet  (eligible cells + recommendations, parquet)
- data/processed/all_recommendations.csv
- data/processed/top_recommendations.csv
- data/processed/top_recommendations_diverse.csv
- data/processed/sensitivity_grid.csv
- reports/figures/counterfactual_top10_lift.png
- reports/figures/counterfactual_sensitivity_top1.png

## Limitations (to disclose in memo)
1. **Cell-anchored prediction assumes log-linearity holds locally** —— extrapolations beyond `[0.85·p_min, 1.15·p_max]` are clipped by the grid; recommendations pegging the upper bound (flagged ⚠ in §8) should be treated as "raise, but verify with a smaller test" rather than a literal price target.
2. **No retransformation correction needed for anchor predictions** —— `mean_q` is empirical level, not log; smearing factor S=1.14 from 03 applies to FE-based holdout prediction only.
3. **Competitor price held fixed in main table** —— ignores game-theoretic response. Sensitivity grid varies β_cross × p_comp ±10% as a what-if.
4. **Within-brand cross-size cannibalization** not modeled —— raising 18oz price may shift demand to the 12oz SKU of the same brand; current optimizer treats each brand-size-store cell independently. This is the main target for `07_cannibalization_robustness.ipynb`.
5. **Inventory not constrained** —— large predicted Q lifts assume restock capacity; flagged in top-10 view via `q_lift_ratio` column.
6. **Margin uses AAC-derived unit_cost** —— see 03 limitation #2 (AAC ≠ marginal cost). Profit numbers are directionally useful, not exact accounting.
7. **Eligibility filter (52-wk history, IQR price band) excludes new SKUs and clearance cells** —— intentional for MVP recommendation reliability; downstream can relax.

---

**Final positioning**: Optimizer output should be interpreted as **candidate actions for experimentation, not production deployment**. See `reports/ab_test_plan.md` for the validation protocol.
