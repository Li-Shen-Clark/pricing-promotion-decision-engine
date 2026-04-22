"""Page 1 — Demand Model: frozen coefficients + holdout fit + caveats."""
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

st.set_page_config(page_title='Demand Model', page_icon='📐', layout='wide')
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
        (1, 'Demand Model',             True),
        (2, 'Counterfactual Simulator', False),
        (3, 'Profit Optimizer',         False),
        (4, 'Experiment Design',        False),
        (5, 'Limitations',              False),
        (6, 'Upload & Score',           False),
    ],
)

page_intro(
    icon='📐',
    kicker='Workflow · Step 1 · Frozen model',
    title='Demand Model',
    tagline=(
        'Inspect the frozen log-log elasticities and the robustness evidence '
        'that justifies using them as the basis for every downstream simulation.'
    ),
    chips=[
        'β_own / β_cross / θ_promo',
        'Holdout diagnostic',
        'Variant comparison',
        'IV-sensitivity tested',
    ],
)

insight_row([
    Insight(
        label='Frozen for MVP',
        headline='One model, read end-to-end',
        detail=('baseline_with_cross: log-log demand with brand-size-store + week FE. '
                'Every simulation, optimizer run, and experiment uses these coefficients.'),
        tone='brand',
    ),
    Insight(
        label='Identification',
        headline='IV-tested: β_own shifts 3.0%',
        detail=('β_own moves from −1.73 (OLS) to −1.78 (IV) under Hausman and over-ID IV. '
                'Store-week FE gives −1.80, a 4.5% shift. Same sign, first-stage F ≫ 10, '
                'CI ratio 1.08 — Robust OLS.'),
        tone='ok',
    ),
    Insight(
        label='Scope',
        headline='Decision support, not forecasting',
        detail=('No dynamic stockpiling or seasonal interactions. Point forecasts should '
                'be read alongside the sensitivity grid, and every recommendation is '
                'validated downstream via A/B test.'),
        tone='note',
    ),
])


@st.cache_data
def _load() -> pd.DataFrame:
    return load_coefficients()

coef = _load()

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
    'are always paired with the sensitivity grid in the Counterfactual Simulator — they '
    'are not intended as production-grade sales forecasts.'
)

# ---- Frozen block from demand_model_summary.md ----
section_header(
    'Frozen model summary',
    caption='Source: `reports/demand_model_summary.md` — the one-pager used in the case study.',
)
md = read_markdown(REPORTS / 'demand_model_summary.md')
# show only the FROZEN block at the top
if '---' in md:
    frozen_block = md.split('---', 2)
    # frozen_block[0] = title, [1] = frozen content, [2] = rest
    st.markdown('---'.join(frozen_block[:2]))
else:
    st.markdown(md[:4000])

with st.expander('Full demand model summary'):
    st.markdown(md)
