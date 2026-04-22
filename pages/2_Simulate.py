"""Page 3 — What-If Simulator: cell selector + sliders + curves."""
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
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(page_title='What-If Simulator', page_icon='🎚', layout='wide')
apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag='Decision support for cereal pricing',
)

page_intro(
    icon='',
    kicker='Step 02 · What happens if I change the price?',
    title='What-If Simulator',
    tagline=(
        'Pick one product at one store. Move the candidate price. See the '
        'predicted units, revenue, and weekly profit response.'
    ),
    chips=[
        'Single product-store',
        'Optional stress-test scenarios',
        'Demand + profit curves',
    ],
)

insight_row([
    Insight(
        label='1 · Pick a product-store',
        headline='One brand-size at one store',
        detail='Use the dropdowns below to choose the product and store.',
        tone='brand',
    ),
    Insight(
        label='2 · Move the price',
        headline='Slide within the historical price band',
        detail=('The slider is bounded by the prices this product has actually '
                'traded at; numbers at the edges are extrapolations and should '
                'be read with extra skepticism.'),
        tone='brand',
    ),
    Insight(
        label='3 · Read the response',
        headline='Predicted units, revenue, and profit',
        detail=('Dashed markers on the curves show the historical baseline vs '
                'your candidate. Sidebar sliders let you stress-test demand, '
                'cost, and competitor shocks.'),
        tone='brand',
    ),
])


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

# ---- Baseline for this product-store ----
section_header('Baseline for this product-store',
               caption='Average over all weeks this product has been observed at this store.')
b1, b2, b3, b4, b5 = st.columns(5)
b1.metric('Average price', f"${row['mean_p']:.2f}")
b2.metric('Average unit cost', f"${row['mean_cost']:.2f}", help='Acquisition cost proxy from the dataset')
b3.metric('Average units / week', f"{row['mean_q']:.1f}")
b4.metric('Average profit / week', f"${row['baseline_profit']:.0f}")
b5.metric('Weeks of history', f"{int(row['n_weeks'])}")

# ---- Sidebar: sensitivity controls ----
def _nearest(grid, target):
    return min(grid, key=lambda v: abs(v - target))


with st.sidebar:
    st.markdown('### Stress-test scenarios')
    st.caption(
        'Optional — defaults are inert. Use these to see how the candidate '
        'profit holds up under a softer demand world, a cost increase, '
        'a competitor price move, or an inventory cap.'
    )
    demand_shock_pct = st.slider(
        'Demand shock (%)', min_value=-30, max_value=30, value=0, step=5,
        help='Shifts the predicted units up or down by a flat percentage.',
    )
    cost_shock_pct = st.slider(
        'Cost shock (%)', min_value=-25, max_value=40, value=0, step=5,
        help='Shifts the unit cost up or down by a flat percentage.',
    )
    comp_shock_pct = st.slider(
        'Competitor price shock (%)', min_value=-25, max_value=25, value=0, step=5,
        help='Shifts the competitor price index up or down. Routes through the cross-price effect.',
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

    st.markdown('---')
    with st.expander('Advanced — override model assumptions', expanded=False):
        st.caption(
            'Override the demo model assumptions to see how sensitive the '
            'result is. Defaults are the values used everywhere else in the app.'
        )
        beta_own = st.select_slider(
            'Price sensitivity',
            options=SENSITIVITY_GRID['beta_own'],
            value=_nearest(SENSITIVITY_GRID['beta_own'], MAIN_COEFS['beta_own']),
            format_func=lambda v: f'{v:+.2f}',
            help='Own-price elasticity (β_own). More negative means a larger '
                 'units drop per 1% price increase.',
        )
        beta_cross = st.select_slider(
            'Rival-price sensitivity',
            options=SENSITIVITY_GRID['beta_cross'], value=0.0,
            format_func=lambda v: f'{v:+.2f}',
            help='Cross-price elasticity (β_cross). Positive means rivals '
                 'raise prices → this product sells more.',
        )
        theta = st.select_slider(
            'Sale-week effect',
            options=SENSITIVITY_GRID['theta_promo'],
            value=_nearest(SENSITIVITY_GRID['theta_promo'], MAIN_COEFS['theta_promo']),
            format_func=lambda v: f'+{v:.2f}',
            help='Conditional promo coefficient θ_promo, in log points; '
                 'exp(θ)-1 ≈ implied % uplift on a sale week.',
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
    help=(f'The candidate price stays within a cautious range around the prices '
          f'this product has actually traded at, and must stay above the margin '
          f'floor (${cost_eff * MARGIN_FLOOR_RATIO:.2f} = unit cost ${cost_eff:.2f} '
          f'× {MARGIN_FLOOR_RATIO}).'),
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

section_header(
    'Demand & profit curves',
    caption='Dashed markers show the observed baseline and your chosen candidate. '
            'These curves come from the demo demand model: rival prices stay fixed '
            'unless you use the sidebar shock, and cost uses the dataset\'s accounting '
            'cost proxy. Numbers near the edges of the price band are extrapolations.',
)
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

