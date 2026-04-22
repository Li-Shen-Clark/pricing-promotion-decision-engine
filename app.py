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
    tag="Decision support for cereal pricing",
)

# ---- Hero ----
page_intro(
    icon='',
    kicker='Pricing decision support',
    title='Find pricing and promotion changes worth testing.',
    tagline=(
        'Pick a product at a store. Test a price or promo change. Get the '
        'expected weekly profit lift plus an A/B test plan.'
    ),
    chips=[
        "Dataset · Dominick's cereals 1989-1996",
        '5,896 product-store combinations',
        'Live on Streamlit Cloud',
    ],
)

# ---- What you can do here ----
section_header(
    'What you can do here',
    caption='Core workflow: Evidence → Simulate / Optimize → Validate. '
            'Boundaries and Upload are optional — read Boundaries to see what the demo '
            'will not claim; use Upload to score your own data.',
)
insight_row([
    Insight(
        label='Step 01',
        headline='Learn how sales respond to price and promotion',
        detail=('Plain-language summary plus the underlying coefficients on '
                'the Evidence page.'),
        tone='brand',
    ),
    Insight(
        label='Step 02',
        headline='Test a change',
        detail=('Try one product at one store on the Simulate page, or rank '
                'all 5,896 product-store combinations by expected lift on '
                'the Optimize page.'),
        tone='brand',
    ),
    Insight(
        label='Step 03',
        headline='Plan validation',
        detail=('Size the A/B test that confirms the lift is real on the '
                'Validate page. Auto-flags tests too short to detect the '
                'expected lift.'),
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
e2.metric('2. Candidate to test', '$4.30',    help='Optimizer-suggested test price')
e2.caption('Large price move; use only as a test candidate. +42% above historical band.')
e3.metric('3. Model-estimated lift', '+$311 / wk', help='Model-implied weekly profit lift')
e3.caption('+166.8% over baseline. Likely overstated near the price ceiling — read as test motivation, not a forecast.')
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
section_header(
    'Pipeline snapshot',
    caption='How the model narrows from the full panel down to a small list of testable candidates.',
)
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
                                help='Adds promo flag, baseline/candidate quantities, '
                                     'baseline/candidate profit, and percent lift.')

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
    'baseline_q':            'Baseline units/wk',
    'opt_q':                 'Test units/wk',
    'baseline_profit':       'Baseline profit ($/wk)',
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
    'Baseline units/wk':               '{:.1f}',
    'Test units/wk':                   '{:.1f}',
    'Baseline profit ($/wk)':          '${:.0f}',
    'Test profit ($/wk)':              '${:.0f}',
    'Lift (%)':                        '{:.0f}%',
}), width='stretch', hide_index=True)

section_header('Where the model would test first',
               caption='Top-10 by model-estimated lift — read as test prioritization, not as a profit forecast.')
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
