"""Page 5 — Limitations: what this MVP does NOT validate, and what comes next."""
from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import read_markdown, REPORTS

st.set_page_config(page_title='Limitations', page_icon='🚧', layout='wide')

st.title('Limitations & Roadmap')

st.error(
    '**Final positioning.** Optimizer output is a list of **candidate actions for '
    'experimentation, not production deployment.** No price change ships without an A/B test.'
)

st.warning(
    '**Upper-guardrail diagnostic.** 98.5% of eligible cells bind at the upper price '
    'guardrail. This is not evidence that the optimizer is production-ready; it is a '
    'diagnostic consequence of constant-elasticity demand plus the AAC-derived cost proxy. '
    'With ε≈-1.73, the implied unconstrained Lerner margin is about 58%, so these rows are '
    '**raise-and-test candidates**, not automatic price changes.'
)

st.markdown('### Six things this MVP does NOT do')
st.markdown(
    """
1. **Causal identification.** The demand model uses brand-size-store and week fixed effects
   but no instrumental variables. Own price, competitor price, and promotion status are
   observational choices, not random treatment assignments. **Diagnosed in `08_iv_sensitivity.ipynb`**:
   Hausman-style leave-one-out other-store price IV (Z_H) + leave-one-out other-store cost
   IV (Z_C; own-cell cost is mechanically tied to own price via DFF's PROFIT field, so
   cannot be used). On a common sample of 2.59M rows, β_own moves from OLS −1.728 →
   store-week-FE OLS −1.805 → Hausman IV −1.781 → over-ID IV −1.780 — |Δβ(IV − OLS)| / |β_OLS|
   = 3.0%, first-stage F ≫ 10, same sign, CI width ratio 1.08. All four decision-rule
   conditions clear → **Robust OLS**. **Same-chain caveat**: DFF is a single chain in a
   single metro, so Z_H still absorbs chain-wide promo calendars and Chicago-local demand
   shocks. The IV is a **sensitivity bound, not definitive causal identification** — true
   causal estimation requires multi-chain, multi-metro data. See the IV sensitivity tab below.

2. **Promotion as clean treatment effect.** θ_promo is a conditional sale-code coefficient in log
   points, not a clean causal promotion effect. A coefficient of 0.43 implies
   `exp(0.43)-1 ≈ 54%` conditional demand difference under the model, but that may include
   promo targeting, vendor funding, inventory pressure, and stockpiling.

3. **Competitor reaction.** Cross-price coefficient captures historical co-movement, not a
   game-theoretic response. The simulator lets you shock rivals' prices ±15% as a what-if,
   but it does not solve a Nash equilibrium. Planned for `08_competitor_response.ipynb`.

4. **Within-brand cannibalization across package sizes.** Raising the 18oz price shifts
   some demand to the 12oz of the same brand. **Diagnosed in `07_cannibalization_robustness.ipynb`**:
   β_same = +0.231*** (significant), but the implied **median spillover adjustment to top-10
   portfolio lifts is +2.5% (max +4.0%)** — direction-positive (raising one size sends a small
   amount of demand to sister sizes, which adds profit at sister-size margins) and well below
   the 10–15% band that would warrant rebuilding the optimizer with a joint objective. The
   per-cell optimizer is kept; this is a quantitatively bounded caveat, not an open hole.
   See the **Cannibalization diagnostic** tab below for the full table.

5. **Inventory feasibility.** Large predicted Q lifts assume restock capacity. The MVP flags
   `q_lift_ratio` per cell but does not enforce a stockout constraint. Production needs a
   live inventory feed and a real stop-test guardrail (the 40% units-drop heuristic in
   `ab_test_plan.md` is a placeholder).

6. **Marginal cost ≠ AAC.** `unit_cost` derives from DFF's average acquisition cost (PROFIT
   field), which lags true replacement cost. Profit numbers are directionally useful, not
   accounting-grade. Production should plug in real cost-of-goods.
"""
)

st.markdown('### Roadmap')
st.markdown(
    """
| Notebook | Adds | Why |
|---|---|---|
| `06_streamlit_mvp.app` (this) | App wrapper for the existing pipeline | Closes the MVP loop |
| `07_cannibalization_robustness.ipynb` ✅ | Same-brand cross-size diagnostic + ex-post spillover adjustment | **Done** — β_same significant but small; top-10 lifts move <5%, optimizer stays per-cell |
| `08_iv_sensitivity.ipynb` ✅ | Hausman-style other-store IV + store-week FE robustness | **Done** — OLS β_own robust within 3% (|Δβ|/|β_OLS| = 3.0%, F≫10, same sign, CI ratio 1.08); same-chain caveat flagged |
| `09_competitor_response.ipynb` | Best-response model for rival prices | Closes the simultaneity gap |
| `10_dynamic_demand.ipynb` | Stockpiling / lead-lag promo effects | Better short-horizon predictions |
"""
)

st.markdown('---')
st.subheader('Source documents')
tabs = st.tabs(['Case study (top candidate end-to-end)',
                'Counterfactual summary', 'Demand model summary',
                'A/B test plan', 'Cannibalization diagnostic',
                'IV sensitivity'])
with tabs[0]:
    st.markdown(read_markdown(REPORTS / 'case_study.md'))
with tabs[1]:
    st.markdown(read_markdown(REPORTS / 'counterfactual_summary.md'))
with tabs[2]:
    st.markdown(read_markdown(REPORTS / 'demand_model_summary.md'))
with tabs[3]:
    st.markdown(read_markdown(REPORTS / 'ab_test_plan.md'))
with tabs[4]:
    st.markdown(read_markdown(REPORTS / 'cannibalization_robustness_summary.md'))
with tabs[5]:
    st.markdown(read_markdown(REPORTS / 'iv_sensitivity_summary.md'))
