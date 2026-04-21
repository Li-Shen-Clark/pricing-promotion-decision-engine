# A/B Validation Design — execution summary
Generated: 2026-04-20T23:56:12

## 1. Load
- top-10 portfolio candidates: 10
- cell_baselines rows: 5,896
- modeling dataset rows: 2,585,593
## 2. Weekly profit variance
- σ (median across top-10): $64.87/store-week
- σ (range): $41.24 – $152.98
## 3. Risk classification
- flag_extrapolation: 10/10 candidates trip
- flag_large_q_change: 0/10 candidates trip
- flag_high_price_jump: 9/10 candidates trip
- flag_low_baseline_volume: 0/10 candidates trip
- risk distribution: {'high': 9, 'medium': 1, 'low': 0}
## 4. Test type assignment
- single_store_flight: 9, cluster_rct: 1
## 5. Sample size
- median n_storeweeks/arm @ 50% MDE, 80% power: 13
- median weeks per treatment store: 12.9 (vs planned duration 8 weeks)
- candidates whose required weeks > planned duration: 7/10
## 6. Sample size curves
- saved: reports/figures/ab_sample_size_curve.png
- representative σ = $65/store-wk, baseline = $74/store-wk
## 7. Experiment candidates
- saved: data/processed/experiment_candidates.csv

| brand | size | store | curr → cand | promo | risk | test type | weeks×stores |
|---|---|---|---|---|---|---|---|
| Kellogg's | 15.00 | 102 | 3.02 → 4.30 | 1 | high | single_store_flight | 8w × 1st |
| General Mills | 20.00 | 126 | 4.02 → 5.16 | 1 | medium | cluster_rct | 6w × 5st |
| General Mills | 12.00 | 102 | 2.95 → 3.91 | 1 | high | single_store_flight | 8w × 1st |
| Kellogg's | 20.00 | 80 | 3.54 → 5.11 | 1 | high | single_store_flight | 8w × 1st |
| General Mills | 14.00 | 126 | 3.25 → 4.32 | 1 | high | single_store_flight | 8w × 1st |
| Kellogg's | 18.00 | 74 | 3.15 → 5.23 | 1 | high | single_store_flight | 8w × 1st |
| General Mills | 18.00 | 126 | 3.66 → 5.20 | 1 | high | single_store_flight | 8w × 1st |
| Kellogg's | 12.00 | 18 | 2.50 → 3.77 | 1 | high | single_store_flight | 8w × 1st |
| General Mills | 15.00 | 126 | 3.12 → 4.11 | 1 | high | single_store_flight | 8w × 1st |
| Post | 16.00 | 126 | 2.85 → 4.05 | 1 | high | single_store_flight | 8w × 1st |
## 8. AB test plan
- saved: reports/ab_test_plan.md (61 lines)
## 9. App wireframe
- saved: docs/app_wireframe.md (71 lines)
## 10. Limitations & handoff
1. **Sample size assumes i.i.d. store-weeks**. With store FE + clustering, effective n is smaller; the formula here is a planning estimate, not a final design. For deployment, use a panel power simulation that respects the within-store correlation structure.
2. **σ estimated from observed period at observed prices** — variance under treatment may differ if price shifts demand into a different regime. Re-estimate σ after wave 1 before sizing waves 2+.
3. **No matched-control selection algorithm** documented for `single_store_flight` — should be added in a follow-up: nearest-neighbor on (baseline_q, mean_p, baseline_profit, brand portfolio mix) within the same census region.
4. **Stockout / inventory guardrail is heuristic** — flagged via 40% units drop, but DFF lacks true stockout indicators. Real deployment needs an inventory feed.
5. **No multiple-testing correction** across the 10 candidates — when running 10 tests in parallel, expect ~0.5 false positives at α=0.05. For MVP that is acceptable; production should apply Benjamini-Hochberg or sequential testing.

## Handoff to Streamlit build
- App wireframe: `docs/app_wireframe.md`
- Inputs the app needs (all already produced):
    · data/processed/all_recommendations.csv
    · data/processed/top_recommendations_diverse.csv
    · data/processed/cell_baselines.parquet
    · data/processed/model_coefficients.csv
    · data/processed/experiment_candidates.csv
    · reports/demand_model_summary.md, counterfactual_summary.md, ab_test_plan.md
    · reports/figures/*.png