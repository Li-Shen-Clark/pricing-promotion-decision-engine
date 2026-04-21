"""Page 2 — Counterfactual Simulator: cell selector + sliders + curves."""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_cells, predict_q, MAIN_COEFS, SENSITIVITY_GRID
from src.optimization import make_price_grid, evaluate_curve, MARGIN_FLOOR_RATIO
from src.plots import quantity_price_curve, profit_price_curve
from src.scenario import (
    Scenario, BASELINE,
    apply_demand_overlay, effective_cost, compute_profit, scenario_warnings,
)
from src.theme import (
    apply_page_theme, page_intro, sidebar_brand, section_header,
)

st.set_page_config(page_title='Counterfactual Simulator', page_icon='🎚', layout='wide')
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
        (2, 'Counterfactual Simulator', True),
        (3, 'Profit Optimizer',         False),
        (4, 'Experiment Design',        False),
        (5, 'Limitations',              False),
        (6, 'Upload & Score',           False),
    ],
)

page_intro(
    icon='🎚',
    kicker='Workflow · Step 2 · What-if explorer',
    title='Counterfactual Simulator',
    tagline=(
        'Pick a cell, move the candidate price, and read the shape of the model '
        'response. Scenario overlays on the sidebar stress-test demand, cost, and '
        'competitor shocks without re-fitting the model.'
    ),
    chips=[
        'Frozen model inference',
        'Sensitivity sliders',
        'Scenario overlays',
        'Curves + edge-flag warnings',
    ],
)


@st.cache_data
def _cells() -> pd.DataFrame:
    df = load_cells()
    return df.sort_values(['brand_final', 'size_oz_rounded', 'STORE'])


cells = _cells()

# ---- Selector cascade ----
sel_col1, sel_col2, sel_col3 = st.columns([1, 1, 1])
brand = sel_col1.selectbox('Brand', sorted(cells['brand_final'].unique()))
sizes = sorted(cells.loc[cells['brand_final'] == brand, 'size_oz_rounded'].unique())
size  = sel_col2.selectbox('Size (oz)', sizes, format_func=lambda s: f'{s:.2f}')
stores = sorted(
    cells.loc[(cells['brand_final'] == brand) & (cells['size_oz_rounded'] == size),
              'STORE'].unique()
)
store = sel_col3.selectbox('Store', stores)

row = cells.loc[
    (cells['brand_final'] == brand) &
    (cells['size_oz_rounded'] == size) &
    (cells['STORE'] == store)
].iloc[0].to_dict()

# ---- Cell baseline ----
section_header('Cell baseline (observed)', caption='Means over the observed history of this brand-size-store cell.')
b1, b2, b3, b4, b5 = st.columns(5)
b1.metric('Mean price', f"${row['mean_p']:.2f}")
b2.metric('Mean cost (AAC)', f"${row['mean_cost']:.2f}")
b3.metric('Mean units / week', f"{row['mean_q']:.1f}")
b4.metric('Baseline profit / week', f"${row['baseline_profit']:.0f}")
b5.metric('History (weeks)', f"{int(row['n_weeks'])}")

# ---- Sidebar: sensitivity controls ----
def _nearest(grid, target):
    return min(grid, key=lambda v: abs(v - target))


with st.sidebar:
    st.markdown('### Demand parameters')
    beta_own = st.select_slider(
        'β_own (own-price elasticity)',
        options=SENSITIVITY_GRID['beta_own'],
        value=_nearest(SENSITIVITY_GRID['beta_own'], MAIN_COEFS['beta_own']),
        format_func=lambda v: f'{v:+.2f}',
    )
    beta_cross = st.select_slider(
        'β_cross (competitor)',
        options=SENSITIVITY_GRID['beta_cross'], value=0.0,
        format_func=lambda v: f'{v:+.2f}',
    )
    theta = st.select_slider(
        'θ_promo (sale-code effect, log-points)',
        options=SENSITIVITY_GRID['theta_promo'],
        value=_nearest(SENSITIVITY_GRID['theta_promo'], MAIN_COEFS['theta_promo']),
        format_func=lambda v: f'+{v:.2f}',
    )
    st.caption(
        'Defaults are the closest sensitivity-grid value to the frozen `baseline_with_cross` '
        'point estimate (β_own=-1.73, θ=+0.43). θ is a conditional sale-code effect; '
        'exp(0.43)-1 ≈ 54% under the model, not a clean causal effect. Move sliders to '
        'explore the elasticity neighbourhood.'
    )

    st.markdown('---')
    st.markdown('### Scenario controls')
    st.caption(
        'Layered on top of the model. Defaults are inert — leave everything at zero / off '
        'to reproduce the frozen baseline.'
    )
    demand_shock_pct = st.slider(
        'Demand shock (%)', min_value=-30, max_value=30, value=0, step=5,
        help='Multiplicative on predicted Q. Use to stress-test soft- or hot-demand worlds.',
    )
    cost_shock_pct = st.slider(
        'Cost shock (%)', min_value=-25, max_value=40, value=0, step=5,
        help='Multiplicative on AAC unit cost. Use to test commodity / supplier scenarios.',
    )
    comp_shock_pct = st.slider(
        'Competitor price shock (%)', min_value=-25, max_value=25, value=0, step=5,
        help='Multiplicative on competitor index. Activates β_cross.',
    )
    use_inv_cap = st.toggle('Inventory cap?', value=False,
                            help='Hard ceiling on units sold per week.')
    inventory_cap_val = (
        st.number_input('Inventory cap (units/week)', min_value=1.0, max_value=10000.0,
                        value=float(round(row['mean_q'] * 1.2, 1)), step=1.0)
        if use_inv_cap else None
    )
    promo_fixed_cost = st.number_input(
        'Promo fixed cost ($/wk)', min_value=0.0, max_value=2000.0, value=0.0, step=5.0,
        help='Deducted from profit when promo is on. Set above 0 to test promo break-even.',
    )

scenario = Scenario(
    demand_shock=demand_shock_pct / 100.0,
    cost_shock=cost_shock_pct / 100.0,
    competitor_price_shock=comp_shock_pct / 100.0,
    inventory_cap=inventory_cap_val,
    promo_fixed_cost=promo_fixed_cost,
)
cost_eff = float(effective_cost(row['mean_cost'], scenario))

# ---- Candidate sliders ----
section_header('Candidate price & promo', caption='Move the slider to set the counterfactual price point.')

# Price grid uses *effective* cost so the margin floor moves with the cost shock.
_grid = make_price_grid(row['p_min'], row['p_max'], cost_eff)
p_lo, p_hi = float(_grid.min()), float(_grid.max())

s1, s2 = st.columns([2, 1])
candidate_price = s1.slider(
    'Candidate price ($)',
    min_value=round(p_lo, 2), max_value=round(p_hi, 2),
    value=float(round(min(max(row['mean_p'], p_lo), p_hi), 2)),
    step=0.05,
    help=f'Bounded by [0.85·p_min, 1.15·p_max] with margin floor {MARGIN_FLOOR_RATIO}×cost_eff. '
         f'Margin floor here = ${cost_eff * MARGIN_FLOOR_RATIO:.2f} '
         f'(raw cost ${row["mean_cost"]:.2f}, effective ${cost_eff:.2f}).',
)
candidate_promo = s2.toggle('Promo on?', value=bool(round(row['mean_promo'])))

# ---- Predict (model output, then scenario overlay) ----
q_model = float(predict_q(
    candidate_price, int(candidate_promo),
    mean_q=row['mean_q'], mean_p=row['mean_p'], mean_promo=row['mean_promo'],
    beta_own=beta_own, theta=theta, beta_cross=beta_cross,
    log_p_comp_delta=scenario.log_p_comp_delta,
))
candidate_q = float(apply_demand_overlay(q_model, scenario))
candidate_rev    = candidate_q * candidate_price
candidate_profit = float(compute_profit(
    candidate_price, candidate_q,
    cost_eff=cost_eff, promo=int(candidate_promo), scenario=scenario,
))

# ---- Outputs ----
section_header('Expected outcomes (under model)', caption='Frozen-model predictions; scenario overlay applied if sliders are off baseline.')
o1, o2, o3, o4 = st.columns(4)
o1.metric('Predicted units / week', f'{candidate_q:.1f}',
          delta=f"{candidate_q - row['mean_q']:+.1f} vs baseline")
o2.metric('Predicted revenue / week', f'${candidate_rev:.0f}',
          delta=f"${candidate_rev - row['baseline_rev']:+.0f}")
o3.metric('Predicted profit / week', f'${candidate_profit:.0f}',
          delta=f"${candidate_profit - row['baseline_profit']:+.0f}")
delta_pct = (candidate_profit - row['baseline_profit']) / max(row['baseline_profit'], 1e-6) * 100
o4.metric('Δ profit (%)', f'{delta_pct:+.1f}%')

# ---- Scenario warnings ----
sc_flags = scenario_warnings(scenario, baseline_q=row['mean_q'])
if sc_flags:
    st.warning('**Scenario warnings.**\n' + '\n'.join(f'- {f}' for f in sc_flags))
elif not scenario.is_baseline:
    st.info('Scenario active but within sane bounds — outputs above include the overlay.')

# ---- Curves ----
prices = np.linspace(p_lo, p_hi, 60)
curve_promo_match = evaluate_curve(
    row, prices, int(candidate_promo),
    beta_own=beta_own, theta=theta, beta_cross=beta_cross,
    scenario=scenario,
)

section_header('Demand & profit curves', caption='Dashed markers show observed baseline vs chosen candidate.')
c1, c2 = st.columns(2)
c1.plotly_chart(
    quantity_price_curve(curve_promo_match,
                         baseline_price=row['mean_p'], baseline_q=row['mean_q'],
                         candidate_price=candidate_price, candidate_q=candidate_q),
)
c2.plotly_chart(
    profit_price_curve(curve_promo_match,
                       baseline_price=row['mean_p'], baseline_profit=row['baseline_profit'],
                       candidate_price=candidate_price, candidate_profit=candidate_profit,
                       cost=cost_eff),
)

st.warning(
    '**Reminder.** These outcomes are **expected lifts under model assumptions** '
    '(log-linear demand, competitor prices held fixed unless overridden, no own-brand '
    'cannibalization, AAC-derived cost). Scenario shocks are applied as a post-hoc '
    'business overlay, not by re-fitting the demand model — use them for what-if '
    'stress tests, not as forecasts. Numbers near the edges of the price grid are '
    'extrapolations and should be read with extra skepticism.'
)
