"""Page 5 — Validate: candidate test plan + sample size widget."""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_experiment_candidates, n_per_arm, read_markdown, REPORTS, MAIN_COEFS
from src.plots import sample_size_curve
from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(page_title='Validate · Plan an A/B test', page_icon='🧪', layout='wide')
apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag='Decision support for cereal pricing',
)

page_intro(
    icon='',
    kicker='Step 03 · How do I confirm it works in real stores?',
    title='Validate · Plan an A/B test',
    tagline=(
        'Every candidate needs a controlled A/B test before deployment. '
        'The randomization unit is the store, matching how prices are '
        'actually set in the chain.'
    ),
    chips=[
        'Top-10 test plan',
        'Store-level randomization',
        'Checks the test is long enough',
    ],
)

insight_row([
    Insight(
        label='1 · Candidate',
        headline='Comes from the Optimize page',
        detail=('The top-10 table below is the offline default-scenario candidate set. '
                'Re-running the optimizer under a scenario produces a new list that '
                'plugs into the same sizing template.'),
        tone='brand',
    ),
    Insight(
        label='2 · Test design',
        headline='Risk tier picks the test type',
        detail=('High-risk candidates need matched store tests; lower-risk '
                'candidates can use simpler A/B tests. The store is the '
                'randomization unit to match how prices are actually set.'),
        tone='note',
    ),
    Insight(
        label='3 · Power check',
        headline='Is the planned test long enough?',
        detail=('The calculator checks whether the planned test is long enough '
                'to reliably detect the expected lift — and flags candidates '
                'that would need more weeks or a tighter target.'),
        tone='ok',
    ),
])


@st.cache_data
def _load() -> pd.DataFrame:
    return load_experiment_candidates()


cand = _load()

# ---- Top-10 test plan table ----
section_header(
    'Test plan · Top-10 portfolio candidates',
    caption='Default test plan for the top-10 candidates. Toggle "Show technical columns" '
            'to add weekly noise, observed profit, store counts, and required sample size.',
)

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

n_under = int(cand['underpowered'].sum())
if n_under:
    st.warning(
        f'⚠ **{n_under} of {len(cand)} candidates are flagged "too short to detect."** '
        'The planned test duration is shorter than the model says is needed to '
        'reliably catch the expected lift. Either extend the test, only commit if '
        'the test catches a much larger effect, or use a paired-store design that '
        'cancels store-to-store noise.'
    )

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

section_header('Sample size curve',
               caption='How required store-weeks per group changes as the smallest lift you want to catch shrinks.')
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
