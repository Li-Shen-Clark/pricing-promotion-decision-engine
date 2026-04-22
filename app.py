"""Pricing & Promotion Decision Engine — Streamlit MVP entry / Executive Summary."""
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
        (1, 'Demand Model',             False),
        (2, 'Counterfactual Simulator', False),
        (3, 'Profit Optimizer',         False),
        (4, 'Experiment Design',        False),
        (5, 'Limitations',              False),
        (6, 'Upload & Score',           False),
    ],
)
st.sidebar.caption(
    'Frozen `baseline_with_cross` FE OLS · IV-robust. See Demand Model.'
)

# ---- Header ----
page_intro(
    icon='📊',
    kicker='Executive summary',
    title='Pricing & Promotion Decision Engine',
    tagline=(
        'A reproducible pipeline that turns historical scanner-panel data into '
        'candidate pricing actions for controlled experimentation. '
        'No price changes ship without an A/B test.'
    ),
    chips=[
        '5,896 eligible cells',
        '4.65M store-weeks',
        '60 tests · pytest green',
        'Live on Streamlit Cloud',
    ],
)

# ---- Three core findings ----
insight_row([
    Insight(
        label='Raise-and-test signal',
        headline='98.5% of eligible cells point to the upper price band',
        detail=('Constant-elasticity demand with ε ≈ -1.73 and an AAC cost proxy '
                'make price increases the dominant model signal. Treat this as a '
                'test-prioritization result, not an automatic deployment rule.'),
        tone='brand',
    ),
    Insight(
        label='Identification',
        headline='β_own passes IV and store-week FE sensitivity checks',
        detail=('OLS −1.73 → Hausman IV −1.78, a 3.0% shift; store-week FE is '
                '−1.80, a 4.5% shift. Same sign, first-stage F ≫ 10, CI ratio '
                '1.08 — Robust OLS with same-chain caveat flagged.'),
        tone='ok',
    ),
    Insight(
        label='Decision rule',
        headline='Recommendations require controlled validation',
        detail=('Every candidate flows into the Experiment Design page: store-level '
                'randomization, power at 80%, an explicit underpowered flag. The '
                'optimizer is a search heuristic; the experiment turns a candidate '
                'into a decision.'),
        tone='note',
    ),
])


@st.cache_data
def _kpi_inputs():
    cells = load_cells()
    top   = load_top_recommendations()
    exp   = load_experiment_candidates()
    return cells, top, exp


cells_df, top_df, exp_df = _kpi_inputs()

# ---- KPI tiles ----
section_header('Portfolio snapshot', caption='Model-implied top-line figures across the eligible panel.')
col1, col2, col3, col4 = st.columns(4)
col1.metric('Eligible cells (brand-size-store)', f'{len(cells_df):,}')
col2.metric('Expected weekly profit lift (model upper-bound)',
            f"${cells_df['profit_lift_abs'].sum():,.0f}")
col3.metric('High-risk candidates (top-10)',
            int((exp_df['risk_flag'] == 'high').sum()))
col4.metric('Underpowered tests (planned vs required)',
            int(exp_df['underpowered'].sum()))

section_header(
    'Top-10 candidate actions',
    caption='One row per brand-size portfolio slot, sorted by expected weekly profit lift. '
            'Each row is a raise-and-test candidate, not a deployment instruction.',
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

section_header('Top-10 expected weekly profit lift (model)')
fig = top_recommendations_bar(top_df)
st.plotly_chart(fig)

section_header('How to read these recommendations')
st.markdown(
    '- **Candidate price** — the model-recommended price within the historical band. '
    'Not a deployment instruction.\n'
    '- **Expected lift under model assumptions** — log-linear demand response holding '
    'competitor prices fixed. Likely an upper bound.\n'
    '- **Every row needs validation.** See **Experiment Design** for the test plan.'
)

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
