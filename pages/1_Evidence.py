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
    tag="Decision support · Dominick's cereals",
    badges=[
        ('β_own',   f"{MAIN_COEFS['beta_own']:.2f}"),
        ('β_cross', f"+{MAIN_COEFS['beta_cross']:.2f}"),
        ('θ',       f"+{MAIN_COEFS['theta_promo']:.2f}"),
    ],
    workflow=[
        (1, 'Overview',   False),
        (2, 'Evidence',   True),
        (3, 'Simulate',   False),
        (4, 'Optimize',   False),
        (5, 'Validate',   False),
        (6, 'Boundaries', False),
        (7, 'Upload',     False),
    ],
)

page_intro(
    icon='📐',
    kicker='Workflow · Step 2 · Can I trust this model?',
    title='Model Evidence',
    tagline=(
        'The estimated elasticities and the robustness evidence behind them. '
        'These coefficients are frozen and reused everywhere downstream.'
    ),
    chips=[
        'β_own / β_cross / θ_promo',
        'Holdout diagnostic',
        'Coefficient variants',
        'IV-sensitivity tested',
    ],
)

insight_row([
    Insight(
        label='Frozen',
        headline='One model, used end-to-end',
        detail=('Every simulation, optimizer run, and test plan calls these '
                'same coefficients. No silent re-fits.'),
        tone='brand',
    ),
    Insight(
        label='IV-tested',
        headline='OLS and IV agree within 3.0%',
        detail=('β_own moves from −1.73 (OLS) to −1.78 (IV); store-week FE '
                'gives −1.80, a 4.5% shift. Same sign across all three. '
                'First-stage F ≫ 10, CI ratio 1.08.'),
        tone='ok',
    ),
    Insight(
        label='Scope',
        headline='Designed to rank actions, not forecast sales',
        detail=('Point predictions should be read alongside the sensitivity '
                'grid in the simulator. Every recommendation downstream goes '
                'through a controlled A/B test.'),
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
    'are always paired with the sensitivity grid in the **What-If Simulator** — they '
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
