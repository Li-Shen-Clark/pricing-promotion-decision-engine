# IV Sensitivity Summary
Generated: 2026-04-21

This notebook tests whether the baseline OLS own-price elasticity is robust to Hausman-style other-store price instruments and stricter store-week fixed effects. Because DFF is a single-chain, single-metro scanner panel, the IV estimates are interpreted as **sensitivity checks rather than definitive causal estimates**.

**Headline.** β_own moves from OLS -1.728 → store-week-FE OLS -1.805 → Hausman IV -1.781 → Hausman + cost IV -1.780. |Δβ(IV − OLS)| / |β_OLS| = 3.0%, first-stage F ≫ 10, same sign = True, CI width ratio 1.08.

**Decision — Robust OLS.** IV β_own is within 15% of OLS, same sign, first-stage F well above 10, and the 95% CI is not explosively wide. The OLS headline estimate (β_own = −1.73) is the preferred working number for the MVP. Trust & Boundaries page item 1 is softened from "planned" to "tested within this sample's identification limits".

---

## Same-chain caveat (prominent)

The Hausman-style instrument averages prices over **other Dominick's stores within the Chicago metro area**. It does not break:

- Chain-wide promotional calendars (weekly circular, end-cap programs)
- Manufacturer funding windows (vendor allowances applied uniformly across stores)
- Chicago-local demand shocks (weather, local employment, school calendars)

The IV estimate therefore still carries same-chain / same-market contamination risk — it is a diagnostic, not a definitive causal estimate. Multi-chain, multi-metro IV with truly exogenous variation (e.g. wholesale cost shifters from a different chain's data) is out of scope for this MVP.

## Cost IV choice

We use *leave-one-out other-store* log_unit_cost (Z_C), **not** the own cell's log_unit_cost. DFF derives `unit_cost = price · (1 − PROFIT/100)`, so the own-cell cost is mechanically linked to the own-cell price and would violate the IV exclusion restriction. The leave-one-out variant breaks the within-cell mechanical link; the residual concern is chain-wide wholesale pricing, flagged above.

## First-stage instrument decomposition

Z_H ~ promo_any_int has partial R² = 0.18 (moderate). The instrument carries mostly cross-store variation that is not promo-driven, which is the result you want; a high value (>0.5) would have flagged that Z_H is essentially a promo dummy in disguise.

---

## Specifications & coefficients

| Spec | FE | Estimator | β_own | SE | N | First-stage F |
|------|----|-----------|------:|---:|---:|---:|
| M0  | bs_store + week | OLS | **−1.728** | 0.020 | 2,585,060 | — |
| M0b | bs_store + **store×week** | OLS | **−1.805** | 0.020 | 2,585,060 | — |
| M1  | bs_store + week | IV (Z_H) | **−1.781** | 0.021 | 2,585,060 | 1.6 × 10⁷ |
| M2  | bs_store + week | IV (Z_H, Z_C) over-ID | **−1.780** | 0.021 | 2,585,060 | 7.8 × 10⁶ |

All specs on the **common IV sample** (N=2,585,060; 99.98% of panel). SEs are cluster-robust at the brand-size-store level; store-week clustering gave virtually identical results (sensitivity fallback, since IV2SLS supports only one-way clustering).

### Hausman OLS vs IV (β only)
χ² = 43.23 on 1 df, p < 0.001. Statistically rejects β_OLS = β_IV, but the **magnitude** of the difference (0.05 in β, 3% relative) is economically small — a large-N significance artefact.

### Over-ID (Sargan J) on M2
J = 5968 on 1 df, p < 0.001. Rejects; reported transparently. Interpretation: Z_H and Z_C over-identify β_own differently at very large N (the mechanical near-collinearity means tiny coefficient differences dominate). Rejection of over-ID is itself a same-chain diagnostic — both instruments are correlated with the chain-wide promotional calendar, which shows up as a J-rejection even though each instrument in isolation clears the relevance bar.

## Heterogeneity by brand (top 5 by volume)

| Brand | N | β_IV | SE |
|---|---:|---:|---:|
| Kellogg's | 914,951 | −1.95 | 0.03 |
| General Mills | 611,718 | −1.25 | 0.10 |
| Post | 305,499 | −2.55 | 0.04 |
| Quaker | 257,918 | −2.11 | 0.04 |
| Private Label | 190,392 | −1.66 | 0.04 |

All same-sign with the pooled estimate; magnitudes span a factor of ≈2. The pooled β_own = −1.73 used in the optimizer is a **volume-weighted average** over heterogeneous per-brand elasticities — the optimizer's per-cell recommendations apply the pooled coefficient, so per-brand dispersion is a second-order modelling choice (noted as a future refinement, not a blocker).

## Why "Robust OLS" and not a switch to IV

All four decision-rule conditions clear:

1. **|Δβ|/|β_OLS| = 3.0%** — well under the 15% threshold for "meaningful change".
2. **First-stage F ≫ 10** — no weak-instrument concern at the relevance margin.
3. **Same sign** — no reversal of the elasticity direction.
4. **CI ratio = 1.08** — IV is only 8% wider than OLS, i.e. not a noisy null.

The economically appropriate reading is that own-price OLS in this sample is not meaningfully contaminated by simultaneity against cross-store pricing variation. **Keep the OLS β_own headline; flag the same-chain / same-metro external-validity limit.**

---

## Artifacts

- `data/processed/iv_sensitivity_coefficients.csv` — M0/M0b/M1/M2 coefficient table
- `data/processed/iv_first_stage_diagnostics.csv` — partial R², F, q for each spec + Z_H ~ promo decomposition
- `reports/figures/iv_sensitivity_coefficients.png` — forest plot across specs
- `reports/figures/iv_first_stage_decomposition.png` — instrument-variance decomposition
- `notebooks/08_iv_sensitivity.ipynb` — executable notebook
