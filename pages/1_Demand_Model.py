"""Page 1 — Demand Model: frozen coefficients + holdout fit + caveats."""
from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.simulation import load_coefficients, read_markdown, REPORTS
from src.plots import coefficients_bar

st.set_page_config(page_title='Demand Model', page_icon='📐', layout='wide')

st.title('Demand Model — frozen for MVP')
st.caption(
    'Transparent log-log demand with brand-size-store + week fixed effects '
    '(linearmodels AbsorbingLS). No IV, no dynamic stockpiling, no seasonal '
    'interactions. Used for **decision support, not production-grade forecasting**.'
)


@st.cache_data
def _load() -> pd.DataFrame:
    return load_coefficients()

coef = _load()

# ---- Coefficients table ----
st.subheader('Estimated coefficients')
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
    'θ_promo is a conditional sale-code coefficient in log points. The percentage column '
    'uses exp(θ)-1; it should be read as a conditional model association, not a clean causal '
    'promotion effect.'
)

# ---- Coefficient bar chart ----
st.subheader('Own / cross / promo coefficients across model variants')
st.plotly_chart(coefficients_bar(coef))

# ---- Holdout snapshot ----
st.subheader('Holdout fit (last 20 weeks of panel)')
c1, c2, c3 = st.columns(3)
c1.metric('Train rows', '2,423,718')
c2.metric('Median APE', '42.3%')
c3.metric('RMSE (units)', '55.0')
st.caption(
    '**Read with care.** Median APE of 42% is elevated because the MVP uses a '
    'transparent FE demand model **without IV, dynamic stockpiling, or generalizable '
    'seasonal interactions**. Results feed counterfactual decision support, '
    'not production-grade forecasting. Any point forecast should be read alongside '
    'the sensitivity grid in the Counterfactual Simulator page.'
)

# ---- Frozen block from demand_model_summary.md ----
st.markdown('---')
st.subheader('Frozen model summary (from `reports/demand_model_summary.md`)')
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
