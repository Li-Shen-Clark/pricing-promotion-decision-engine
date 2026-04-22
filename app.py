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
    icon='📊',
    kicker='Find pricing and promotion changes worth testing.',
    title='Pricing & Promotion Decision Engine',
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
    caption='Core workflow: Evidence → Simulate → Candidate Finder → Test Planner. '
            'Boundaries and Upload are optional — read Boundaries to see what the demo '
            'will not claim; use Upload to score your own data.',
)
insight_row([
    Insight(
        label='1 · Learn the response',
        headline='How do sales react to price and promotion?',
        detail=('Estimated from 2.59M weekly records across 5,896 product-store '
                'combinations. Plain-language summary on the Evidence page.'),
        tone='brand',
    ),
    Insight(
        label='2 · Try a change',
        headline='What happens if I move the price?',
        detail=('Pick one product at one store, slide a candidate price, and '
                'read the model-predicted units, revenue, and profit response.'),
        tone='brand',
    ),
    Insight(
        label='3 · Rank candidates',
        headline='Which changes are worth testing first?',
        detail=('Sort 5,896 product-store combinations by expected weekly '
                'profit lift. The top of the list is where to test next — '
                'not where to deploy.'),
        tone='brand',
    ),
    Insight(
        label='4 · Plan a test',
        headline='How do I confirm it works in real stores?',
        detail=('A test plan with store-level randomization, 80% power sizing, '
                'and an automatic flag for tests too short to detect a real '
                'lift.'),
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
e3.caption('+166.8% over baseline. Likely overstated near the price ceiling — read as test motivation.')
e4.metric('4. To validate', 'Needs a controlled store test', help='Recommended test design')
e4.caption('Planned test is too short to reliably detect this lift; extend duration or '
           'only commit if the test catches a much larger effect.')

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
    'size_oz_rounded':       'Size (oz)',
    'STORE':                 'Store',
    'mean_p':                'Current price ($)',
    'opt_price':             'Test price ($)',
    'profit_lift_abs':       'Expected lift ($/wk)',
    'opt_hits_upper':        'At price ceiling?',
}
technical_cols = {
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
