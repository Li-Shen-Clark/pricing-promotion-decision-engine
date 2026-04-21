"""Page 4 — Experiment Design: candidate test plan + sample size widget."""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_experiment_candidates, n_per_arm, read_markdown, REPORTS
from src.plots import sample_size_curve

st.set_page_config(page_title='Experiment Design', page_icon='🧪', layout='wide')

st.title('Experiment Design')
st.caption(
    'Every candidate from the optimizer needs validation. This page sizes the test '
    'and assigns a risk-tiered design (single-store flight / cluster RCT / standard A/B). '
    'Randomization unit: store (or store-cluster), matching offline retail price policy.'
)


@st.cache_data
def _load() -> pd.DataFrame:
    return load_experiment_candidates()


cand = _load()

st.info(
    '**Scenario note.** This test plan is the offline BASELINE list (no demand / cost / '
    'competitor / inventory shocks applied). If you ran the **Profit Optimizer** under a '
    'non-baseline scenario and want to test the resulting candidates, treat this page as '
    'a sizing template — the σ and δ inputs in the calculator below are what flow into '
    'the formula, regardless of which candidate generated them.'
)

# ---- Top-10 test plan table ----
st.subheader('Test plan for top-10 portfolio candidates')

display_cols = {
    'brand_final':                                       'Brand',
    'size_oz_rounded':                                   'Size (oz)',
    'STORE':                                             'Store',
    'current_price':                                     'Current $',
    'candidate_price':                                   'Candidate $',
    'promo_status':                                      'Promo',
    'baseline_profit':                                   'Baseline profit ($/wk)',
    'profit_lift_abs':                                   'Δ profit ($/wk, model)',
    'profit_std_wk':                                     'σ ($/wk)',
    'risk_flag':                                         'Risk',
    'recommended_test_type':                             'Test type',
    'planned_duration_weeks':                            'Planned weeks',
    'planned_stores_per_arm':                            'Stores per arm',
    'n_storeweeks_per_arm_at_50pct_MDE_80pct_power':     'Required n_sw/arm @ 50% MDE',
    'underpowered':                                      'Underpowered?',
}
view = cand.rename(columns=display_cols)[list(display_cols.values())]
st.dataframe(view.style.format({
    'Size (oz)':                       '{:.2f}',
    'Current $':                       '${:.2f}',
    'Candidate $':                     '${:.2f}',
    'Baseline profit ($/wk)':          '${:.0f}',
    'Δ profit ($/wk, model)':          '${:+.0f}',
    'σ ($/wk)':                        '${:.0f}',
    'Required n_sw/arm @ 50% MDE':     '{:.0f}',
}), width='stretch', hide_index=True)

n_under = int(cand['underpowered'].sum())
if n_under:
    st.warning(
        f'⚠ **{n_under}/{len(cand)} candidates are underpowered** at the planned design '
        '(required weeks > planned duration). Either extend the test, accept a larger '
        'MDE, or use a paired-control design that reduces variance.'
    )

# ---- Sample size widget ----
st.markdown('---')
st.subheader('Sample size calculator')
st.caption(
    'Two-sample equal-variance t-test with store-week as the unit. '
    'For panel designs with within-store correlation, multiply n by the design effect '
    '`1 + (m-1)·ICC` where m = weeks per store.'
)

w1, w2, w3, w4 = st.columns(4)
sigma = w1.number_input('σ (weekly profit std, $)',
                        min_value=1.0, max_value=1000.0,
                        value=float(round(cand['profit_std_wk'].median(), 0)),
                        step=1.0)
delta = w2.number_input('δ (MDE, $/week)',
                        min_value=1.0, max_value=2000.0,
                        value=float(round(cand['baseline_profit'].median() * 0.5, 0)),
                        step=1.0)
alpha = w3.select_slider('α (two-sided)', options=[0.01, 0.05, 0.10], value=0.05,
                         format_func=lambda v: f'{v:.2f}')
power = w4.select_slider('Power (1−β)', options=[0.70, 0.80, 0.90, 0.95],
                         value=0.80, format_func=lambda v: f'{v:.2f}')

n = n_per_arm(sigma, delta, alpha=alpha, power=power)
r1, r2, r3 = st.columns(3)
r1.metric('Required n per arm (store-weeks)', f'{n:,.0f}')
r2.metric('Total store-weeks (both arms)',    f'{2*n:,.0f}')
weeks_at_5_stores = n / 5 if n != float('inf') else float('inf')
r3.metric('Weeks if 5 stores per arm',
          '∞' if weeks_at_5_stores == float('inf') else f'{weeks_at_5_stores:,.1f}')

st.subheader('Sample size curve (log scale)')
st.plotly_chart(
    sample_size_curve(sigma=float(sigma),
                      baseline_profit=float(round(cand['baseline_profit'].median(), 0))),
)

# ---- A/B test plan markdown ----
st.markdown('---')
with st.expander('📋 Full A/B test plan (`reports/ab_test_plan.md`)', expanded=False):
    st.markdown(read_markdown(REPORTS / 'ab_test_plan.md'))

st.info(
    '**Online translation note.** In a SaaS or e-commerce setting the randomization '
    'unit shifts from `store` to `user / session`. The same design pattern applies: '
    'define a primary economic metric, compute σ from historical user-week spend, '
    'and size the test the same way.'
)
