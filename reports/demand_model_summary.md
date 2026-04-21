# Demand Model Summary — baseline
Generated: 2026-04-20T16:51:03

---

## FROZEN — Main model for MVP counterfactuals

**Model**: `+Cross` brand-size-store-week FE (linearmodels AbsorbingLS), MOVE-weighted aggregation, OLS on log-log + promo dummy.

**Main coefficients** (used by `04_counterfactual.ipynb` by default):

| Parameter | Value |
|---|---|
| β_own  (log_p)         | **-1.73** |
| β_cross (log_comp_price) | **+0.65** |
| promo_any sale-code effect (log-point) | **+0.43** |
| implied promo demand difference (`exp(θ)-1`) | **+53.2%** |
| smearing factor S       | **1.14** |

**Robustness** (UPC × store × week panel):

| Parameter | Value |
|---|---|
| β_own (UPC-level)      | -1.90 |
| β_cross (UPC-level)    | +0.50 |
| promo sale-code effect (UPC-level, log-point) | +0.51 |
| implied promo demand difference (UPC-level) | +66.4% |
| smearing (UPC)         | 1.17 |

**04 sensitivity grid** (counterfactual robustness):

- `β_own` lower/upper: **-1.90, -1.73, -1.50**
- `β_cross` sensitivity: **0, +0.50, +0.65**
- `promo` sensitivity: **+0.30, +0.43, +0.51**

**Holdout caveat**: Holdout APE (median 42.3%, last 20 weeks) is elevated because the MVP uses a transparent FE demand model **without IV, dynamic stockpiling, or generalizable seasonal interactions**. Results are used for **counterfactual decision support, not production-grade forecasting**. Any point forecast should be read alongside the sensitivity band above.

**Eligibility filter for 04 top-N recommendations** (applied before price optimization, to avoid dirty cells biasing decisions):

- `brand_confidence ∈ {high, medium}`
- `size_kind ∈ {oz, oz_bundle}` with valid `size_oz`
- sufficient historical weeks (≥ 52)
- `unit_cost > 0`
- reasonable current `unit_price` band (within IQR of brand-size distribution)
- `cell_quality_flag` does not include `high_price_dispersion`
- minimum `quantity` threshold (drops thin cells)

---


## 1. Load
- baseline panel (brand × size × store × week): 2,690,548 rows, 7 brands, 93 stores, 366 weeks
- robustness panel (UPC × store × week): 4,654,156 rows
## 2. Modeling dataset (baseline)
- rows: 2,585,593 (dropped 104,955 for low-quantity/zero)
- promo_any share: 9.27%
- log_q: mean=2.90, sd=0.97
- log_p: mean=1.12, sd=0.25
## 3. Competitor price index
- dropped rows with no competitor in same store-week: 0
- remaining rows: 2,585,593
- log_comp_price: mean=1.09, sd=0.09
- brand-size-store units: 16,969
- week units: 366
## 4. Baseline FE model (own price + promo)
- n obs = 2,585,593
- R² within absorbed = 0.7470
- β_own  (log_p)         = -1.7464  [SE 0.0198]
- θ (promo_any)          = +0.4326  [SE 0.0037]
## 5. FE model with cross price
- n obs = 2,585,593
- R² within absorbed = 0.7479
- β[log_p] = -1.7276  [SE 0.0197]
- β[log_comp_price] = +0.6449  [SE 0.0168]
- β[promo_any_int] = +0.4269  [SE 0.0037]
## 6. Robustness UPC-level model
- n obs = 4,553,237
- R² within absorbed = 0.6222
- β[log_p] = -1.8999  [SE 0.0121]
- β[log_comp_price] = +0.5007  [SE 0.0118]
- β[promo_any_int] = +0.5094  [SE 0.0032]
## 7. Smearing
- baseline smearing factor S = 1.1395
- UPC robustness smearing S = 1.1708
  (S≈1 indicates near-symmetric residuals; >1 means naive exp undershoots mean)
## 8. Holdout (last 20 weeks)
- train rows: 2,423,718, test rows: 158,824
- median APE: 42.3%
- RMSE: 55.01 units
## 9. Coefficient table
-      baseline_own_only: own β=-1.746, cross β=+nan, promo θ=+0.433 (implied diff +54.1%), R²w=0.747
-    baseline_with_cross: own β=-1.728, cross β=+0.645, promo θ=+0.427 (implied diff +53.2%), R²w=0.7479
-         robustness_upc: own β=-1.900, cross β=+0.501, promo θ=+0.509 (implied diff +66.4%), R²w=0.6222
- saved: data/processed/model_coefficients.csv

## Limitations (to disclose in memo)

1. **No IV**: own price, competitor price, and sale-code timing are observational choices. Remaining endogeneity (unobserved within-cell shocks correlated with price or promotion timing) can bias β_own, β_cross, and θ_promo. Next notebook adds Hausman IV (same-brand prices in other stores) and cost-shock IV.
2. **AAC ≠ marginal cost**: PROFIT-based unit_cost drags behind true replacement cost (see rawData/README §3.4). Margin numbers are directionally useful but not a strict marginal-cost measure.
3. **Competitor price index is simple quantity-weighted mean**: not a full demand system. Cross-elasticity here is a reduced-form substitution signal, not a utility-based Nevo-style estimate.
4. **Holdout is the last 20 weeks only**: pure forecast test, not out-of-sample cross-validation. Store-week rollout of new UPCs is censored.
5. **Unknown SALE code G** (~0.15% of aggregated rows) is bucketed as promo but its exact mechanism is undocumented.
6. **brand_confidence=low UPCs excluded** (31 UPCs, including the 4 Nabisco/Post conflict UPCs) — robustness panel keeps them.

**Promotion interpretation note**: θ_promo is a conditional sale-code coefficient in log points, not a clean causal promotion effect. When shown as a percentage, the report uses `exp(θ)-1`; for θ≈0.43 this is about 53–54%.
