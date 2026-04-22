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
    tag='Decision support for cereal pricing',
)

page_intro(
    icon='🧭',
    kicker='When should I NOT trust this?',
    title='Trust & Boundaries',
    tagline=(
        'What this MVP is designed to do — and what it deliberately does not claim.'
    ),
    chips=[
        'Decision support, not deployment',
        'A/B required before any rollout',
        'Robustness checked, identification limited',
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
        label='Optimizer signal',
        headline='98.5% of candidates want the upper price band',
        detail=('Given the estimated price sensitivity and the cost proxy, the '
                'model almost always recommends raising price up to the historical '
                'maximum. That is a test-prioritization signal, not a deployment '
                'instruction.'),
        tone='warn',
    ),
    Insight(
        label='Identification',
        headline='Headline holds within ±5% under stricter checks',
        detail=('Two stricter identification approaches (instrumental variables '
                'and store-week effects) preserve the direction and shift the '
                'price-sensitivity number by 3.0% and 4.5% respectively. '
                'Same-chain caveat flagged.'),
        tone='ok',
    ),
])

section_header('Six things this MVP does NOT do',
               caption='Each row is a deliberate scope choice, not an unknown failure mode. '
                       'Open the expander below for the technical detail behind each row.')

st.markdown(
    """
| Risk | What we checked | What you should do |
|---|---|---|
| **Cause vs correlation.** Prices and promotions in the data were chosen, not randomly assigned. | We re-ran the model with stricter controls and instrumental-variable methods; price-sensitivity moved by ≤4.5%, same direction. | Treat candidates as test prioritization; confirm with an A/B before deployment. |
| **Promo lift is not a clean causal effect.** Sale weeks coincide with vendor funding and inventory pushes. | The "+54% on promo" figure is an in-sample association, not a causal estimate. | Don't quote the +54% as a forecast for "if we run more promos"; size promo bets via the Test Planner. |
| **Competitors don't react.** The model treats rival prices as fixed. | The What-If Simulator lets you stress-test ±25% rival moves; we don't solve a Nash response. | If the test category has known reactive competitors, shorten the test or watch competitor moves. |
| **Cross-size cannibalization.** Raising a 15oz price can shift sales to the 12oz of the same brand. | We measured the spillover: median +2.5%, max +4.0% on top-10 lifts — small enough that the per-product optimizer is kept. | Treat reported lifts as accurate within ±5%; for portfolio-wide moves, reassess. |
| **Inventory limits.** Large predicted unit increases assume restock capacity. | The app flags large quantity shifts but does not enforce a stockout constraint. | Confirm restock feasibility with operations before any large up-volume test. |
| **Cost is an accounting average, not true marginal cost.** | Profit numbers use the dataset's acquisition-cost proxy. | Treat absolute profit numbers as directional; in production, plug in real cost-of-goods. |
"""
)

with st.expander('Technical detail — what each row means in model language', expanded=False):
    st.markdown(
        """
1. **Causal identification.** The demand model uses brand-size-store and week fixed effects
   but no instrumental variables in the headline run. **Diagnosed in `08_iv_sensitivity.ipynb`**:
   Hausman-style leave-one-out other-store price IV (Z_H) + leave-one-out other-store cost
   IV (Z_C; own-cell cost is mechanically tied to own price via DFF's PROFIT field, so
   cannot be used). On a common sample of 2.59M rows, β_own moves from OLS −1.728
   to store-week-FE OLS −1.805, Hausman IV −1.781, and over-ID IV −1.780.
   The IV-vs-OLS relative difference is 3.0%; the store-week-FE-vs-OLS difference is
   4.5%. First-stage F ≫ 10, same sign, CI width ratio 1.08. All four decision-rule
   conditions clear → **Robust OLS**. **Same-chain caveat**: DFF is a single chain in a
   single metro, so Z_H still absorbs chain-wide promo calendars and Chicago-local demand
   shocks. The IV is a **sensitivity bound, not definitive causal identification** — true
   causal estimation requires multi-chain, multi-metro data.

2. **Promotion as clean treatment effect.** θ_promo is a conditional sale-code coefficient in log
   points, not a clean causal promotion effect. A coefficient of 0.43 implies
   `exp(0.43)-1 ≈ 54%` conditional demand difference under the model, but that may include
   promo targeting, vendor funding, inventory pressure, and stockpiling.

3. **Competitor reaction.** Cross-price coefficient captures historical co-movement, not a
   game-theoretic response. The simulator lets you shock rivals' prices ±25% as a what-if,
   but it does not solve a Nash equilibrium. Planned for `09_competitor_response.ipynb`.

4. **Within-brand cannibalization across package sizes.** **Diagnosed in `07_cannibalization_robustness.ipynb`**:
   β_same = +0.231*** (significant), but the implied **median spillover adjustment to top-10
   portfolio lifts is +2.5% (max +4.0%)** — well below the 10–15% band that would warrant
   rebuilding the optimizer with a joint objective. The per-cell optimizer is kept.

5. **Inventory feasibility.** Large predicted Q lifts assume restock capacity. The MVP flags
   `q_lift_ratio` per product-store but does not enforce a stockout constraint. Production
   needs a live inventory feed and a real stop-test guardrail (the 40% units-drop heuristic in
   `ab_test_plan.md` is a placeholder).

6. **Marginal cost ≠ AAC.** `unit_cost` derives from DFF's average acquisition cost (PROFIT
   field), which lags true replacement cost. Profit numbers are directionally useful, not
   accounting-grade.
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
