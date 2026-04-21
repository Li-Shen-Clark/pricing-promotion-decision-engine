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

st.set_page_config(
    page_title='Pricing & Promotion Decision Engine',
    page_icon='📊',
    layout='wide',
)

# ---- Sidebar ----
with st.sidebar:
    st.markdown('### Pricing & Promotion Decision Engine')
    st.caption('MVP demo · Dominick’s Finer Foods · Cereals')
    st.markdown('**Frozen model**: `baseline_with_cross` (FE OLS)')
    st.markdown(
        f"- β_own = **{MAIN_COEFS['beta_own']:.2f}**  \n"
        f"- β_cross = **+{MAIN_COEFS['beta_cross']:.2f}**  \n"
        f"- sale-code θ = **+{MAIN_COEFS['theta_promo']:.2f}**"
    )
    st.caption(
        'β_own IV-sensitivity-tested (notebook 08): Hausman IV and '
        'store-week FE move the estimate by 3-4% and preserve sign — **Robust OLS**. '
        'Same-chain caveat applies; see Limitations.'
    )
    st.markdown('---')
    st.markdown('**Use the page list above to explore.**')
    st.markdown(
        '1. Demand Model  \n'
        '2. Counterfactual Simulator  \n'
        '3. Profit Optimizer  \n'
        '4. Experiment Design  \n'
        '5. Limitations  \n'
        '6. Upload & Score'
    )

# ---- Header ----
st.title('Pricing & Promotion Decision Engine')
st.markdown(
    'A reproducible pipeline that turns historical scanner-panel data into '
    '**candidate pricing actions for controlled experimentation**. '
    'No price changes ship without an A/B test.'
)

# ---- Headline alert ----
st.warning(
    '**Headline finding.** The optimizer frequently binds at the upper price guardrail: '
    '**98.5% of eligible cells** recommend the maximum allowed price under the model. '
    'This is a **diagnostic result** of the constant-elasticity model and cost proxy. '
    'These are **candidate price increases that require controlled validation**, not '
    'deployment recommendations.'
)

st.success(
    '**β_own robustness (notebook 08).** Hausman-style leave-one-out other-store IV and '
    'store-week fixed effects move the own-price elasticity by 3-4% (OLS −1.73, IV −1.78, '
    'store-week FE −1.80) with the same sign, first-stage F ≫ 10, and a 1.08× CI width '
    'ratio. All four robustness conditions clear → **Robust OLS**. The estimate is '
    'bounded against cross-store simultaneity within this sample\'s identification '
    'limits; a same-chain / single-metro caveat remains.'
)


@st.cache_data
def _kpi_inputs():
    cells = load_cells()
    top   = load_top_recommendations()
    exp   = load_experiment_candidates()
    return cells, top, exp


cells_df, top_df, exp_df = _kpi_inputs()

# ---- KPI tiles ----
col1, col2, col3, col4 = st.columns(4)
col1.metric('Eligible cells (brand-size-store)', f'{len(cells_df):,}')
col2.metric('Total expected weekly profit lift (model)',
            f"${cells_df['profit_lift_abs'].sum():,.0f}")
col3.metric('High-risk candidates (top-10)',
            int((exp_df['risk_flag'] == 'high').sum()))
col4.metric('Underpowered tests (planned vs required)',
            int(exp_df['underpowered'].sum()))

st.markdown('### Top-10 candidate actions (portfolio view, one per brand-size)')
st.caption(
    'Sorted by expected weekly profit lift under model assumptions. Each row is a '
    '**raise-and-test candidate**, not a deployment instruction.'
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

st.markdown('### Top-10 expected weekly profit lift (model)')
fig = top_recommendations_bar(top_df)
st.plotly_chart(fig)

st.info(
    '**How to read these recommendations**  \n'
    '• "Candidate price" = the model-recommended price within the historical band. '
    'Not a deployment instruction.  \n'
    '• "Expected lift under model assumptions" = log-linear demand response holding '
    'competitor prices fixed. Likely an upper bound.  \n'
    '• Every row needs validation. See **Experiment Design** for the test plan.'
)

st.markdown('---')
st.caption(
    'Data: Dominick’s Finer Foods Cereals (1989–1996, 4.65M store-week observations). '
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
