"""Page 6 — Trust & Boundaries: what this MVP does NOT validate, and what comes next."""
from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import read_markdown, REPORTS, MAIN_COEFS
from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(page_title='Trust & Boundaries', page_icon='🧭', layout='wide')
apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag="Decision support · Dominick's cereals",
    badges=[
        ('β_own',   f"{MAIN_COEFS['beta_own']:.2f}"),
        ('β_cross', f"+{MAIN_COEFS['beta_cross']:.2f}"),
        ('θ',       f"+{MAIN_COEFS['theta_promo']:.2f}"),
    ],
    workflow=[
        (1, 'Overview',   False),
        (2, 'Evidence',   False),
        (3, 'Simulate',   False),
        (4, 'Optimize',   False),
        (5, 'Validate',   False),
        (6, 'Boundaries', True),
        (7, 'Upload',     False),
    ],
)

page_intro(
    icon='🧭',
    kicker='Workflow · Step 6 · When should I NOT trust this?',
    title='Trust & Boundaries',
    tagline=(
        'What this MVP is designed to do — and what it deliberately does not claim.'
    ),
    chips=[
        'Scope: decision support',
        'Validation: A/B required',
        'Robustness: IV-tested',
        'Roadmap to causal',
    ],
)

insight_row([
    Insight(
        label='Scope',
        headline='Candidate actions, not deployments',
        detail=('Optimizer output is a ranked list of raise-and-test candidates. '
                'No price change ships without a controlled experiment from the '
                'Test Planner.'),
        tone='brand',
    ),
    Insight(
        label='Guardrail diagnostic',
        headline='98.5% cells bind at the upper guardrail',
        detail=('Constant-elasticity demand with ε≈-1.73 and AAC cost proxy imply '
                'Lerner margin ≈ 58%; the upper bound is where the model wants to go. '
                'Read rows as raise-and-test candidates.'),
        tone='warn',
    ),
    Insight(
        label='Identification',
        headline='Robust OLS — IV moves β_own by 3.0%',
        detail=('Hausman + over-ID IV preserve sign and move β_own by 3.0%; '
                'store-week FE moves it by 4.5%. Same-chain caveat flagged; '
                'true causal identification needs multi-chain, multi-metro data.'),
        tone='ok',
    ),
])

section_header('Six things this MVP does NOT do',
               caption='Each item is a deliberate scope choice, not an unknown failure mode.')
st.markdown(
    """
1. **Causal identification.** The demand model uses brand-size-store and week fixed effects
   but no instrumental variables. Own price, competitor price, and promotion status are
   observational choices, not random treatment assignments. **Diagnosed in `08_iv_sensitivity.ipynb`**:
   Hausman-style leave-one-out other-store price IV (Z_H) + leave-one-out other-store cost
   IV (Z_C; own-cell cost is mechanically tied to own price via DFF's PROFIT field, so
   cannot be used). On a common sample of 2.59M rows, β_own moves from OLS −1.728
   to store-week-FE OLS −1.805, Hausman IV −1.781, and over-ID IV −1.780.
   The IV-vs-OLS relative difference is 3.0%; the store-week-FE-vs-OLS difference is
   4.5%. First-stage F ≫ 10, same sign, CI width ratio 1.08. All four decision-rule
   conditions clear → **Robust OLS**. **Same-chain caveat**: DFF is a single chain in a
   single metro, so Z_H still absorbs chain-wide promo calendars and Chicago-local demand
   shocks. The IV is a **sensitivity bound, not definitive causal identification** — true
   causal estimation requires multi-chain, multi-metro data. See the IV sensitivity tab below.

2. **Promotion as clean treatment effect.** θ_promo is a conditional sale-code coefficient in log
   points, not a clean causal promotion effect. A coefficient of 0.43 implies
   `exp(0.43)-1 ≈ 54%` conditional demand difference under the model, but that may include
   promo targeting, vendor funding, inventory pressure, and stockpiling.

3. **Competitor reaction.** Cross-price coefficient captures historical co-movement, not a
   game-theoretic response. The simulator lets you shock rivals' prices ±25% as a what-if,
   but it does not solve a Nash equilibrium. Planned for `09_competitor_response.ipynb`.

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

section_header('Roadmap',
               caption='Shipped ✅ means the notebook exists and its findings feed the app.')
st.markdown(
    """
| Notebook | Adds | Why |
|---|---|---|
| `07_cannibalization_robustness.ipynb` ✅ | Same-brand cross-size diagnostic + ex-post spillover adjustment | **Done** — β_same significant but small; top-10 lifts move <5%, optimizer stays per-cell |
| `08_iv_sensitivity.ipynb` ✅ | Hausman-style other-store IV + store-week FE robustness | **Done** — OLS β_own robust within 3% (|Δβ|/|β_OLS| = 3.0%, F≫10, same sign, CI ratio 1.08); same-chain caveat flagged |
| `09_competitor_response.ipynb` | Best-response model for rival prices | Closes the simultaneity gap |
| `10_dynamic_demand.ipynb` | Stockpiling / lead-lag promo effects | Better short-horizon predictions |
"""
)

section_header('Source documents',
               caption='The reports below are what a reviewer would read to check the claims above.')
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
