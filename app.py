"""Pricing & Promotion Decision Engine — Streamlit MVP entry / Overview."""
from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import (
    load_cells, load_top_recommendations, load_experiment_candidates,
    MAIN_COEFS, REPORTS,
)
from src.plots import top_recommendations_bar
from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(
    page_title='Pricing & Promotion Decision Engine',
    page_icon='📊',
    layout='wide',
)

apply_page_theme()

# ---- Sidebar (branded) ----
sidebar_brand(
    name='Pricing Engine',
    tag='Decision product for pricing teams',
)

# ---- Hero ----
page_intro(
    icon='',
    kicker='Pricing decision product',
    title='Turn pricing data into testable product decisions.',
    tagline=(
        'A decision product for pricing teams: rank price and promotion actions, '
        'explain risk, and define the A/B validation plan before rollout.'
    ),
    chips=[
        '4.65M scanner observations',
        '5,896 candidate actions',
        'Retail pricing -> healthcare pricing roadmap',
    ],
)

section_header(
    'Fast demo path for reviewers',
    caption='A short path through the product if you only have two minutes. The rest is optional depth.',
)
d1, d2, d3, d4 = st.columns(4)
with d1:
    st.markdown('**1. Product brief**')
    st.caption('User, problem, MVP scope, metrics, and roadmap.')
    st.page_link('pages/0_Product_Brief.py', label='Open Product Brief')
with d2:
    st.markdown('**2. Find candidates**')
    st.caption('See how 5,896 product-store cells become a ranked test queue.')
    st.page_link('pages/3_Optimize.py', label='Open Optimize')
with d3:
    st.markdown('**3. Validate**')
    st.caption('Check whether the test is long enough to trust the lift.')
    st.page_link('pages/4_Validate.py', label='Open Validate')
with d4:
    st.markdown('**4. Read boundaries**')
    st.caption('See the risks the product refuses to hide.')
    st.page_link('pages/5_Boundaries.py', label='Open Boundaries')

with st.expander('Product framing and workflow', expanded=False):
    st.markdown(
        """
| Question | Product answer |
|---|---|
| **Who is this for?** | Pricing, revenue, or category teams choosing which action to test next. |
| **What is the workflow?** | Evidence -> Simulate / Optimize -> Validate -> Boundaries. |
| **What is the core trade-off?** | Interpretable recommendations over black-box forecast accuracy. |
| **What is the launch rule?** | No automatic price changes; every candidate needs validation. |
| **What makes this product-relevant?** | It turns analysis into a decision queue, risk readout, and A/B test plan. |
"""
    )


# ---- Worked example ----
@st.cache_data
def _kpi_inputs():
    cells = load_cells()
    top   = load_top_recommendations()
    exp   = load_experiment_candidates()
    return cells, top, exp


cells_df, top_df, exp_df = _kpi_inputs()

section_header(
    "Worked example · Kellogg's 15oz at Store 102",
    caption='One row from the panel, traced through every step of the workflow.',
)
e1, e2, e3, e4 = st.columns(4)
e1.metric('1. Today',      '$3.03',           help='Current shelf price')
e1.caption('76 weeks of history at this store.')
e2.metric('2. Candidate to test', '$4.30',    help='Optimizer-suggested test price')
e2.caption('Large price move; use only as a test candidate. +42% above historical band.')
e3.metric('3. Model-estimated lift', '+$311 / wk', help='Model-implied weekly profit lift')
e3.caption('+166.8% vs observed profit. Likely overstated near the price ceiling — read as test motivation, not a forecast.')
e4.metric('4. To validate', 'Store test', help='Recommended test design')
e4.caption('Planned test is too short to reliably detect this lift; extend duration or '
           'only commit if the test catches a much larger effect.')

st.markdown(
    'This single row reproduces the entire workflow: the model learns how sales '
    'usually respond to price, the simulator predicts the result, the optimizer '
    'ranks the candidate, and the validator checks whether the planned test is '
    'long enough. Open any page on the left to see the same row from that '
    'page\'s perspective.'
)

# ---- Model evidence (collapsed) ----
with st.expander('Why we trust the ranking', expanded=False):
    st.markdown(
        f"- **Own-price elasticity ≈ {MAIN_COEFS['beta_own']:.2f}** "
        '(fixed-effects OLS, frozen for the entire pipeline).\n'
        '- **IV-vs-OLS shift = 3.0%**, store-week FE shift = 4.5% — same sign, '
        'first-stage F ≫ 10. Decision rule says **Robust OLS**.\n'
        '- **98.5% of cells point to the upper price band** — read this as '
        'test-prioritization signal, not as a deployment instruction.\n\n'
        'Full evidence on the **Evidence** page; what the model can\'t claim '
        'on **Boundaries**.'
    )

# ---- Pipeline snapshot ----
section_header('Pipeline snapshot')
col1, col2, col3, col4 = st.columns(4)
col1.metric('Product-store combinations screened', f'{len(cells_df):,}')
col2.metric('Top-10 shortlisted for testing',      f'{len(top_df):,}')
col3.metric('Top-10 flagged high-risk',            int((exp_df['risk_flag'] == 'high').sum()))
col4.metric('Top-10 too short to detect a real lift',
            int(exp_df['underpowered'].sum()))

with st.expander('Model-implied lift across the full panel — diagnostic only, not a forecast'):
    st.markdown(
        f"If you naively sum the model-implied weekly profit lift across all "
        f"{len(cells_df):,} product-store combinations, you get "
        f"**${cells_df['profit_lift_abs'].sum():,.0f} / week** — but this is "
        '**not an additive portfolio forecast**. It assumes every candidate '
        'gets deployed simultaneously and that the model holds at the '
        'extrapolated upper price band for 98.5% of cases. Treat it as a '
        'sanity-check on the magnitude of opportunity, not as a business case.'
    )

# ---- Top-10 table ----
section_header(
    'Top-10 candidate actions',
    caption='Sorted by expected weekly profit lift. Each row is something to test, '
            'not something to deploy. "At price ceiling?" flags candidates where the '
            'recommended price would push beyond what this product has historically sold for.',
)

home_show_technical = st.toggle('Show technical columns', value=False, key='home_tech',
                                help='Adds promo flag, observed/test quantities, '
                                     'observed/test profit, and percent lift.')

decision_cols = {
    'brand_final':           'Brand',
    'STORE':                 'Store',
    'mean_p':                'Current price ($)',
    'opt_price':             'Test price ($)',
    'profit_lift_abs':       'Expected lift ($/wk)',
    'opt_hits_upper':        'At price ceiling?',
}
technical_cols = {
    'size_oz_rounded':       'Size (oz)',
    'opt_promo':             'Promo (model)',
    'baseline_q':            'Observed units/wk',
    'opt_q':                 'Test units/wk',
    'baseline_profit':       'Observed profit ($/wk)',
    'opt_profit':            'Test profit ($/wk)',
    'profit_lift_pct':       'Lift (%)',
}
display_cols = {**decision_cols, **technical_cols} if home_show_technical else decision_cols
top_view = top_df.rename(columns=display_cols)[list(display_cols.values())]
st.dataframe(top_view.style.format({
    'Size (oz)':                       '{:.2f}',
    'Current price ($)':               '{:.2f}',
    'Test price ($)':                  '{:.2f}',
    'Expected lift ($/wk)':            '${:.0f}',
    'Observed units/wk':               '{:.1f}',
    'Test units/wk':                   '{:.1f}',
    'Observed profit ($/wk)':          '${:.0f}',
    'Test profit ($/wk)':              '${:.0f}',
    'Lift (%)':                        '{:.0f}%',
}), width='stretch', hide_index=True)

with st.expander('Open chart view', expanded=False):
    fig = top_recommendations_bar(top_df)
    st.plotly_chart(fig)

st.markdown('---')
st.caption(
    "Data: Dominick's Finer Foods Cereals, 1989–1996. "
    'The full cleaning, modeling, counterfactual, validation, and robustness '
    'audit trail is documented in the repo.'
)

with st.expander('Technical audit trail', expanded=False):
    st.markdown(
        f"""
        **Pipeline.** `01_data_cleaning` → `02_eda` → `03_demand_estimation` →
        `04_counterfactual` → `05_ab_testing_design` →
        `07_cannibalization_robustness` → `08_iv_sensitivity`.

        **Reports.** `{(REPORTS / "demand_model_summary.md").relative_to(PROJECT_ROOT)}`,
        `{(REPORTS / "counterfactual_summary.md").relative_to(PROJECT_ROOT)}`,
        `{(REPORTS / "ab_test_plan.md").relative_to(PROJECT_ROOT)}`,
        `{(REPORTS / "cannibalization_robustness_summary.md").relative_to(PROJECT_ROOT)}`,
        `{(REPORTS / "iv_sensitivity_summary.md").relative_to(PROJECT_ROOT)}`,
        `{(REPORTS / "case_study.md").relative_to(PROJECT_ROOT)}`.
        """
    )

with st.expander('Next domain: healthcare pricing and access', expanded=False):
    st.markdown(
        """
| Stage | Focus |
|---|---|
| **Current product** | Retail pricing decisions: rank price/promo tests from scanner data. |
| **Next domain** | Healthcare pricing, reimbursement, payer constraints, patient affordability, and value evidence. |
| **PM trajectory** | Data-heavy product management for high-stakes decision workflows. |
"""
    )
