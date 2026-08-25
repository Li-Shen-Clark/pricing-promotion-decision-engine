"""Page 5 — Validate: candidate test plan + sample size widget."""
from __future__ import annotations
from html import escape
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_experiment_candidates, n_per_arm, read_markdown, REPORTS, MAIN_COEFS
from src.plots import sample_size_curve
from src.theme import (
    apply_page_theme, page_intro, sidebar_brand, section_header, status_pill,
)

apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag='Decision product for pricing teams',
)

page_intro(
    icon='',
    kicker='Experiment validation',
    title='Size the test before rollout.',
    tagline=(
        'Turn a shortlisted price action into a test plan with enough evidence '
        'to trust the result.'
    ),
    chips=[
        'Top-10 shortlist',
        'Store randomization',
        'Power check',
    ],
)

st.markdown(
    """
    <style>
      .pe-val-panel {
          border: 1px solid var(--border); border-radius: 8px;
          background: var(--surface-card); padding: 1rem 1.1rem;
          margin: 0.4rem 0 1.1rem 0;
      }
      .pe-val-head {
          display: flex; justify-content: space-between; gap: 1rem;
          align-items: flex-start; margin-bottom: 0.9rem;
      }
      .pe-val-title {
          font-size: 1.12rem; font-weight: 650; color: var(--text);
          line-height: 1.35;
      }
      .pe-val-copy {
          font-size: 0.94rem; color: var(--text-muted); line-height: 1.5;
          margin-top: 0.2rem;
      }
      .pe-val-grid {
          display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.7rem;
      }
      .pe-val-card {
          border: 1px solid var(--border); border-radius: 8px;
          background: var(--surface-2); padding: 0.85rem 0.95rem;
          min-height: 5.6rem;
      }
      .pe-val-card .label {
          font-size: 0.78rem; color: var(--text-muted); line-height: 1.35;
      }
      .pe-val-card .value {
          font-size: 1.32rem; color: var(--text); font-weight: 700;
          line-height: 1.2; margin-top: 0.25rem;
      }
      .pe-val-card .detail {
          font-size: 0.86rem; color: var(--text-muted); line-height: 1.45;
          margin-top: 0.35rem;
      }
      @media (max-width: 760px) {
          .pe-val-head { flex-direction: column; }
          .pe-val-grid { grid-template-columns: 1fr; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def _val_card(label: str, value: str, detail: str) -> str:
    return (
        '<div class="pe-val-card">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        f'<div class="detail">{escape(detail)}</div>'
        '</div>'
    )

with st.expander('How to read this page', expanded=False):
    st.markdown(
        """
- The table uses the default top-10 candidate set from Optimize.
- The key question is whether the planned test is long enough to detect the expected lift.
- The calculator below lets you resize a test for a different noise level or target effect.
"""
    )


@st.cache_data
def _load() -> pd.DataFrame:
    return load_experiment_candidates()


cand = _load()
n_under = int(cand['underpowered'].sum())
n_ready = len(cand) - n_under

section_header('Validation snapshot')
v1, v2, v3, v4 = st.columns(4)
v1.metric('Candidates reviewed', f'{len(cand)}')
v2.metric('Ready under current plan', f'{n_ready}')
v3.metric('Need resize', f'{n_under}')
v4.metric('Randomization unit', 'Store')

resize_status = (
    status_pill('Resize before rollout', 'warn')
    if n_under else status_pill('Current plan clears power check', 'ok')
)
st.markdown(
    f"""
    <div class="pe-val-panel">
      <div class="pe-val-head">
        <div>
          <div class="pe-val-title">Validation decision</div>
          <div class="pe-val-copy">
            The shortlist is ready for experiment planning, but most candidates need more exposure
            before the result should be trusted as a launch decision.
          </div>
        </div>
        <div>{resize_status}</div>
      </div>
      <div class="pe-val-grid">
        {_val_card('Ready under current plan', f'{n_ready} candidates', 'Planned store-weeks meet the power check.')}
        {_val_card('Need resize', f'{n_under} candidates', 'Add duration, add stores, or only act on a larger observed effect.')}
        {_val_card('Median required exposure', f"{cand['n_storeweeks_per_arm_at_50pct_MDE_80pct_power'].median():.1f} store-weeks", 'Per group at 50% MDE and 80% power.')}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- Top-10 test plan table ----
section_header(
    'Test plan · Top-10 portfolio candidates',
    caption='Default plan for the shortlisted candidates. Open the table when you want row-level detail.',
)

with st.expander('Open top-10 test-plan table', expanded=False):
    val_show_technical = st.toggle('Show technical columns', value=False, key='val_tech',
                                   help='Adds noise floor, observed profit, stores per group, '
                                        'and the required store-weeks per group.')

    decision_cols = {
        'brand_final':                                       'Brand',
        'size_oz_rounded':                                   'Size (oz)',
        'STORE':                                             'Store',
        'current_price':                                     'Current price',
        'candidate_price':                                   'Test price',
        'profit_lift_abs':                                   'Expected lift ($/wk)',
        'risk_flag':                                         'Risk',
        'recommended_test_type':                             'Test type',
        'planned_duration_weeks':                            'Planned weeks',
        'underpowered':                                      'Too short to detect?',
    }
    technical_cols = {
        'promo_status':                                      'Promo',
        'baseline_profit':                                   'Observed profit ($/wk)',
        'profit_std_wk':                                     'Weekly profit noise ($)',
        'planned_stores_per_arm':                            'Stores per group',
        'n_storeweeks_per_arm_at_50pct_MDE_80pct_power':     'Required store-weeks per group',
    }
    display_cols = {**decision_cols, **technical_cols} if val_show_technical else decision_cols
    view = cand.rename(columns=display_cols)[list(display_cols.values())]
    st.dataframe(view.style.format({
        'Size (oz)':                            '{:.2f}',
        'Current price':                        '${:.2f}',
        'Test price':                           '${:.2f}',
        'Observed profit ($/wk)':               '${:.0f}',
        'Expected lift ($/wk)':                 '${:+.0f}',
        'Weekly profit noise ($)':              '${:.0f}',
        'Required store-weeks per group':       '{:.0f}',
    }), width='stretch', hide_index=True)

# ---- Sample size widget ----
section_header(
    'Sample size calculator',
    caption='Defaults are drawn from the median candidate above. Change the inputs to size '
            'the test for a different candidate or a more conservative target.',
)

w1, w2, w3, w4 = st.columns(4)
sigma = w1.number_input('Weekly profit noise ($)',
                        min_value=1.0, max_value=1000.0,
                        value=float(round(cand['profit_std_wk'].median(), 0)),
                        step=1.0,
                        help='How much a single product-store\'s weekly profit varies week to week. '
                             'The noise floor the test has to cut through. (σ)')
delta = w2.number_input('Smallest lift to detect ($/week)',
                        min_value=1.0, max_value=2000.0,
                        value=float(round(cand['baseline_profit'].median() * 0.5, 0)),
                        step=1.0,
                        help='Set the test to reliably catch a real weekly profit improvement '
                             'of at least this size. (δ — minimum detectable effect)')
alpha = w3.select_slider('False-alarm risk',
                         options=[0.01, 0.05, 0.10], value=0.05,
                         format_func=lambda v: f'{v:.2f}',
                         help='Chance of declaring a winner when there is no real lift. (α, two-sided)')
power = w4.select_slider('Chance of catching a real lift',
                         options=[0.70, 0.80, 0.90, 0.95],
                         value=0.80, format_func=lambda v: f'{v:.2f}',
                         help='Chance the test detects a real lift of at least the size above. (1−β)')

n = n_per_arm(sigma, delta, alpha=alpha, power=power)
r1, r2, r3 = st.columns(3)
r1.metric('Required store-weeks per group', f'{n:,.0f}')
r2.metric('Total store-weeks (both groups)', f'{2*n:,.0f}')
weeks_at_5_stores = n / 5 if n != float('inf') else float('inf')
r3.metric('Weeks needed (5 stores per group)',
          '∞' if weeks_at_5_stores == float('inf') else f'{weeks_at_5_stores:,.1f}')

with st.expander('Open sample size curve', expanded=False):
    st.plotly_chart(
        sample_size_curve(sigma=float(sigma),
                          baseline_profit=float(round(cand['baseline_profit'].median(), 0))),
    )

# ---- A/B test plan markdown ----
section_header('Reference · Full test plan',
               caption="Source doc `reports/ab_test_plan.md` — what a PM would read before kicking off the test.")
with st.expander('Open full A/B test plan', expanded=False):
    st.markdown(read_markdown(REPORTS / 'ab_test_plan.md'))

st.caption(
    '**Online translation.** In a SaaS or e-commerce setting the randomization unit '
    'shifts from store to user / session. The same pattern applies: define a primary '
    'economic metric, compute σ from historical user-week spend, and size the test '
    'with the same formula.'
)
