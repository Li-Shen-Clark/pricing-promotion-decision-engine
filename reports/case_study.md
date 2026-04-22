# Case Study — Top Candidate End-to-End

**Pricing & Promotion Decision Engine MVP** · Dominick's Finer Foods Cereals

This walks one named candidate through the full pipeline — data → demand model → optimizer → experiment design → limitations — using the actual numbers shipped with the app. The goal is to make the workflow concrete and to expose what the model trusts, what it doesn't, and what decision the data actually supports.

---

## 1. The candidate at a glance

| Field | Value |
|---|---|
| Brand | **Kellogg's** |
| Package size | **15 oz** |
| Store | **#102** |
| History | **357 weeks** (1989–1996, full panel) |
| Current avg price | **\$3.03** |
| Current avg unit cost (AAC proxy) | **\$2.55** |
| Current realised margin | **16%** |
| Current promo share | **33%** of weeks on sale |
| Avg baseline quantity | **392 units/wk** |
| Avg baseline profit | **\$187/wk** |

This is the **top-ranked candidate** in [`top_recommendations_diverse.csv`](../data/processed/top_recommendations_diverse.csv) and the first row on the app's Executive Summary page.

---

## 2. What the model says

Under the frozen `baseline_with_cross` demand model:

- β_own (own-price elasticity) = **−1.73**
- β_cross (competitor price index) = **+0.64**
- θ_promo (sale-code coefficient, log) = **+0.43**, i.e. promo weeks see roughly `exp(0.43) − 1 ≈ 54%` higher conditional demand at the same price
- Cell-anchored prediction: at any (price, promo), `Q̂ = mean_q · exp[β_own · Δlog p + θ · Δm + β_cross · Δlog p_comp]`

Holding competitor prices fixed and optimising over the bounded grid `[max(p_min·0.85, c·1.05), p_max·1.15]`:

| | Current | Candidate (model) | Δ |
|---|---|---|---|
| Price | \$3.03 | **\$4.30** | **+42%** |
| Promo | 33% of weeks | **always on** | promo flag flips to 1 |
| Quantity (model) | 392 / wk | **284 / wk** | −28% |
| **Profit (model)** | **\$187 / wk** | **\$498 / wk** | **+\$311 / wk (+167%)** |

The optimizer **binds at the upper price guardrail** (`opt_hits_upper = True`). This is the central caveat — see §6.

---

## 3. What the price-profit curve looks like

The cell's profit is monotonically increasing in price across the entire grid up to the guardrail:

- At the lower boundary (`max($1.37, $2.68) ≈ $2.68`) profit ≈ \$50
- At the current price (\$3.03) with current promo state, profit ≈ \$187
- At the candidate price (\$4.30) with promo on, profit ≈ \$498
- The curve is concave only because the upper guardrail truncates it; the unconstrained constant-elasticity optimum would be even higher.

Geometrically: with β = −1.73 and AAC cost \$2.55, the unconstrained optimal markup is Lerner = 1/|β| ≈ 58%, which gives p\* ≈ \$6.07 — well outside the historical range. The guardrail is doing the regularisation that the model's functional form alone won't.

---

## 4. Cannibalization check (notebook 07)

Kellogg's 15oz at Store 102 has **39 sister sizes** of the same brand on the same shelf. Notebook 07 computed the model-implied substitution back into those sister sizes when the focal price moves from \$3.03 to \$4.30:

| | Value |
|---|---|
| β_same (own-brand cross-size coefficient) | +0.231\*\*\* |
| Implied weekly profit shifted to sister sizes | **+\$9 / wk** |
| Direction | profit-positive (sister-size customers buy at higher margins) |
| Adjusted lift | \$311 → **\$321 / wk** (+3.0%) |

The cannibalization correction is **directionally favourable and quantitatively small**. The MVP optimizer does not rebuild around joint optimisation, but the diagnostic is shipped in [`reports/cannibalization_robustness_summary.md`](cannibalization_robustness_summary.md).

---

## 5. The experiment design

We do not deploy this price change. We test it. From [`experiment_candidates.csv`](../data/processed/experiment_candidates.csv) and the Test Planner page (`/Validate`):

| Field | Value |
|---|---|
| Historical profit σ at this cell | **\$142 / wk** |
| Required minimum detectable effect (50% of baseline lift) | **\$156 / wk** |
| Sample size (per arm, 80% power, α = 0.05) | **13 store-weeks** |
| Planned design | **single-store flight, 8 weeks** |
| Underpowered? | **yes** (8 < 13) |
| Risk flag | **high** (extrapolation + 42% price jump) |

**Translation.** Even at a generous 50% MDE, the planned 8-week single-store flight is below the 13-store-week threshold needed to detect the effect at 80% power. Three options:

1. **Extend the flight to 13–15 weeks** at the same store — straightforward, no design change.
2. **Use a paired-control design** (a matched store as control), which lowers the effective σ via within-pair variance reduction.
3. **Accept a larger MDE** — if the test is designed to detect "at least \$200 / wk", 8 weeks at one store is adequate. The trade-off is that a real \$160 / wk lift would be missed.

The app surfaces this trilemma directly on the Test Planner page; nothing about the candidate gets shipped without resolving it.

---

## 6. Why we don't simply deploy

Six concrete reasons, each one of which the app surfaces on the Trust & Boundaries page (`/Boundaries`):

1. **Extrapolation.** The candidate price \$4.30 is +13.6% above the historical max for this cell. The constant-elasticity functional form has no ceiling, but that doesn't mean real-world demand doesn't.
2. **Cost proxy ≠ marginal cost.** AAC is an accounting average, not the true replacement cost. If the real marginal cost is even \$0.30 higher than AAC, the lift estimate falls by ~\$50 / wk.
3. **Promo recommendation is conditional, not causal.** θ = +0.43 captures the historical sale-code coefficient, which mixes vendor funding, inventory pulls, and stockpiling. "Always on" is a within-model recommendation; it's not a behavioural prediction about a permanent everyday-low-price strategy.
4. **No competitor reaction.** β_cross fits historical co-movement, not a Nash response. If competing brands match a +42% price increase, the cross-price benefit evaporates.
5. **Inventory feasibility.** The model predicts 284 units/wk under the candidate; we have not verified Store 102 can restock at that level under the new promo cadence.
6. **Cannibalization is bounded but real.** β_same > 0 means a portion of the modelled profit gain is sister-size customers shifting up — the corrected lift is +\$321 / wk, not +\$311 / wk. (Effect is small at this cell; could be larger in lower-SKU-density categories.)

The model is a **search heuristic over a hypothesis space**. The hypothesis "Kellogg's 15oz at Store 102 is currently underpriced relative to its own historical elasticity" deserves a controlled test. It does not deserve a memo to the buyer.

---

## 7. The narrative the app supports

What this MVP allows a pricing analyst to do, end-to-end, in roughly five minutes:

1. **Open the app**, see the headline: 98.5% of eligible cells bind at the upper guardrail (a *diagnostic*, not a green light).
2. **Inspect a candidate** on Page 3, drill into its profit-price curve, see the risk flags fire.
3. **Stress-test the candidate** on Page 2 under demand / cost / competitor / inventory shocks, see how robust the recommendation is.
4. **Cross-check the cannibalization risk** on Page 5, see the diagnosed +3% bound.
5. **Plan the experiment** on Page 4, see whether the proposed flight is powered.
6. **Walk away with one of three decisions**: extend the test, accept a larger MDE, or downgrade the candidate to "not worth testing".

What it does NOT do:
- Set prices automatically.
- Issue a recommendation memo.
- Replace the buyer's category knowledge.

That is the intended scope, and the test plan is the part that matters most. The optimizer is a search tool over the candidate space; the experiment is what turns a candidate into a decision.

---

## 8. Provenance

| Artifact | Source |
|---|---|
| Demand coefficients | [`data/processed/model_coefficients.csv`](../data/processed/model_coefficients.csv) (notebook 03) |
| Cell baselines | [`data/processed/cell_baselines.parquet`](../data/processed/cell_baselines.parquet) (notebook 04) |
| Top-10 portfolio | [`data/processed/top_recommendations_diverse.csv`](../data/processed/top_recommendations_diverse.csv) (notebook 04) |
| Experiment plan | [`data/processed/experiment_candidates.csv`](../data/processed/experiment_candidates.csv) (notebook 05) |
| Cannibalization | [`reports/cannibalization_robustness_summary.md`](cannibalization_robustness_summary.md) (notebook 07) |
| Methodology | [`docs/methodology.md`](../docs/methodology.md) / [`.tex`](../docs/methodology.tex) |

All numbers in this document are reproducible from a fresh checkout via the notebooks listed, then `streamlit run app.py`.
