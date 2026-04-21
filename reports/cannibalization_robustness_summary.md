**Headline.** β_same (own-brand other-size cross-price coef) = +0.231 (SE 0.018, p = 0.000). Median |spillover adjustment| across top-10 candidates = 2.5% (max 4.0%).

**Limited first-order impact**: β_same is positive and significant but small in magnitude — top-10 adjustment is 2.5% (median, max 4.0%). Document the diagnostic; the MVP optimizer is fit-for-purpose without joint optimization.

---

# Cannibalization Robustness Summary
Generated: 2026-04-21T01:01:05

## Question
Within the same brand and store, do other-size price changes shift the focal size's demand? If yes, the optimizer's per-cell raise-price recommendation over-states portfolio profit by ignoring within-brand substitution.

## 1. Load
- demand_modeling_dataset: 2,585,593 rows, 7 brands, 93 stores, 366 weeks
- brand-store combos: 644; with ≥2 sizes: 644 (100.0%)

## 2. Same-brand other-size price index
Construction: for each (brand, store, week, size = focal size K), compute the baseline-quantity-weighted geometric mean of `log unit_price` across all OTHER sizes of the same brand at the same store-week. **Baseline weights are the size-level mean quantity over the whole sample within (brand, store)** — time-invariant, so they do not absorb current-week demand shocks.
- baseline weights computed for 16,969 (brand,store,size) cells
- rows with same-brand index defined: 2,582,666 of 2,585,593 (99.9%)
- median # other sizes per brand-store-week: 20
- corr(log_p_focal, log_p_same) = +0.468  (high but not 1 → meaningful within-week within-brand variation)

## 3. Fixed-effect models
All models share the same regression sample (rows where the same-brand index is defined) so coefficients are directly comparable. FE = brand×size×store + week.
  fitting M0_baseline ...
  fitting M1_with_cross ...
  fitting M2_with_same_brand ...

### Coefficient table (full pooled sample)
- N obs (common sample): 2,582,666

| spec | β_own | β_cross (other brands) | β_same (own brand) | θ_promo | R² within |
|------|------:|------:|------:|------:|------:|
| M0_baseline | -1.750*** (0.020) | — | — | +0.433*** (0.004) | 0.7473 |
| M1_with_cross | -1.731*** (0.020) | +0.647*** (0.017) | — | +0.427*** (0.004) | 0.7482 |
| M2_with_same_brand | -1.786*** (0.021) | +0.723*** (0.018) | +0.231*** (0.018) | +0.423*** (0.004) | 0.7484 |

Stars: * |t|>1.65, ** |t|>1.96, *** |t|>2.58. Cluster-robust SE in parentheses (clustered at brand-size-store).
- saved /Volumes/外接硬盘/webAPP/pricing/data/processed/cannibalization_model_coefficients.csv

## 4. Top-brand sub-samples (M3)
Re-fit M2 separately for the top brands by row count to check whether β_same is driven by one or two large brands.
- top 5 brands: ["Kellogg's", 'General Mills', 'Post', 'Quaker', 'Private Label']
  Kellogg's                  N= 915,108  β_own=-1.849(0.029)  β_same=+0.508(0.057)
  General Mills              N= 611,718  β_own=-1.266(0.089)  β_same=+0.204(0.043)
  Post                       N= 305,528  β_own=-2.411(0.041)  β_same=+0.493(0.116)
  Quaker                     N= 258,037  β_own=-2.018(0.040)  β_same=+0.454(0.067)
  Private Label              N= 187,976  β_own=-1.610(0.036)  β_same=-0.063(0.086)

## 5. Spillover-adjusted top-10 portfolio lift
- loaded top-10 portfolio recommendations (10 rows)
- using β_same = +0.2307 from M2_with_same_brand

### Top-10 candidates: focal lift vs. spillover-adjusted lift
| brand | size | store | focal Δπ | sisters | spillover | adjusted Δπ | Δ% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Kellogg's | 15.00 | 102 | $311 | 39 | $+9 | $321 | +3.0% |
| General Mills | 20.00 | 126 | $195 | 30 | $+3 | $199 | +1.7% |
| General Mills | 12.00 | 102 | $161 | 27 | $+3 | $164 | +1.7% |
| Kellogg's | 20.00 | 80 | $151 | 15 | $+1 | $152 | +1.0% |
| General Mills | 14.00 | 126 | $143 | 30 | $+3 | $147 | +2.4% |
| Kellogg's | 18.00 | 74 | $141 | 41 | $+5 | $147 | +3.7% |
| General Mills | 18.00 | 126 | $139 | 30 | $+3 | $142 | +2.4% |
| Kellogg's | 12.00 | 18 | $129 | 35 | $+3 | $132 | +2.6% |
| General Mills | 15.00 | 126 | $122 | 30 | $+3 | $125 | +2.5% |
| Post | 16.00 | 126 | $115 | 15 | $+5 | $120 | +4.0% |

**Median |adjustment| across top-10 = 2.5%; max = 4.0%.**

## 6. Decision rule outcome
**Limited first-order impact**: β_same is positive and significant but small in magnitude — top-10 adjustment is 2.5% (median, max 4.0%). Document the diagnostic; the MVP optimizer is fit-for-purpose without joint optimization.

## 7. Artifacts
- /Volumes/外接硬盘/webAPP/pricing/data/processed/cannibalization_diagnostics.parquet  (2,585,593 rows)
- /Volumes/外接硬盘/webAPP/pricing/reports/figures/cannibalization_coefficients.png
