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
    apply_page_theme, page_intro, sidebar_brand, section_header,
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
    title='Pricing cockpit for test decisions.',
    tagline='Rank price actions, read the risk, and size the A/B test before rollout.',
    chips=[
        '5,896 candidate actions',
        'Risk guardrails',
        'A/B validation',
    ],
)

@st.cache_data
def _kpi_inputs():
    cells = load_cells()
    top   = load_top_recommendations()
    exp   = load_experiment_candidates()
    return cells, top, exp


cells_df, top_df, exp_df = _kpi_inputs()

best = top_df.sort_values('profit_lift_abs', ascending=False).iloc[0]
best_plan = exp_df[
    (exp_df['brand_final'] == best['brand_final']) &
    (exp_df['size_oz_rounded'] == best['size_oz_rounded']) &
    (exp_df['STORE'] == best['STORE'])
]
best_plan_row = best_plan.iloc[0] if len(best_plan) else None

section_header(
    'Cockpit preview',
    caption='One candidate, one decision path. Deeper tables and model notes stay available below.',
)
preview_left, preview_right = st.columns([2.2, 1])
with preview_left:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Current price', f"${best['mean_p']:.2f}")
    m2.metric('Test price', f"${best['opt_price']:.2f}")
    m3.metric('Expected lift', f"${best['profit_lift_abs']:.0f}/wk")
    m4.metric(
        'Validation',
        'Extend test' if bool(best_plan_row['underpowered']) else 'Ready to test',
    )

    n1, n2, n3 = st.columns(3)
    with n1:
        st.page_link('pages/3_Optimize.py', label='Open Cockpit')
    with n2:
        st.page_link('pages/4_Validate.py', label='Check Validation')
    with n3:
        st.page_link('pages/0_Product_Brief.py', label='Read Brief')

with preview_right:
    risk = best_plan_row['risk_flag'] if best_plan_row is not None else 'review'
    test_type = best_plan_row['recommended_test_type'] if best_plan_row is not None else 'store test'
    st.markdown('**Decision read**')
    st.markdown(
        f"""
- **Candidate:** {best['brand_final']} {best['size_oz_rounded']:.0f}oz · Store {int(best['STORE'])}
- **Status:** test candidate, not auto-deployment
- **Risk:** {risk}
- **Next step:** {test_type.replace('_', ' ')}
"""
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
section_header('Decision queue snapshot')
col1, col2, col3, col4 = st.columns(4)
col1.metric('Product-store combinations screened', f'{len(cells_df):,}')
col2.metric('Shortlisted for testing',             f'{len(top_df):,}')
col3.metric('Flagged high-risk',                   int((exp_df['risk_flag'] == 'high').sum()))
col4.metric('Need longer validation',
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

with st.expander('Open top-10 candidate table', expanded=False):
    st.caption(
        'Sorted by expected weekly profit lift. Each row is something to test, not something to deploy.'
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
