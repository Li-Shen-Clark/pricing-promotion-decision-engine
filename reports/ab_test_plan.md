# A/B Test Plan — Pricing Decision Engine MVP
Generated: 2026-04-20T23:56:13  ·  source: `notebooks/05_ab_testing_design.ipynb`

## Purpose
Validate the raise-and-test candidates produced by `notebooks/04_counterfactual.ipynb`. The optimizer recommends candidate price increases for ~5,900 brand-size-store cells, but the same headline showed 98.5% bind at the upper guardrail. **No price change ships without controlled validation.**

## Design summary
| Element | Choice | Rationale |
|---|---|---|
| Randomization unit | store (or store-cluster) | DFF is store-week scanner data; offline retail prices are typically a store-level policy. *Online equivalent: user/session — see app wireframe.* |
| Primary metric | gross profit per store-week | direct revenue−cost reading; matches optimizer objective |
| Secondary metrics | units sold, revenue, observed price compliance | guardrails for stockout / margin erosion |
| Estimator | DiD with store FE, cluster SE at store | accounts for store-level baseline differences |
| α | 0.05 (two-sided) | standard |
| Power | 0.80 | standard MVP target; 0.90 used for high-stakes price increases |
| MDE | 50% of model-predicted profit lift | half the optimistic point estimate; still beats no-test status quo |

## Risk-tiered test types
| Risk tier | Test type | Stores per arm | Duration | Use when |
|---|---|---|---|---|
| **high**   | `single_store_flight`  | 1 + 1 matched control | 8 weeks | extrapolation past historical price band, large Q swings |
| **medium** | `cluster_rct`          | 5 vs 5                | 6 weeks | one risk flag, otherwise normal |
| **low**    | `standard_ab`          | 10 vs 10              | 4 weeks | clean candidate, within historical price band |

## Top-10 portfolio test plan
| brand | size | store | current → candidate | risk | test type | required n_storeweeks/arm | weeks/store | 
|---|---|---|---|---|---|---|---|
| Kellogg's | 15.00 | 102 | $3.02 → $4.30 | high | `single_store_flight` | 13 | 13.1 |
| General Mills | 20.00 | 126 | $4.02 → $5.16 | medium | `cluster_rct` | 3 | 0.6 |
| General Mills | 12.00 | 102 | $2.95 → $3.91 | high | `single_store_flight` | 11 | 11.1 |
| Kellogg's | 20.00 | 80 | $3.54 → $5.11 | high | `single_store_flight` | 7 | 7.7 |
| General Mills | 14.00 | 126 | $3.25 → $4.32 | high | `single_store_flight` | 21 | 21.9 |
| Kellogg's | 18.00 | 74 | $3.15 → $5.23 | high | `single_store_flight` | 35 | 35.1 |
| General Mills | 18.00 | 126 | $3.66 → $5.20 | high | `single_store_flight` | 5 | 5.5 |
| Kellogg's | 12.00 | 18 | $2.50 → $3.77 | high | `single_store_flight` | 14 | 14.7 |
| General Mills | 15.00 | 126 | $3.12 → $4.11 | high | `single_store_flight` | 99 | 99.4 |
| Post | 16.00 | 126 | $2.85 → $4.05 | high | `single_store_flight` | 12 | 12.7 |

## Sample size formula
Two-sample equal-variance t-test:
$$ n_{\text{per arm}} = \frac{2(z_{1-\alpha/2} + z_{1-\beta})^2 \sigma^2}{\delta^2} $$
where σ = historical weekly profit std for the cell, δ = MDE in dollars/store-week.

## Guardrails (stop-test triggers)
1. Treatment-arm units sold drops by > 40% vs control over rolling 2-week window → pause test
2. Treatment-arm gross revenue drops > 20% vs control → pause test (margin floor breach risk)
3. Observed treatment-store price compliance < 80% → re-instruct stores; if persists, drop arm
4. Customer complaint proxy unavailable in DFF — flagged as future ingestion target

## Rollout sequencing
Run tests in waves to avoid same-store interference:
1. **Wave 1 (weeks 1–8)**: all `single_store_flight` candidates (high risk) — limits downside
2. **Wave 2 (weeks 9–14)**: all `cluster_rct` candidates (medium risk)
3. **Wave 3 (weeks 15–18)**: all `standard_ab` candidates (low risk) — should be empty for MVP top-10
After each wave, re-estimate elasticity on the new data and refresh the candidate list.

## What this test does NOT validate
1. Cross-store substitution (customers driving to a control store)
2. Cross-brand cannibalization (planned for `06_portfolio_pricing_extension.ipynb`)
3. Long-horizon price-image effects (>6 months)
4. Competitor reaction (rivals see your shelf price too)