"""Page 5 — Validate: candidate test plan + sample size widget."""
from __future__ import annotations
from html import escape
from math import ceil, isinf
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
    format_money,
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
- The table uses the default top-10 candidate set from Cockpit.
- The key question is whether the planned test is long enough to detect the expected lift.
- The calculator below lets you adjust test size for a different noise level or target effect.
"""
    )


@st.cache_data
def _load() -> pd.DataFrame:
    return load_experiment_candidates()


cand = _load()
n_under = int(cand['underpowered'].sum())
n_ready = len(cand) - n_under

section_header(
    'Default shortlist check',
    caption='This snapshot uses the default top-10 plan. Manual sizing changes are evaluated in the calculator below.',
)
v1, v2, v3, v4 = st.columns(4)
v1.metric('Candidates reviewed', f'{len(cand)}')
v2.metric('Ready in default plan', f'{n_ready}')
v3.metric('Need sizing review', f'{n_under}')
v4.metric('Randomization unit', 'Store')

exposure_status = (
    status_pill('Default plan needs sizing review', 'note')
    if n_under else status_pill('Default plan clears power check', 'ok')
)
st.markdown(
    f"""
    <div class="pe-val-panel">
      <div class="pe-val-head">
        <div>
          <div class="pe-val-title">Default plan readout</div>
          <div class="pe-val-copy">
            The top-10 shortlist starts from a default plan. Use the calculator below to see whether
            a revised setup, such as more weeks or more stores per group, meets the sizing check.
          </div>
        </div>
        <div>{exposure_status}</div>
      </div>
      <div class="pe-val-grid">
        {_val_card('Ready in default plan', f'{n_ready} candidates', 'Default store-weeks meet the power check.')}
        {_val_card('Need sizing review', f'{n_under} candidates', 'May clear after adding weeks, adding stores, or targeting a larger detectable effect.')}
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
        'underpowered':                                      'Needs longer test?',
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
        'Current price':                        lambda value: format_money(value),
        'Test price':                           lambda value: format_money(value),
        'Observed profit ($/wk)':               '${:.0f}',
        'Expected lift ($/wk)':                 '${:+.0f}',
        'Weekly profit noise ($)':              '${:.0f}',
        'Required store-weeks per group':       '{:.0f}',
    }), width='stretch', hide_index=True)

# ---- Sample size widget ----
section_header(
    'Test sizing calculator',
    caption='Defaults start with an 8-week footprint sized to clear the median requirement. Lower stores, raise power, or shrink the detectable lift to see when the plan breaks.',
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
default_weeks = int(round(cand['planned_duration_weeks'].median()))
default_stores = min(500, max(1, ceil(n / default_weeks))) if not isinf(n) else 1
f1, f2 = st.columns(2)
planned_weeks = f1.number_input(
    'Planned test weeks',
    min_value=1,
    max_value=52,
    value=default_weeks,
    step=1,
    help='Change this when the experiment needs more time before rollout.',
)
stores_per_group = f2.number_input(
    'Stores per group',
    min_value=1,
    max_value=500,
    value=default_stores,
    step=1,
    help='Change this when the experiment needs more matched stores in each arm.',
)

planned_storeweeks = planned_weeks * stores_per_group
storeweek_gap = n - planned_storeweeks
needed_weeks = n / stores_per_group if stores_per_group else float('inf')
needed_stores = ceil(n / planned_weeks) if planned_weeks and not isinf(n) else float('inf')
plan_clears = storeweek_gap <= 0
plan_status = (
    status_pill('Plan meets sizing check', 'ok')
    if plan_clears else status_pill('Increase weeks or stores', 'warn')
)

st.markdown(
    f"""
    <div class="pe-val-panel">
      <div class="pe-val-head">
        <div>
          <div class="pe-val-title">Current test footprint</div>
          <div class="pe-val-copy">
            Planned exposure is weeks × stores per group. If it is below the required store-weeks,
            extend the test or add stores before treating the result as rollout evidence.
          </div>
        </div>
        <div>{plan_status}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

r1, r2, r3, r4 = st.columns(4)
r1.metric('Required store-weeks per group', f'{n:,.0f}')
r2.metric('Planned store-weeks per group', f'{planned_storeweeks:,.0f}')
r3.metric(
    'Gap to required exposure',
    'Clears' if plan_clears else f'{storeweek_gap:,.0f}',
    delta='Ready' if plan_clears else 'Add weeks or stores',
    delta_color='normal' if plan_clears else 'inverse',
)
r4.metric(
    'Needed at current setup',
    '∞' if isinf(needed_weeks) else f'{needed_weeks:,.1f} weeks',
    delta='or ∞ stores/group' if isinf(needed_stores) else f'or {needed_stores:,.0f} stores/group',
    delta_color='off',
)

with st.expander('Open sample size curve', expanded=False):
    st.plotly_chart(
        sample_size_curve(sigma=float(sigma),
                          baseline_profit=float(round(cand['baseline_profit'].median(), 0))),
        config={'displayModeBar': False},
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
