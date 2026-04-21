"""Plotly figure helpers for the Streamlit MVP.

Each helper returns a `plotly.graph_objects.Figure` ready for `st.plotly_chart`.
Wording follows the project rule: candidate / expected-under-model, not
"optimal" or "deploy".
"""
from __future__ import annotations
from typing import Mapping
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .simulation import n_per_arm

PROJECT_BLUE = '#3a78b8'
PROJECT_GRAY = '#888'
PROJECT_RED  = '#c0504d'
PROJECT_GREEN= '#5da651'


def quantity_price_curve(curve: pd.DataFrame, *, baseline_price: float,
                         baseline_q: float, candidate_price: float,
                         candidate_q: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve['price'], y=curve['q'], mode='lines',
                             name='Predicted demand', line=dict(color=PROJECT_BLUE)))
    fig.add_trace(go.Scatter(x=[baseline_price], y=[baseline_q], mode='markers',
                             name='Observed baseline',
                             marker=dict(color=PROJECT_GRAY, size=11, symbol='diamond')))
    fig.add_trace(go.Scatter(x=[candidate_price], y=[candidate_q], mode='markers',
                             name='Candidate',
                             marker=dict(color=PROJECT_RED, size=12, symbol='star')))
    fig.update_layout(
        xaxis_title='Price ($)',
        yaxis_title='Predicted units / week',
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    return fig


def profit_price_curve(curve: pd.DataFrame, *, baseline_price: float,
                       baseline_profit: float, candidate_price: float,
                       candidate_profit: float, cost: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve['price'], y=curve['profit'], mode='lines',
                             name='Expected profit (model)',
                             line=dict(color=PROJECT_GREEN)))
    fig.add_trace(go.Scatter(x=[baseline_price], y=[baseline_profit], mode='markers',
                             name='Observed baseline',
                             marker=dict(color=PROJECT_GRAY, size=11, symbol='diamond')))
    fig.add_trace(go.Scatter(x=[candidate_price], y=[candidate_profit], mode='markers',
                             name='Candidate',
                             marker=dict(color=PROJECT_RED, size=12, symbol='star')))
    fig.add_vline(x=cost, line=dict(color='black', dash='dot'),
                  annotation_text='unit cost', annotation_position='top right')
    fig.update_layout(
        xaxis_title='Price ($)',
        yaxis_title='Expected gross profit / week ($)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    return fig


def top_recommendations_bar(df: pd.DataFrame, value_col: str = 'profit_lift_abs',
                            label_template: str = '{brand_final} | {size_oz_rounded:.0f}oz | S{STORE}',
                            title: str = '') -> go.Figure:
    labels = [label_template.format(**row) for _, row in df.iterrows()]
    fig = go.Figure(go.Bar(x=df[value_col], y=labels, orientation='h',
                           marker_color=PROJECT_BLUE))
    fig.update_layout(
        xaxis_title='Expected weekly profit lift under model ($)',
        yaxis=dict(autorange='reversed'),
        margin=dict(l=10, r=10, t=30, b=10),
        height=max(320, 28 * len(df)),
        title=title,
    )
    return fig


def coefficients_bar(coef_df: pd.DataFrame) -> go.Figure:
    """Side-by-side bars of own / cross / promo coefficients across model variants."""
    melt = coef_df.melt(id_vars='model',
                        value_vars=['beta_own_price', 'beta_cross_price', 'beta_promo'],
                        var_name='coef', value_name='value')
    label_map = {'beta_own_price':'β_own (log price)',
                 'beta_cross_price':'β_cross (log competitor price)',
                 'beta_promo':'θ (promo on)'}
    melt['coef'] = melt['coef'].map(label_map)
    fig = go.Figure()
    for variant in coef_df['model']:
        sub = melt[melt['model'] == variant]
        fig.add_trace(go.Bar(name=variant, x=sub['coef'], y=sub['value']))
    fig.update_layout(barmode='group',
                      yaxis_title='Coefficient value',
                      margin=dict(l=10, r=10, t=10, b=10),
                      height=350,
                      legend=dict(orientation='h', yanchor='bottom', y=1.02))
    fig.add_hline(y=0, line=dict(color='black', width=0.5))
    return fig


def sample_size_curve(sigma: float, baseline_profit: float,
                      mde_pct_grid: np.ndarray | None = None) -> go.Figure:
    """n_storeweeks per arm vs MDE (% of baseline weekly profit) at three power levels."""
    if mde_pct_grid is None:
        mde_pct_grid = np.linspace(10, 200, 39)
    fig = go.Figure()
    for power in [0.70, 0.80, 0.90]:
        n_grid = [n_per_arm(sigma, baseline_profit * pct / 100, power=power)
                  for pct in mde_pct_grid]
        fig.add_trace(go.Scatter(x=mde_pct_grid, y=n_grid, mode='lines',
                                 name=f'power = {power:.2f}'))
    fig.update_layout(
        xaxis_title='MDE (% of baseline weekly profit)',
        yaxis_title='Required n_storeweeks per arm',
        yaxis_type='log',
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    return fig
