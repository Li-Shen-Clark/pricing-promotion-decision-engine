"""Page 7 — Upload & Score.

User uploads a CSV → validate schema → standardize → score with the FROZEN
Dominick's cereal coefficients → optional Scenario overlay → per-row + aggregate
predictions, downloadable as CSV. **No model re-estimation** — uploaded data
are evaluated against the pre-estimated demand model only.
"""
from __future__ import annotations
import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import MAIN_COEFS, SENSITIVITY_GRID
from src.scenario import Scenario, scenario_warnings
from src.upload import (
    validate, score, template_csv,
    REQUIRED_COLUMNS, OPTIONAL_COLUMNS, MAX_ROWS,
)
from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(page_title='Upload & Score', page_icon='📤', layout='wide')
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
        (1, 'Overview',   False),
        (2, 'Evidence',   False),
        (3, 'Simulate',   False),
        (4, 'Optimize',   False),
        (5, 'Validate',   False),
        (6, 'Boundaries', False),
        (7, 'Upload',     True),
    ],
)

page_intro(
    icon='📤',
    kicker='Workflow · Step 7 · Can I try this on my own data?',
    title='Upload & Score',
    tagline=(
        'Score a CSV of product rows against the frozen cereal-category coefficients. '
        'No re-estimation — this is a transferability probe, not a new model fit.'
    ),
    chips=[
        'CSV template + validator',
        f'Frozen β_own {MAIN_COEFS["beta_own"]:+.2f}',
        'Scenario overlay',
        'Per-row + aggregate output',
    ],
)

insight_row([
    Insight(
        label='Scope',
        headline='Scoring only — no re-estimation',
        detail=('Rows are scored against the frozen Dominick\'s cereal coefficients. '
                'Full re-estimation on user panels needs its own identification strategy '
                'and held-out validation — that is a follow-up, not this MVP.'),
        tone='brand',
    ),
    Insight(
        label='Transfer assumption',
        headline='Cereal elasticity → your rows',
        detail=('Predictions assume cereal-category elasticity applies to the uploaded '
                'product context. If category, channel, or buyer behaviour differ, read '
                'the magnitudes as directional only.'),
        tone='note',
    ),
    Insight(
        label='Action under stress',
        headline='Scenario overlay separates action from shock',
        detail=('Sidebar sliders apply demand / cost / competitor / inventory shocks. '
                'Profit lift is measured against "do-nothing under the same scenario", '
                'so the reported Δ isolates the action you chose.'),
        tone='ok',
    ),
])

# ---- Template download ----
section_header('Step 1 · Download the CSV template', caption='Optional, but the fastest way to get the schema right the first time.')
st.caption(
    'Required columns: ' + ', '.join(f'`{c}`' for c in REQUIRED_COLUMNS) + '. '
    'Optional columns: ' + ', '.join(f'`{c}`' for c in OPTIONAL_COLUMNS) + '. '
    f'Max rows: {MAX_ROWS:,}. Common synonyms are auto-mapped (e.g. `qty`→`quantity`, `sku`→`product_id`).'
)
st.download_button(
    label='⬇ Download template CSV',
    data=template_csv(),
    file_name='upload_template.csv',
    mime='text/csv',
)

# ---- Upload ----
section_header('Step 2 · Upload your CSV')
upload = st.file_uploader('Pick a CSV file', type=['csv'])

if upload is None:
    st.info('Upload a CSV to continue. Use the template above as a starting point.')
    st.stop()

# Read once, gracefully.
try:
    raw = pd.read_csv(upload)
except Exception as exc:
    st.error(f'Could not parse uploaded file as CSV: `{exc}`')
    st.stop()

# ---- Validate FIRST ----
section_header('Step 3 · Validation report')
report = validate(raw)

c1, c2, c3 = st.columns(3)
c1.metric('Rows uploaded', f'{report.n_rows_in:,}')
c2.metric('Rows kept after validation', f'{report.n_rows_out:,}')
c3.metric('Status', '✅ pass' if report.ok else '❌ fail')

if report.detected_synonyms:
    with st.expander('Column-name synonyms applied', expanded=False):
        for src_col, tgt_col in report.detected_synonyms.items():
            st.markdown(f'- `{src_col}` → `{tgt_col}`')

if report.errors:
    st.error('**Blocking errors — scoring cannot proceed:**\n'
             + '\n'.join(f'- {e}' for e in report.errors))
    st.stop()

if report.warnings:
    st.warning('**Warnings — scoring will proceed:**\n'
               + '\n'.join(f'- {w}' for w in report.warnings))

assert report.standardized is not None  # narrowed by report.ok check above
df = report.standardized

with st.expander(f'Preview standardized data (first 10 of {len(df):,} rows)', expanded=False):
    st.dataframe(df.head(10), width='stretch', hide_index=True)

# ---- Sidebar: coefficients + scenario ----
def _nearest(grid, target):
    return min(grid, key=lambda v: abs(v - target))


with st.sidebar:
    st.markdown('### Demand parameters (frozen)')
    beta_own = st.select_slider(
        'β_own', options=SENSITIVITY_GRID['beta_own'],
        value=_nearest(SENSITIVITY_GRID['beta_own'], MAIN_COEFS['beta_own']),
        format_func=lambda v: f'{v:+.2f}',
    )
    beta_cross = st.select_slider(
        'β_cross', options=SENSITIVITY_GRID['beta_cross'], value=0.0,
        format_func=lambda v: f'{v:+.2f}',
    )
    theta = st.select_slider(
        'θ_promo', options=SENSITIVITY_GRID['theta_promo'],
        value=_nearest(SENSITIVITY_GRID['theta_promo'], MAIN_COEFS['theta_promo']),
        format_func=lambda v: f'+{v:.2f}',
    )

    st.markdown('---')
    st.markdown('### Scenario overlay')
    st.caption('Defaults inert — leave at zero / off to score the uploaded data as-is.')
    demand_shock_pct = st.slider('Demand shock (%)', -30, 30, 0, 5)
    cost_shock_pct   = st.slider('Cost shock (%)',   -25, 40, 0, 5)
    comp_shock_pct   = st.slider('Competitor price shock (%)', -25, 25, 0, 5)
    use_inv_cap = st.toggle('Inventory cap?', value=False)
    inventory_cap_val = (
        st.number_input('Inventory cap (units/wk)', min_value=1.0, max_value=100000.0,
                        value=float(round(df['quantity'].median() * 1.5, 1)), step=1.0)
        if use_inv_cap else None
    )
    promo_fixed_cost = st.number_input(
        'Promo fixed cost ($/wk)', min_value=0.0, max_value=2000.0, value=0.0, step=5.0,
    )

scenario = Scenario(
    demand_shock=demand_shock_pct / 100.0,
    cost_shock=cost_shock_pct / 100.0,
    competitor_price_shock=comp_shock_pct / 100.0,
    inventory_cap=inventory_cap_val,
    promo_fixed_cost=promo_fixed_cost,
)

# ---- Counterfactual action ----
section_header('Step 4 · Counterfactual action',
               caption='One uniform action applied to every row, layered on top of the sidebar scenario overlay.')
st.caption(
    'Pick a uniform action to apply to every uploaded row. The action is layered '
    'on top of the scenario shocks above. Use the price multiplier for portfolio-wide '
    '"raise prices by X%" stress tests.'
)
a1, a2 = st.columns([2, 1])
price_change_pct = a1.slider(
    'Candidate price change (%)',
    min_value=-30, max_value=30, value=0, step=1,
    help='Multiplicative on each row\'s `price`. 0% = keep current price.',
)
promo_action = a2.radio(
    'Promo action',
    options=['keep', 'on', 'off'],
    horizontal=True,
    help='`keep` = use uploaded promo flag. `on`/`off` overrides every row.',
)

# ---- Score ----
scored = score(
    df,
    beta_own=beta_own, beta_cross=beta_cross, theta=theta,
    price_multiplier=price_change_pct / 100.0,
    promo_action=promo_action,
    scenario=scenario,
)

# ---- Scenario warnings ----
sc_flags = scenario_warnings(scenario, baseline_q=float(df['quantity'].median()))
if sc_flags:
    st.warning('**Scenario warnings.**\n' + '\n'.join(f'- {f}' for f in sc_flags))

# ---- Aggregate KPIs ----
section_header('Step 5 · Portfolio outcomes',
               caption='Under the frozen model + scenario overlay + chosen action.')
agg_q_obs    = float(df['quantity'].sum())
agg_rev_obs  = float((df['quantity'] * df['price']).sum())
agg_pi_obs   = float((df['quantity'] * (df['price'] - df['unit_cost'])).sum())
agg_q_cand   = float(scored['cand_q'].sum())
agg_rev_cand = float(scored['cand_revenue'].sum())
agg_pi_cand  = float(scored['cand_profit'].sum())
agg_pi_base  = float(scored['baseline_profit'].sum())   # do-nothing under same scenario
agg_lift     = agg_pi_cand - agg_pi_base
agg_lift_pct = (agg_lift / agg_pi_base * 100) if abs(agg_pi_base) > 1e-6 else np.nan

k1, k2, k3, k4 = st.columns(4)
k1.metric('Total predicted units', f'{agg_q_cand:,.0f}',
          delta=f'{agg_q_cand - agg_q_obs:+,.0f} vs observed')
k2.metric('Total predicted revenue', f'${agg_rev_cand:,.0f}',
          delta=f'${agg_rev_cand - agg_rev_obs:+,.0f} vs observed')
k3.metric('Total predicted profit', f'${agg_pi_cand:,.0f}',
          delta=f'${agg_lift:+,.0f} vs do-nothing under scenario')
k4.metric('Δ profit (%) vs do-nothing under scenario',
          'n/a' if np.isnan(agg_lift_pct) else f'{agg_lift_pct:+.1f}%')

st.caption(
    '"Observed" reflects the rows you uploaded. "Do-nothing under scenario" applies '
    'the same demand / cost / competitor / inventory shocks to your current price + '
    'promo, so the lift number isolates the *action* from the *shock*.'
)

# ---- Per-row table ----
section_header('Per-row predictions')
display_cols = ['product_id', 'store_id', 'quantity', 'price', 'unit_cost',
                'promo', 'competitor_price',
                'cand_price', 'cand_promo', 'cand_q', 'cand_revenue',
                'baseline_profit', 'cand_profit',
                'profit_lift_abs', 'profit_lift_pct']
display_cols = [c for c in display_cols if c in scored.columns]
st.dataframe(
    scored[display_cols].style.format({
        'quantity':         '{:.1f}',
        'price':            '${:.2f}',
        'unit_cost':        '${:.2f}',
        'competitor_price': '${:.2f}',
        'cand_price':       '${:.2f}',
        'cand_q':           '{:.1f}',
        'cand_revenue':     '${:.0f}',
        'baseline_profit':  '${:.0f}',
        'cand_profit':      '${:.0f}',
        'profit_lift_abs':  '${:+.0f}',
        'profit_lift_pct':  '{:+.1f}%',
    }, na_rep='—'),
    width='stretch', hide_index=True,
)

st.download_button(
    label='⬇ Download per-row predictions (CSV)',
    data=scored.to_csv(index=False).encode('utf-8'),
    file_name='upload_scored.csv',
    mime='text/csv',
)

st.caption(
    '**Reminder.** These predictions assume the frozen Dominick\'s cereal elasticities '
    'transfer to the uploaded product. If your category, channel, or buyer behaviour '
    'differs materially from late-90s grocery cereal, treat the magnitudes as '
    'directional only. Re-estimation on user-specific panels is the natural next step '
    'beyond this MVP.'
)
