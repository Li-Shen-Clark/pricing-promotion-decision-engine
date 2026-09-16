"""Page 3 — What-If Simulator: cell selector + sliders + curves."""
from __future__ import annotations
from html import escape
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
    kicker='Simulation workbench',
    title='Simulate one price move.',
    tagline=(
        'Select one product-store cell, set a candidate action, and read the '
        'before/after economics before opening the curves.'
    ),
    chips=[
        'Single product-store',
        'Before / after outcomes',
        'Demand + profit curves',
    ],
)

st.markdown(
    """
    <style>
      .pe-sim-eyebrow {
          font-size: 0.78rem; font-weight: 650; letter-spacing: 0.06em;
          text-transform: uppercase; color: var(--text-muted);
          margin-bottom: 0.35rem;
      }
      .pe-sim-title {
          font-size: 1.12rem; font-weight: 650; color: var(--text);
          line-height: 1.35; margin-bottom: 0.55rem;
      }
      .pe-sim-stat-grid,
      .pe-sim-outcome-grid {
          display: grid; gap: 0.7rem;
      }
      .pe-sim-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .pe-sim-outcome-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .pe-sim-stat,
      .pe-sim-outcome {
          border: 1px solid var(--border); border-radius: 8px;
          background: var(--surface-card); padding: 0.85rem 0.95rem;
          min-height: 6.4rem;
      }
      .pe-sim-stat .label,
      .pe-sim-outcome .label {
          font-size: 0.78rem; color: var(--text-muted); line-height: 1.35;
      }
      .pe-sim-stat .value,
      .pe-sim-outcome .value {
          font-size: 1.34rem; color: var(--text); font-weight: 700;
          line-height: 1.2; margin-top: 0.25rem;
      }
      .pe-sim-stat .detail,
      .pe-sim-outcome .detail {
          font-size: 0.86rem; color: var(--text-muted); line-height: 1.45;
          margin-top: 0.35rem;
      }
      .pe-sim-control-note {
          border-left: 3px solid var(--brand-soft);
          background: var(--surface-2); padding: 0.8rem 0.95rem;
          color: var(--text-muted); font-size: 0.92rem; line-height: 1.5;
          border-radius: 8px; margin-top: 0.75rem;
      }
      @media (max-width: 900px) {
          .pe-sim-stat-grid,
          .pe-sim-outcome-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }
      @media (max-width: 560px) {
          .pe-sim-stat-grid,
          .pe-sim-outcome-grid { grid-template-columns: 1fr; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def _money(value: float, digits: int = 0) -> str:
    return format_money(value, digits)


def _signed_money(value: float, digits: int = 0) -> str:
    return format_money(value, digits, signed=True)


def _signed_number(value: float, digits: int = 1) -> str:
    return f"{value:+,.{digits}f}"


def _stat(label: str, value: str, detail: str) -> str:
    return (
        '<div class="pe-sim-stat">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        f'<div class="detail">{escape(detail)}</div>'
        '</div>'
    )


def _outcome(label: str, value: str, detail: str) -> str:
    return (
        '<div class="pe-sim-outcome">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        f'<div class="detail">{escape(detail)}</div>'
        '</div>'
    )


with st.expander('How to read this simulator', expanded=False):
    st.markdown(
        """
1. Pick one brand-size-store cell.
2. Move the price or promo setting.
3. Read the predicted units, revenue, and profit response.

Sidebar shocks are optional; defaults show the frozen model without scenario overlays.
"""
    )


@st.cache_data
def _cells() -> pd.DataFrame:
    df = load_cells()
    return df.sort_values(['brand_final', 'size_oz_rounded', 'STORE'])


cells = _cells()

# ---- Selector cascade ----
section_header(
    'Choose context',
    caption='The simulator works on one product at one store so the economics stay inspectable.',
)
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
_grid = make_price_grid(row['p_min'], row['p_max'], cost_eff)
p_lo, p_hi = float(_grid.min()), float(_grid.max())

section_header(
    'Simulation workbench',
    caption='Baseline context on the left. Candidate action controls on the right.',
)

context_col, action_col = st.columns([1, 1.15])
with context_col:
    st.markdown('<div class="pe-sim-eyebrow">Selected product-store</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="pe-sim-title">{escape(str(row["brand_final"]))} '
        f'{row["size_oz_rounded"]:.2f}oz · Store {int(row["STORE"])}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pe-sim-stat-grid">'
        + _stat('Average price', _money(row['mean_p'], 2), f"{int(row['n_weeks'])} weeks of history")
        + _stat('Average unit cost', _money(row['mean_cost'], 2), 'Dataset acquisition-cost proxy')
        + _stat('Average units / week', f"{row['mean_q']:,.1f}", 'Observed weekly baseline')
        + _stat('Average profit / week', _money(row['baseline_profit'], 0), 'Observed baseline profit')
        + '</div>',
        unsafe_allow_html=True,
    )

with action_col:
    st.markdown('<div class="pe-sim-eyebrow">Candidate action</div>', unsafe_allow_html=True)
    scenario_label = (
        status_pill('Baseline scenario', 'neutral')
        if scenario.is_baseline else
        status_pill('Stress scenario active', 'warn')
    )
    st.markdown(scenario_label, unsafe_allow_html=True)
    candidate_price = st.slider(
        'Candidate price ($)',
        min_value=round(p_lo, 2), max_value=round(p_hi, 2),
        value=float(round(min(max(row['mean_p'], p_lo), p_hi), 2)),
        step=0.05,
        help=(f'The candidate price stays within a cautious range around the prices '
              f'this product has actually traded at, and must stay above the margin '
              f'floor (${cost_eff * MARGIN_FLOOR_RATIO:.2f} = unit cost ${cost_eff:.2f} '
              f'× {MARGIN_FLOOR_RATIO}).'),
    )
    candidate_promo = st.toggle('Promo on?', value=bool(round(row['mean_promo'])))
    st.markdown(
        f"""
        <div class="pe-sim-control-note">
          Price band: <strong>{_money(p_lo, 2)} to {_money(p_hi, 2)}</strong><br>
          Effective unit cost: <strong>{_money(cost_eff, 2)}</strong><br>
          Margin floor: <strong>{_money(cost_eff * MARGIN_FLOOR_RATIO, 2)}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
delta_pct = (candidate_profit - row['baseline_profit']) / max(row['baseline_profit'], 1e-6) * 100

# ---- Outputs ----
section_header(
    'Outcome preview',
    caption='Frozen-model prediction; sidebar stress controls are included when active.',
)
st.markdown(
    '<div class="pe-sim-outcome-grid">'
    + _outcome(
        'Action price',
        _money(candidate_price, 2),
        f"Current {_money(row['mean_p'], 2)} | {_signed_money(candidate_price - row['mean_p'], 2)}",
    )
    + _outcome(
        'Predicted units / week',
        f'{candidate_q:,.1f}',
        f"Observed {row['mean_q']:,.1f} | {_signed_number(candidate_q - row['mean_q'], 1)}",
    )
    + _outcome(
        'Predicted revenue / week',
        _money(candidate_rev, 0),
        f"Observed {_money(row['baseline_rev'], 0)} | {_signed_money(candidate_rev - row['baseline_rev'], 0)}",
    )
    + _outcome(
        'Predicted profit / week',
        _money(candidate_profit, 0),
        f"Observed {_money(row['baseline_profit'], 0)} | {_signed_money(candidate_profit - row['baseline_profit'], 0)} ({delta_pct:+.1f}%)",
    )
    + '</div>',
    unsafe_allow_html=True,
)
if scenario.is_baseline:
    st.caption(
        'Baseline note: the simulator recomputes outcomes from the fitted demand curve '
        'at the displayed price step, so predicted profit can differ slightly from the '
        'observed weekly baseline. Treat small gaps as model-fit/rounding noise, not as '
        'a data error.'
    )

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
    'Decision evidence curves',
    caption='Dashed markers show the observed average and your chosen candidate. '
            'These curves come from the demo demand model: rival prices stay fixed '
            'unless you use the sidebar shock, and cost uses the dataset\'s accounting '
            'cost proxy. Numbers near the edges of the price band are extrapolations.',
)
c1, c2 = st.columns(2)
c1.plotly_chart(
    quantity_price_curve(curve_promo_match,
                         baseline_price=row['mean_p'], baseline_q=row['mean_q'],
                         candidate_price=candidate_price, candidate_q=candidate_q),
    use_container_width=True,
)
c2.plotly_chart(
    profit_price_curve(curve_promo_match,
                       baseline_price=row['mean_p'], baseline_profit=row['baseline_profit'],
                       candidate_price=candidate_price, candidate_profit=candidate_profit,
                       cost=cost_eff),
    use_container_width=True,
)
