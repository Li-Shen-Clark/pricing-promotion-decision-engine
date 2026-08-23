# Pricing & Promotion Decision Engine — Streamlit MVP Wireframe
Generated: 2026-04-20T23:56:13  ·  source: `notebooks/05_ab_testing_design.ipynb`

## Stack
- `streamlit ≥ 1.30`, `pandas`, `pyarrow`, `plotly`, `altair`
- All data read from `data/processed/*.parquet` and `*.csv` — no live DB
- Sidebar: project name, model version (FROZEN block from `demand_model_summary.md`), date stamp

---

## Page 1 — Executive Summary
**Audience**: VP / decision approver.
- KPI tiles: total eligible cells, total predicted weekly profit lift across portfolio, # of high-risk candidates, top-3 portfolio brand-size-store cards
- One-line headline: "98.5% of recommendations are raise-and-test candidates; no price changes ship without controlled validation."
- Link buttons → other pages
- Inputs: `top_recommendations_diverse.csv`, `cell_baselines.parquet`, `reports/counterfactual_summary.md` (rendered)

## Page 2 — Model Evidence (`/Evidence`)
**Audience**: data scientist peer.
- Show frozen coefficients table from `model_coefficients.csv`
- Holdout fit panel (RMSE, median APE) — be explicit it is a no-IV baseline
- Brand-level price elasticity bar chart (own + cross + promo)
- Markdown rendering of `reports/demand_model_summary.md` FROZEN block
- Inputs: `model_coefficients.csv`, `demand_model_summary.md`, `figures/demand_*.png`

## Page 3 — What-If Simulator (`/Simulate`)
**Audience**: pricing analyst exploring "what if".
- Selectors: brand_final, size_oz_rounded, STORE → loads cell baseline
- Slider: candidate price (bounded by `[0.85·p_min, 1.15·p_max]`, with margin floor 1.05·cost_eff)
- Toggle: promo on/off
- Live plot: predicted Q vs price (curve), profit vs price (curve), with baseline marker
- Sensitivity sidebar: β_own ∈ {-1.90, -1.73, -1.50}, β_cross ∈ {0, 0.5, 0.65}, promo θ ∈ {0.30, 0.43, 0.51} → re-render curves
- **Scenario controls** (sidebar): demand shock (±30%), cost shock (-25 to +40%), competitor price shock (±25%), inventory cap, promo fixed cost. Defaults inert; non-zero values trigger live recomputation and risk-flag banners. See "Scenario overlay" module below.
- Inputs: `cell_baselines.parquet`, `model_coefficients.csv`

## Page 4 — Candidate Finder (`/Optimize`)
**Audience**: pricing analyst building a candidate list.
- Filter widget: brand, size range, store, current_promo, min n_weeks
- Table: filtered slice of `all_recommendations.csv` with sortable Δprofit and risk columns
- "Add to experiment basket" button → writes selected rows to a session basket
- Bar chart: top-N current view by predicted Δprofit
- **Scenario controls** (sidebar): same shocks as the simulator. Non-baseline values trigger a live vectorised re-optimization across all eligible cells (`optimize_all_cells`), so the candidate ranking, candidate prices, and lift columns all reflect the active scenario.
- Inputs: `all_recommendations.csv`, `cell_baselines.parquet`

## Page 5 — Test Planner (`/Validate`)
**Audience**: same analyst, now planning the test.
- Render `experiment_candidates.csv` as interactive table; per-row expand shows: σ, MDE, required n_storeweeks, recommended test type, planned duration, flagged risks
- Sample size widget: input σ + δ + α + power → output n per arm + n_storeweeks total + reuse the §6 curve
- Render `reports/ab_test_plan.md` as a tab
- "Export experiment basket" button → CSV download with the test plan rows for ops handoff
- Inputs: `experiment_candidates.csv`, `figures/ab_sample_size_curve.png`, `ab_test_plan.md`

## Page 6 — Trust & Boundaries (`/Boundaries`)
**Audience**: anyone who is about to use the recommendations.
- Render `reports/counterfactual_summary.md` "Limitations" section + 03 limitations list
- Banner: "These are candidate actions for experimentation, not production deployment."
- Diagnostic banner: "98.5% upper-guardrail binding is a warning from the constant-elasticity model and AAC cost proxy, not proof that prices should be deployed."
- Coefficient note: `theta_promo` is a conditional sale-code effect in log points; percent display uses `exp(theta)-1` and is not a clean causal promotion effect.
- Roadmap callout: cannibalization (06), competitor response (07), causal IV (08)
- Inputs: `counterfactual_summary.md`, `demand_model_summary.md`

## Page 7 — Upload & Score (`/Upload`)
**Audience**: prospective external user with their own pricing dataset.

Flow: **template → upload → validate → score → scenario overlay → download**.

- **Scope guardrail (banner)**: scoring-only — uploaded data are evaluated against the frozen Dominick's cereal coefficients (`MAIN_COEFS`). Re-estimation on user-specific panels is explicitly out of MVP scope.
- **Template** (`src.upload.template_csv`): downloadable CSV with 4 example rows covering the required + optional schema.
- **Required columns**: `product_id`, `store_id`, `quantity`, `price`, `unit_cost`, `promo`, `competitor_price`. **Optional**: `brand`, `size_oz`, `inventory`.
- **Synonym mapping** (`COLUMN_SYNONYMS`): tolerant standardization, e.g. `qty`→`quantity`, `sku`→`product_id`, `cogs`→`unit_cost`, `p_comp`→`competitor_price`.
- **Validation** (`src.upload.validate`): MUST pass before scoring. Blocking errors: empty file, missing required column, all-row drop after coercion. Non-blocking warnings: NaN-row drop, range violations (`qty≤0`, `price≤0`, `cost≤0`, `comp_price≤0`, `promo ∉ {0,1}`), negative-margin rows, promo share > 80%, extreme price-vs-comp ratios.
- **Cap**: 50,000 rows.
- **Scoring** (`src.upload.score`): per-row cell-anchored prediction using the row itself as the anchor (`mean_q` = uploaded `quantity`, `mean_p` = uploaded `price`, etc.). No global aggregation, no model re-fit.
- **Action widget**: uniform `price_multiplier` (±30%) and `promo_action ∈ {keep, on, off}` applied to every row.
- **Scenario overlay** (sidebar): same `Scenario` controls as Pages 3 & 4 — defaults inert, non-zero values flow through `score()` via the existing `apply_demand_overlay` / `effective_cost` / `compute_profit` helpers.
- **Outputs**: portfolio KPIs (predicted units / revenue / profit, vs. observed AND vs. do-nothing-under-scenario), per-row table, downloadable scored CSV.
- **Inputs**: user upload only. No project artifacts read.

---

## Scenario overlay (cross-page module)

Implemented in `src/scenario.py` as a frozen `Scenario` dataclass with five inert defaults:

| Field                  | Range (UI)        | Effect                                                       |
|------------------------|-------------------|--------------------------------------------------------------|
| `demand_shock`         | -30% to +30%      | Multiplies predicted Q after the model: `Q ← Q × (1+shock)`  |
| `cost_shock`           | -25% to +40%      | Multiplies unit cost: `c ← c × (1+shock)`. Moves margin floor.|
| `competitor_price_shock` | -25% to +25%    | Feeds `log(1+shock)` into β_cross.                            |
| `inventory_cap`        | optional, units/wk | Hard ceiling: `Q_sold = min(Q, cap)`                         |
| `promo_fixed_cost`     | $/wk              | Deducted from profit when promo = 1.                          |

**Invariance contract.** `Scenario()` (the BASELINE singleton) produces numerically identical results to the offline notebook. Any non-zero shock triggers a re-computation and surfaces a risk-flag banner (e.g. "Demand shock outside ±20%: stress-test only").

**Propagation.** The same `Scenario` instance flows from the sidebar through `predict_q` (for cross-price) and `optimize_cell` / `evaluate_curve` / `optimize_all_cells` (for everything else), so the simulator and optimizer always agree.

## Online translation note (for SaaS pricing)
In a SaaS / e-commerce setting, the randomization unit shifts from `store` to `user / session`. The same design pattern applies: define a primary economic metric, compute σ from historical user-week spend, and size the test the same way. The DFF MVP uses store-level rollout because it matches the underlying scanner-panel structure; replacing the unit and the σ source is the only change needed.

## Build sequence
1. `app.py` (explicit navigation)
2. `views/0_Overview.py`
3. `views/1_Evidence.py`
4. `views/2_Simulate.py`  ← shared `predict_q` helper imported from `src/`
5. `views/3_Optimize.py`
6. `views/4_Validate.py`
7. `views/5_Boundaries.py`
8. Deploy: `streamlit run app.py` locally → free-tier Streamlit Cloud for portfolio link
