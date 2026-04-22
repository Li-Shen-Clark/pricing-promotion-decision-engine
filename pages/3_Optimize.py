"""Page 4 — Optimize: filter, sort, and inspect candidate cells."""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_cells, load_experiment_candidates, n_per_arm, MAIN_COEFS
from src.optimization import (
    make_price_grid, evaluate_curve, optimize_all_cells, MARGIN_FLOOR_RATIO,
)
from src.plots import profit_price_curve, top_recommendations_bar
from src.scenario import Scenario, BASELINE, scenario_warnings
from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(page_title='Optimize · Find candidates', page_icon='⚙️', layout='wide')
apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag='Decision support for cereal pricing',
)

page_intro(
    icon='',
    kicker='Step 02 · Which products are worth testing first?',
    title='Optimize · Find candidates',
    tagline=(
        'Browse 5,896 product-store combinations ranked by expected weekly '
        'profit lift. The top of the list is where to test next — not where '
        'to deploy.'
    ),
    chips=[
        '5,896 product-store combinations',
        'Filter + drill-down',
        'Re-ranks under your scenario',
    ],
)

insight_row([
    Insight(
        label='1 · Ranked list',
        headline='Top of list = first test, not first rollout',
        detail=('The order is by model-implied weekly profit lift. Treat it as '
                'a test-prioritization queue.'),
        tone='brand',
    ),
    Insight(
        label='2 · Filter + inspect',
        headline='Narrow by brand, size, or history depth',
        detail=('Click any row to see its price-vs-profit curve and the risk '
                'flags (price ceiling, large quantity shift) the model fired.'),
        tone='brand',
    ),
    Insight(
        label='3 · Validate before deploy',
        headline='Every row goes through the Validate page',
        detail=('The optimizer is a search heuristic. The A/B test on the '
                'next page is what turns a candidate into a decision.'),
        tone='note',
    ),
])


@st.cache_data
def _load() -> pd.DataFrame:
    return load_cells()


@st.cache_data
def _load_experiments() -> pd.DataFrame:
    return load_experiment_candidates()


# baseline_cells is the always-on offline-baseline ranking (cached).
# `cells` is the version actually displayed: identical to baseline if
# the scenario sliders are inert, or re-optimized live otherwise. We
# keep both around so the Decision-summary card can show rank-shift
# vs the baseline.
baseline_cells = _load()
cells = baseline_cells

# Scenario warnings live near the top so users see them before reading the table.
_warnings_placeholder = st.empty()

# ---- Sidebar: scenario overlay ----
st.sidebar.markdown('### Scenario controls')
st.sidebar.caption(
    'Optional — leave all shocks at 0 to see the default ranking. '
    'Any non-zero shock re-ranks all 5,896 product-store combinations live.'
)
demand_shock_pct = st.sidebar.slider(
    'Demand shock (%)', min_value=-30, max_value=30, value=0, step=5,
    help='Shifts predicted units up or down by a flat percentage.',
)
cost_shock_pct = st.sidebar.slider(
    'Cost shock (%)', min_value=-25, max_value=40, value=0, step=5,
    help='Shifts the estimated unit cost — and therefore the minimum acceptable margin.',
)
comp_shock_pct = st.sidebar.slider(
    'Competitor price shock (%)', min_value=-25, max_value=25, value=0, step=5,
    help='Shifts the competitor price index up or down. Routes through the cross-price effect.',
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
    cells = optimize_all_cells(baseline_cells, scenario=scenario)
    st.sidebar.success(f'Re-ranked {len(cells):,} product-store combinations under active scenario.')
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
    'Hide candidates at the price ceiling',
    value=False,
    help='98.5% of combinations want the model maximum — toggle on to see only interior optima.',
)
top_n = st.sidebar.slider('Top N to chart', min_value=5, max_value=50, value=15)

# ---- Apply filters ----
mask = (cells['brand_final'].isin(brands) &
        cells['size_oz_rounded'].between(size_min, size_max) &
        (cells['n_weeks'] >= n_weeks_min))
if hide_ceiling:
    mask &= ~cells['opt_hits_upper'].astype(bool)
view = cells.loc[mask].copy()

section_header(f'Filtered view · {len(view):,} of {len(cells):,} product-store combinations',
               caption='Use the sidebar to filter by brand, size, history depth, or hide candidates that hit the historical price ceiling.')

# ---- Top-N bar chart ----
top = view.sort_values('profit_lift_abs', ascending=False).head(top_n)
if len(top) > 0:
    st.plotly_chart(
        top_recommendations_bar(top, title=f'Top {len(top)} candidates by expected weekly profit lift'),
    )

# ---- Table ----
section_header('Candidate table',
               caption='Top 500 rows of the filtered view, sorted by expected weekly profit lift. '
                       'Toggle "Show technical columns" for promo flag, baseline profit, and risk diagnostics.')

show_technical = st.toggle('Show technical columns', value=False,
                           help='Hide by default to keep the decision view clean.')

decision_cols = {
    'brand_final':       'Brand',
    'size_oz_rounded':   'Size (oz)',
    'STORE':             'Store',
    'mean_p':            'Current price',
    'opt_price':         'Test price',
    'profit_lift_abs':   'Expected lift ($/wk)',
    'opt_hits_upper':    'At price ceiling?',
}
technical_cols = {
    'n_weeks':           'Weeks of history',
    'opt_promo':         'Promo (model)',
    'baseline_profit':   'Baseline profit ($/wk)',
    'opt_profit':        'Expected profit ($/wk)',
    'profit_lift_pct':   'Lift (%)',
    'q_lift_ratio':      'Units ratio (cand/base)',
}
display_cols = {**decision_cols, **technical_cols} if show_technical else decision_cols
view_disp = view.sort_values('profit_lift_abs', ascending=False)\
                .head(500)\
                .rename(columns=display_cols)[list(display_cols.values())]
st.dataframe(view_disp.style.format({
    'Size (oz)':                       '{:.2f}',
    'Current price':                   '${:.2f}',
    'Test price':                      '${:.2f}',
    'Expected lift ($/wk)':            '${:.0f}',
    'Baseline profit ($/wk)':          '${:.0f}',
    'Expected profit ($/wk)':          '${:.0f}',
    'Lift (%)':                        '{:.0f}%',
    'Units ratio (cand/base)':         '{:.2f}×',
}), width='stretch', hide_index=True)
# ---- Drill-down ----
section_header('Inspect a single candidate',
               caption='Pick a row to see its profit-vs-price curve and active risk flags.')
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

    # ---------------------------------------------------------------
    # Decision summary — three audit cards under the drill-down.
    # Designed so the recommendation isn't a black box: which
    # constraints bound the optimizer, how stable the choice is
    # under stress, and what an A/B test for this row looks like.
    # ---------------------------------------------------------------
    section_header(
        'Decision summary',
        caption='Where the model hit a constraint, how the choice moves under stress, '
                'and what an A/B test for this candidate would look like.',
    )

    # ---- Pre-compute everything the three cards need ----
    cost_eff = float(row.get('cost_eff', row['mean_cost']))
    margin_floor_price = cost_eff * MARGIN_FLOOR_RATIO
    at_margin_floor = row['opt_price'] <= margin_floor_price + 1e-3
    above_history   = row['opt_price'] > row['p_max']
    below_history   = row['opt_price'] < row['p_min']
    inv_active      = scenario.inventory_cap is not None
    inv_binding     = bool(inv_active and row['opt_q'] >= scenario.inventory_cap - 1e-6)
    comp_shocked    = scenario.competitor_price_shock != 0

    # Rank in baseline vs active scenario, by profit_lift_abs.
    def _rank(df, brand, size, store):
        ranked = df.sort_values('profit_lift_abs', ascending=False).reset_index(drop=True)
        match = ranked[(ranked['brand_final'] == brand) &
                       (ranked['size_oz_rounded'] == size) &
                       (ranked['STORE'] == store)]
        return int(match.index[0]) + 1 if len(match) else None

    baseline_rank = _rank(baseline_cells, row['brand_final'], row['size_oz_rounded'], int(row['STORE']))
    active_rank   = _rank(cells,           row['brand_final'], row['size_oz_rounded'], int(row['STORE']))
    baseline_match = baseline_cells[
        (baseline_cells['brand_final'] == row['brand_final']) &
        (baseline_cells['size_oz_rounded'] == row['size_oz_rounded']) &
        (baseline_cells['STORE'] == int(row['STORE']))
    ]
    baseline_price = float(baseline_match['opt_price'].iloc[0]) if len(baseline_match) else None
    baseline_lift  = float(baseline_match['profit_lift_abs'].iloc[0]) if len(baseline_match) else None

    # Validation card — pull from experiment_candidates if this cell is on the top-10
    # test plan (precomputed with real σ); otherwise fall back to a rough on-the-fly estimate.
    exp_df = _load_experiments()
    exp_match = exp_df[
        (exp_df['brand_final'] == row['brand_final']) &
        (exp_df['size_oz_rounded'] == row['size_oz_rounded']) &
        (exp_df['STORE'] == int(row['STORE']))
    ]
    if len(exp_match):
        ec = exp_match.iloc[0]
        sample_size_n = float(ec['n_storeweeks_per_arm_at_50pct_MDE_80pct_power'])
        sigma_used    = float(ec['profit_std_wk'])
        delta_used    = float(ec['mde_dollars_50pct'])
        sample_source = 'precomputed for top-10'
    else:
        # Heuristic σ ≈ 40% of baseline weekly profit, MDE = 50% of expected lift.
        sigma_used = max(float(row['baseline_profit']) * 0.4, 1.0)
        delta_used = max(abs(float(row['profit_lift_abs'])) * 0.5, 1.0)
        sample_size_n = float(n_per_arm(sigma_used, delta_used))
        sample_source = 'rough estimate · open Validate for the full calculator'

    # ---- Render the three cards ----
    dc1, dc2, dc3 = st.columns(3)

    with dc1:
        st.markdown('**Decision diagnostics**')
        st.caption('Which constraints did the optimizer hit on this row?')
        diags = [
            ('Upper price ceiling',    'Yes — at historical max' if row['opt_hits_upper'] else 'No'),
            ('Margin floor',           f'Yes — at ${margin_floor_price:.2f}' if at_margin_floor else 'No'),
            ('Inventory cap',          ('Yes — binding' if inv_binding
                                        else 'No' if inv_active
                                        else 'Not active')),
            ('Outside historical band', ('Yes (above ' + f'${row["p_max"]:.2f})' if above_history
                                          else 'Yes (below ' + f'${row["p_min"]:.2f})' if below_history
                                          else 'No')),
            ('Competitor prices',      'Held fixed' if not comp_shocked
                                        else f'Shocked {scenario.competitor_price_shock:+.0%}'),
        ]
        for k, v in diags:
            st.markdown(f'- **{k}** — {v}')

    with dc2:
        st.markdown('**Sensitivity readout**')
        st.caption('How does the recommendation hold up under the active scenario?')
        if scenario.is_baseline:
            st.markdown(
                f'- **Active scenario** — none (baseline view)\n'
                f'- **Baseline rank** — #{baseline_rank} of {len(baseline_cells):,}\n'
                f'- **Candidate price** — ${row["opt_price"]:.2f}\n'
                f'- **Expected lift** — ${row["profit_lift_abs"]:+.0f} / wk\n'
                f'- _Move a sidebar slider to stress-test the choice._'
            )
        else:
            rank_delta = (baseline_rank - active_rank) if (baseline_rank and active_rank) else None
            rank_arrow = ('↑' if rank_delta and rank_delta > 0
                          else '↓' if rank_delta and rank_delta < 0
                          else '→')
            price_delta = (row['opt_price'] - baseline_price) if baseline_price else 0
            lift_delta  = (row['profit_lift_abs'] - baseline_lift) if baseline_lift is not None else 0
            st.markdown(
                f'- **Rank shift** — #{baseline_rank} → #{active_rank} '
                f'({rank_arrow} {abs(rank_delta) if rank_delta else 0})\n'
                f'- **Candidate price** — ${baseline_price:.2f} → ${row["opt_price"]:.2f} '
                f'(${price_delta:+.2f})\n'
                f'- **Expected lift** — ${baseline_lift:+.0f} → ${row["profit_lift_abs"]:+.0f} / wk '
                f'(${lift_delta:+.0f})\n'
                f'- **Still recommended?** — '
                + ('Yes — top quintile under both' if (active_rank or 999) <= len(cells) // 5
                   else 'Maybe — re-check before testing')
            )

    with dc3:
        st.markdown('**Validation card**')
        st.caption('What an A/B test for this candidate would look like.')
        st.markdown(
            f'- **Primary metric** — Weekly profit per store\n'
            f'- **Randomization unit** — Store (or store cluster)\n'
            f'- **Treatment** — Test price ${row["opt_price"]:.2f}'
            + (' + promo on' if row['opt_promo'] else '') + '\n'
            f'- **Control** — Current price ${row["mean_p"]:.2f}\n'
            f'- **Guardrails** — ≥40% units drop, margin floor ${margin_floor_price:.2f}, stockout watch\n'
            f'- **Required sample size** — ~{sample_size_n:,.0f} store-weeks per group '
            f'_(50% MDE @ 80% power · {sample_source})_\n'
            f'- _Open the **Validate** page for the full sizing calculator and the test plan markdown._'
        )
