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
    tag="Decision support · Dominick's cereals",
    badges=[
        ('β_own',   f"{MAIN_COEFS['beta_own']:.2f}"),
        ('β_cross', f"+{MAIN_COEFS['beta_cross']:.2f}"),
        ('θ',       f"+{MAIN_COEFS['theta_promo']:.2f}"),
    ],
    workflow=[
        (1, 'Overview',   True),
        (2, 'Evidence',   False),
        (3, 'Simulate',   False),
        (4, 'Optimize',   False),
        (5, 'Validate',   False),
        (6, 'Boundaries', False),
        (7, 'Upload',     False),
    ],
)

# ---- Hero ----
page_intro(
    icon='📊',
    kicker='Find pricing and promotion changes worth testing.',
    title='Pricing & Promotion Decision Engine',
    tagline=(
        'This app turns historical retail scanner data into a ranked list of '
        'price and promotion changes worth A/B testing — with the demand '
        'model, sensitivity grid, and test plan all visible.'
    ),
    chips=[
        "Built on Dominick's cereals · 1989-1996",
        '5,896 candidate cells',
        'Live on Streamlit Cloud',
    ],
)

# ---- What you can do here ----
section_header(
    'What you can do here',
    caption='Four steps. The sidebar on the left walks you through them in order.',
)
insight_row([
    Insight(
        label='1 · Estimate demand',
        headline='Learn how sales respond to price and promotion',
        detail=('Fit on 2.59M weekly observations across 5,896 brand-size-store '
                'cells. View the elasticities and the robustness checks behind '
                'them on the Evidence page.'),
        tone='brand',
    ),
    Insight(
        label='2 · Simulate a change',
        headline='Ask what happens if you move price, cost, or promo',
        detail=('Pick a cell, slide a candidate price, and read the model-'
                'predicted demand and profit response. Useful for pricing '
                'committee what-ifs.'),
        tone='brand',
    ),
    Insight(
        label='3 · Rank candidates',
        headline='Sort 5,896 cells by expected weekly profit lift',
        detail=('Filter by brand, size, or history. The top of the list is '
                'where the model says to test next — not where to deploy.'),
        tone='brand',
    ),
    Insight(
        label='4 · Plan a test',
        headline='Turn a candidate into a controlled A/B',
        detail=('Store-level randomization, 80% power sizing, and an automatic '
                'underpowered flag. No price change ships without a passing '
                'test.'),
        tone='brand',
    ),
])


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
e2.metric('2. Model says', '$4.30',           help='Optimizer candidate price')
e2.caption('+42% — flagged as extrapolation beyond historical band.')
e3.metric('3. Expected',   '+$311 / wk',      help='Model-implied weekly profit lift')
e3.caption('+166.8% over baseline · model upper-bound, not a deployment target.')
e4.metric('4. To validate', 'High-risk cluster RCT', help='Recommended test design')
e4.caption('Flagged underpowered at planned duration — extend or accept larger MDE.')

st.markdown(
    'This single row reproduces the entire pipeline: the demand model fits the '
    'elasticity, the simulator predicts the response, the optimizer ranks the '
    'candidate, the risk flags fire, and the test planner sizes the experiment. '
    'Open any page on the left to see the same row from that page\'s perspective.'
)

# ---- Model evidence (collapsed) ----
with st.expander('Model evidence — coefficients, IV checks, robustness', expanded=False):
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

# ---- Portfolio snapshot ----
section_header('Portfolio snapshot', caption='Model-implied top-line figures across the eligible panel.')
col1, col2, col3, col4 = st.columns(4)
col1.metric('Eligible cells (brand-size-store)', f'{len(cells_df):,}')
col2.metric('Expected weekly profit lift (model upper-bound)',
            f"${cells_df['profit_lift_abs'].sum():,.0f}")
col3.metric('High-risk candidates (top-10)',
            int((exp_df['risk_flag'] == 'high').sum()))
col4.metric('Underpowered tests (planned vs required)',
            int(exp_df['underpowered'].sum()))

# ---- Top-10 table ----
section_header(
    'Top-10 candidate actions',
    caption='One row per brand-size portfolio slot, sorted by expected weekly profit lift. '
            'Each row is a raise-and-test candidate, not a deployment instruction. '
            '"Hits price ceiling?" flags candidates where the model wants a price '
            'beyond the historical band — read those with extra skepticism.',
)

display_cols = {
    'brand_final':           'Brand',
    'size_oz_rounded':       'Size (oz)',
    'STORE':                 'Store',
    'mean_p':                'Current price ($)',
    'opt_price':             'Candidate price ($)',
    'opt_promo':             'Promo (model)',
    'baseline_q':            'Baseline q (units/wk)',
    'opt_q':                 'Candidate q (units/wk, model)',
    'baseline_profit':       'Baseline profit ($/wk)',
    'opt_profit':            'Candidate profit ($/wk, model)',
    'profit_lift_abs':       'Δ profit ($/wk, model)',
    'profit_lift_pct':       'Δ profit (%)',
    'opt_hits_upper':        'Hits price ceiling?',
}
top_view = top_df.rename(columns=display_cols)[list(display_cols.values())]
st.dataframe(top_view.style.format({
    'Size (oz)':                       '{:.2f}',
    'Current price ($)':               '{:.2f}',
    'Candidate price ($)':             '{:.2f}',
    'Baseline q (units/wk)':           '{:.1f}',
    'Candidate q (units/wk, model)':   '{:.1f}',
    'Baseline profit ($/wk)':          '${:.0f}',
    'Candidate profit ($/wk, model)':  '${:.0f}',
    'Δ profit ($/wk, model)':          '${:.0f}',
    'Δ profit (%)':                    '{:.0f}%',
}), width='stretch', hide_index=True)

section_header('Top-10 expected weekly profit lift (model upper-bound)')
fig = top_recommendations_bar(top_df)
st.plotly_chart(fig)

st.markdown('---')
st.caption(
    "Data: Dominick's Finer Foods Cereals (1989–1996, 4.65M store-week observations). "
    'Pipeline: `01_data_cleaning` → `02_eda` → `03_demand_estimation` → '
    '`04_counterfactual` → `05_ab_testing_design` → `07_cannibalization_robustness` → '
    '`08_iv_sensitivity`. '
    f'Reports: `{(REPORTS / "demand_model_summary.md").relative_to(PROJECT_ROOT)}`, '
    f'`{(REPORTS / "counterfactual_summary.md").relative_to(PROJECT_ROOT)}`, '
    f'`{(REPORTS / "ab_test_plan.md").relative_to(PROJECT_ROOT)}`, '
    f'`{(REPORTS / "cannibalization_robustness_summary.md").relative_to(PROJECT_ROOT)}`, '
    f'`{(REPORTS / "iv_sensitivity_summary.md").relative_to(PROJECT_ROOT)}`, '
    f'`{(REPORTS / "case_study.md").relative_to(PROJECT_ROOT)}`.'
)
