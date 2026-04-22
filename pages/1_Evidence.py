"""Page 2 — Model Evidence: frozen coefficients + holdout fit + IV checks."""
from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_coefficients, read_markdown, REPORTS, MAIN_COEFS
from src.plots import coefficients_bar
from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(page_title='Model Evidence', page_icon='📐', layout='wide')
apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag='Decision support for cereal pricing',
)

page_intro(
    icon='📐',
    kicker='Can I trust this model?',
    title='Model Evidence',
    tagline=(
        'A plain-language summary of what the model says about pricing — '
        'and a tested-robustness check below.'
    ),
    chips=[
        'Business translation',
        'Robustness tested',
        'Frozen for the whole app',
    ],
)

# ---- Plain-language business translation ----
section_header('What the model says (in business language)')
insight_row([
    Insight(
        label='Price → Units',
        headline='Raise price, sell fewer units — but margins can rise',
        detail=('A 10% price increase is associated with roughly a 17% drop in '
                'units sold for the same product, on average. Depending on the '
                'starting margin, total weekly profit can still go up.'),
        tone='brand',
    ),
    Insight(
        label='Rivals matter',
        headline='Competitor prices push in the expected direction',
        detail=('When competing brands raise their prices, this brand sells '
                'somewhat more — the relationship has the sign business teams '
                'expect.'),
        tone='brand',
    ),
    Insight(
        label='Promotion weeks',
        headline='Sale weeks sell more, but it is not a clean causal estimate',
        detail=('Weeks flagged as "on sale" sell about 50% more units in this '
                'data — but those weeks also tend to be when vendors fund '
                'promotions and when retailers push inventory, so this is an '
                'association, not a clean uplift.'),
        tone='note',
    ),
])

# ---- Robustness summary ----
section_header(
    'Is this stable under stricter assumptions?',
    caption='Same headline, three different identification choices.',
)
insight_row([
    Insight(
        label='Robustness 1 of 3',
        headline='Standard fit · price-sensitivity index −1.73',
        detail='Brand-size-store and week effects controlled out.',
        tone='brand',
    ),
    Insight(
        label='Robustness 2 of 3',
        headline='Stricter fit · price-sensitivity index −1.80',
        detail='Adds store-week effects to absorb local promo and demand shocks. 4.5% drift.',
        tone='ok',
    ),
    Insight(
        label='Robustness 3 of 3',
        headline='Stricter robustness fit · price-sensitivity index −1.78',
        detail='Uses other-store prices as a sensitivity check; not definitive causal proof. 3.0% drift.',
        tone='ok',
    ),
])

st.caption(
    'Same direction across all three approaches; the headline shifts by less than '
    '5%. Decision rule says: keep the standard fit as the working number, but '
    'remember it was tested.'
)

# ---- Technical detail expander (β / OLS / IV / R² / smearing) ----
with st.expander('Model details — coefficients, standard errors, IV diagnostics', expanded=False):
    st.markdown(
        f"Frozen coefficients (the actual numbers reused everywhere):\n\n"
        f"- **β_own = {MAIN_COEFS['beta_own']:.2f}** — own-price elasticity (log-log).\n"
        f"- **β_cross = +{MAIN_COEFS['beta_cross']:.2f}** — cross-price elasticity (competitor index).\n"
        f"- **θ_promo = +{MAIN_COEFS['theta_promo']:.2f}** — sale-code coefficient in log points; "
        f"`exp(θ)-1 ≈ 54%` conditional uplift, not a clean causal effect.\n\n"
        'See the coefficient table, holdout fit, and robustness variants in the sections '
        'below. Full notebook: `notebooks/03_demand_estimation.ipynb` and '
        '`notebooks/08_iv_sensitivity.ipynb`.'
    )


@st.cache_data
def _load() -> pd.DataFrame:
    return load_coefficients()

coef = _load()

st.markdown('---')
show_tech_evidence = st.toggle(
    'Show technical reviewer view',
    value=False,
    help='Coefficient tables, R²/SE/Smearing diagnostics, holdout fit, '
         'and the frozen model summary doc.',
)

if show_tech_evidence:
    # ---- Coefficients table ----
    section_header(
        'Estimated coefficients',
        caption='Variants differ in controls; baseline_with_cross is frozen for downstream use.',
    )
    display = coef.rename(columns={
        'model':           'Model variant',
        'n_obs':           'n obs',
        'R2_within':       'R² within',
        'beta_own_price':  'β_own',
        'se_own_price':    'SE_own',
        'beta_cross_price':'β_cross',
        'se_cross_price':  'SE_cross',
        'beta_promo':      'θ_promo',
        'se_promo':        'SE_promo',
        'promo_uplift_%':  'Implied promo diff (%)',
        'smearing':        'Smearing S',
    })
    st.dataframe(display.style.format({
        'n obs':            '{:,}',
        'R² within':        '{:.3f}',
        'β_own':            '{:.3f}',
        'SE_own':           '{:.4f}',
        'β_cross':          '{:.3f}',
        'SE_cross':         '{:.4f}',
        'θ_promo':          '{:.3f}',
        'SE_promo':         '{:.4f}',
        'Implied promo diff (%)': '{:.1f}',
        'Smearing S':       '{:.3f}',
    }, na_rep='—'), width='stretch', hide_index=True)

    st.caption(
        'θ_promo is a conditional sale-code coefficient in log points; the percentage column '
        'uses exp(θ)-1 and should be read as a conditional model association, not a clean '
        'causal promotion effect.'
    )

    # ---- Coefficient bar chart ----
    section_header('Own / cross / promo coefficients across model variants')
    st.plotly_chart(coefficients_bar(coef))

    # ---- Holdout snapshot ----
    section_header(
        'Holdout fit',
        caption='Last 20 weeks of the panel held out; reported to size the sensitivity band, '
                'not to claim forecasting accuracy.',
    )
    c1, c2, c3 = st.columns(3)
    c1.metric('Train rows', '2,423,718')
    c2.metric('Median APE', '42.3%')
    c3.metric('RMSE (units)', '55.0')
    st.caption(
        'Median APE of ~42% is expected for a transparent FE demand model without stockpiling '
        'or seasonal interactions. Point forecasts feed counterfactual decision support and '
        'are always paired with the sensitivity grid in the **What-If Simulator** — they '
        'are not intended as production-grade sales forecasts.'
    )

    # ---- Frozen block from demand_model_summary.md ----
    section_header(
        'Frozen model summary',
        caption='Source: `reports/demand_model_summary.md` — the one-pager used in the case study.',
    )
    md = read_markdown(REPORTS / 'demand_model_summary.md')
    if '---' in md:
        frozen_block = md.split('---', 2)
        st.markdown('---'.join(frozen_block[:2]))
    else:
        st.markdown(md[:4000])

    with st.expander('Full demand model summary'):
        st.markdown(md)
