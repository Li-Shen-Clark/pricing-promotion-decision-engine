"""Page 3 — Profit Optimizer: filter, sort, and inspect candidate cells."""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_cells, MAIN_COEFS
from src.optimization import (
    make_price_grid, evaluate_curve, optimize_all_cells, MARGIN_FLOOR_RATIO,
)
from src.plots import profit_price_curve, top_recommendations_bar
from src.scenario import Scenario, BASELINE, scenario_warnings

st.set_page_config(page_title='Profit Optimizer', page_icon='⚙️', layout='wide')

st.title('Profit Optimizer')
st.caption(
    'Browse the **5,896 eligible brand-size-store cells** ranked by '
    'expected profit lift under the frozen model. Every row is a '
    '**raise-and-test candidate**, not a deployment instruction.'
)


@st.cache_data
def _load() -> pd.DataFrame:
    return load_cells()


cells = _load()

# Scenario warnings live near the top so users see them before reading the table.
_warnings_placeholder = st.empty()

# ---- Sidebar: scenario overlay ----
st.sidebar.markdown('### Scenario controls')
st.sidebar.caption(
    'Defaults are inert — leave at zero / off to see the frozen offline candidates. '
    'Any non-zero shock triggers a live re-optimization across all eligible cells.'
)
demand_shock_pct = st.sidebar.slider(
    'Demand shock (%)', min_value=-30, max_value=30, value=0, step=5,
    help='Multiplicative on predicted Q.',
)
cost_shock_pct = st.sidebar.slider(
    'Cost shock (%)', min_value=-25, max_value=40, value=0, step=5,
    help='Multiplicative on AAC unit cost. Moves the margin floor too.',
)
comp_shock_pct = st.sidebar.slider(
    'Competitor price shock (%)', min_value=-25, max_value=25, value=0, step=5,
    help='Activates β_cross.',
)
use_inv_cap = st.sidebar.toggle('Inventory cap?', value=False)
inventory_cap_val = (
    st.sidebar.number_input('Inventory cap (units/wk)',
                            min_value=1.0, max_value=10000.0, value=50.0, step=1.0)
    if use_inv_cap else None
)
promo_fixed_cost = st.sidebar.number_input(
    'Promo fixed cost ($/wk)', min_value=0.0, max_value=2000.0, value=0.0, step=5.0,
)

scenario = Scenario(
    demand_shock=demand_shock_pct / 100.0,
    cost_shock=cost_shock_pct / 100.0,
    competitor_price_shock=comp_shock_pct / 100.0,
    inventory_cap=inventory_cap_val,
    promo_fixed_cost=promo_fixed_cost,
)

if not scenario.is_baseline:
    # Live re-optimization. Vectorised, ~10ms across the full panel.
    cells = optimize_all_cells(cells, scenario=scenario)
    st.sidebar.success(f'Re-optimized {len(cells):,} cells under active scenario.')
    sc_flags = scenario_warnings(scenario, baseline_q=float(cells['mean_q'].median()))
    if sc_flags:
        _warnings_placeholder.warning(
            '**Scenario warnings.**\n' + '\n'.join(f'- {f}' for f in sc_flags)
        )
    else:
        _warnings_placeholder.info(
            'Scenario active but within sane bounds — table and curves include the overlay. '
            'Lift is candidate-under-shock minus historical observed profit.'
        )

st.sidebar.markdown('---')

# ---- Filters ----
st.sidebar.markdown('### Filters')
brands = st.sidebar.multiselect('Brand', sorted(cells['brand_final'].unique()),
                                default=sorted(cells['brand_final'].unique()))
size_min, size_max = st.sidebar.slider(
    'Size (oz)',
    min_value=float(cells['size_oz_rounded'].min()),
    max_value=float(cells['size_oz_rounded'].max()),
    value=(float(cells['size_oz_rounded'].min()),
           float(cells['size_oz_rounded'].max())),
)
n_weeks_min = st.sidebar.slider(
    'Min history (weeks)', min_value=52, max_value=int(cells['n_weeks'].max()),
    value=52,
)
hide_ceiling = st.sidebar.checkbox(
    'Hide candidates that hit price ceiling',
    value=False,
    help='98.5% of cells bind at the upper guardrail. Toggle to focus on interior optima.',
)
top_n = st.sidebar.slider('Top N to chart', min_value=5, max_value=50, value=15)

# ---- Apply filters ----
mask = (cells['brand_final'].isin(brands) &
        cells['size_oz_rounded'].between(size_min, size_max) &
        (cells['n_weeks'] >= n_weeks_min))
if hide_ceiling:
    mask &= ~cells['opt_hits_upper'].astype(bool)
view = cells.loc[mask].copy()

st.markdown(f'### Filtered view: **{len(view):,}** of {len(cells):,} eligible cells')

# ---- Top-N bar chart ----
top = view.sort_values('profit_lift_abs', ascending=False).head(top_n)
if len(top) > 0:
    st.plotly_chart(
        top_recommendations_bar(top, title=f'Top {len(top)} candidates by expected weekly profit lift'),
    )

# ---- Table ----
st.markdown('### Candidate table')
display_cols = {
    'brand_final':       'Brand',
    'size_oz_rounded':   'Size (oz)',
    'STORE':             'Store',
    'n_weeks':           'Weeks',
    'mean_p':            'Current price',
    'opt_price':         'Candidate price',
    'opt_promo':         'Promo (model)',
    'baseline_profit':   'Baseline profit ($/wk)',
    'opt_profit':        'Expected profit ($/wk, model)',
    'profit_lift_abs':   'Δ profit ($/wk, model)',
    'profit_lift_pct':   'Δ profit (%)',
    'q_lift_ratio':      'Q ratio (cand/baseline)',
    'opt_hits_upper':    'Hits ceiling?',
}
view_disp = view.sort_values('profit_lift_abs', ascending=False)\
                .head(500)\
                .rename(columns=display_cols)[list(display_cols.values())]
st.dataframe(view_disp.style.format({
    'Size (oz)':                       '{:.2f}',
    'Current price':                   '${:.2f}',
    'Candidate price':                 '${:.2f}',
    'Baseline profit ($/wk)':          '${:.0f}',
    'Expected profit ($/wk, model)':   '${:.0f}',
    'Δ profit ($/wk, model)':          '${:.0f}',
    'Δ profit (%)':                    '{:.0f}%',
    'Q ratio (cand/baseline)':         '{:.2f}×',
}), width='stretch', hide_index=True)
st.caption('Showing top 500 rows of the filtered view, sorted by expected weekly profit lift under model.')

# ---- Drill-down ----
st.markdown('---')
st.markdown('### Inspect a single candidate')
if len(view) == 0:
    st.info('No cells match the current filters.')
else:
    options = view.sort_values('profit_lift_abs', ascending=False).head(50)
    label = options.apply(
        lambda r: f"{r['brand_final']} | {r['size_oz_rounded']:.2f}oz | Store {int(r['STORE'])} "
                  f"(Δprofit ${r['profit_lift_abs']:.0f})",
        axis=1,
    ).tolist()
    pick = st.selectbox('Select a candidate (top 50 of filtered view)', range(len(options)),
                        format_func=lambda i: label[i])
    row = options.iloc[pick].to_dict()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric('Current price',          f"${row['mean_p']:.2f}")
        st.metric('Candidate price',        f"${row['opt_price']:.2f}",
                  delta=f"${row['opt_price'] - row['mean_p']:+.2f}")
        st.metric('Promo recommendation',   'on' if row['opt_promo'] else 'off')
        st.metric('Δ profit ($/wk, model)', f"${row['profit_lift_abs']:+.0f}")
        st.metric('Δ profit (%)',           f"{row['profit_lift_pct']:+.0f}%")

        flags = []
        if row['opt_hits_upper']:
            flags.append('🚧 hits price ceiling (extrapolation risk)')
        if (row['opt_price'] - row['mean_p']) / max(row['mean_p'], 1e-6) > 0.30:
            flags.append('📈 candidate price > +30% vs current')
        if row['q_lift_ratio'] > 1.5 or row['q_lift_ratio'] < 0.5:
            flags.append('🔁 large quantity shift (>±50%)')
        if not flags:
            flags.append('✅ no risk flags tripped')
        st.markdown('**Risk flags:**\n' + '\n'.join(f'- {f}' for f in flags))

    with col2:
        cost_for_grid = float(row.get('cost_eff', row['mean_cost']))
        prices = np.linspace(
            float(make_price_grid(row['p_min'], row['p_max'], cost_for_grid).min()),
            float(make_price_grid(row['p_min'], row['p_max'], cost_for_grid).max()),
            60,
        )
        curve = evaluate_curve(row, prices, int(row['opt_promo']), scenario=scenario)
        st.plotly_chart(
            profit_price_curve(curve,
                               baseline_price=row['mean_p'],
                               baseline_profit=row['baseline_profit'],
                               candidate_price=row['opt_price'],
                               candidate_profit=row['opt_profit'],
                               cost=cost_for_grid),
        )

st.warning(
    'These candidates require **controlled validation** before any price change. '
    'See **Experiment Design** for the test plan and sample-size guidance.'
)
