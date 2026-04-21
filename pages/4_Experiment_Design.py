"""Page 4 — Experiment Design: candidate test plan + sample size widget."""
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

st.set_page_config(page_title='Experiment Design', page_icon='🧪', layout='wide')
apply_page_theme()

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
        (4, 'Experiment Design',        True),
        (5, 'Limitations',              False),
        (6, 'Upload & Score',           False),
    ],
)

page_intro(
    icon='🧪',
    kicker='Workflow · Step 4 · Validation gate',
    title='Experiment Design',
    tagline=(
        'Every optimizer candidate flows through a risk-tiered test plan. Randomization '
        'unit is the store (or store-cluster), matching offline retail price policy.'
    ),
    chips=[
        'Top-10 test plan',
        'Store-level RCT',
        '80% power sizing',
        'Underpowered flag',
    ],
)

insight_row([
    Insight(
        label='Step A · Candidate',
        headline='Optimizer output feeds the plan',
        detail=('The top-10 table below is the offline baseline candidate set. '
                'Re-running the optimizer under a scenario overlay produces a new set '
                'that plugs into the same sizing template.'),
        tone='brand',
    ),
    Insight(
        label='Step B · Test design',
        headline='Risk tier picks the test type',
        detail=('Risk flag (high / medium / low) maps to single-store flight, cluster RCT, '
                'or standard A/B. Store is the randomization unit to match how prices are '
                'actually set in the chain.'),
        tone='note',
    ),
    Insight(
        label='Step C · Power check',
        headline='Size the test to detect a real lift',
        detail=('Two-sample t-test with store-week as the unit. The calculator flags '
                'candidates whose required duration exceeds the planned weeks so they can '
                'be re-designed or deprioritised.'),
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
    caption='Offline baseline list (no scenario shocks). Under a custom scenario, use the '
            'calculator below as a sizing template with the σ and δ of your candidates.',
)

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
section_header(
    'Sample size calculator',
    caption='Two-sample equal-variance t-test with store-week as the unit. For panel designs '
            'with within-store correlation, multiply n by the design effect `1 + (m-1)·ICC`.',
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

section_header('Sample size curve (log scale)',
               caption='Required store-weeks per arm vs detectable effect size.')
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
