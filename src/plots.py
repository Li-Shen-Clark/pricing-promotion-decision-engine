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

from .formatting import format_money
from .simulation import n_per_arm

PROJECT_BLUE = '#3a78b8'
PROJECT_GRAY = '#888'
PROJECT_RED  = '#c0504d'
PROJECT_GREEN= '#5da651'
SOFT_BLUE = '#86aeca'
SOFT_BLUE_LIGHT = '#b7ccd8'
SOFT_GREEN = '#91b39c'
SOFT_RED = '#cf8f8b'
SOFT_GOLD = '#d3b16c'
SOFT_BORDER = '#d9dee8'
PLOT_TEXT = '#1f2933'


def quantity_price_curve(curve: pd.DataFrame, *, baseline_price: float,
                         baseline_q: float, candidate_price: float,
                         candidate_q: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve['price'], y=curve['q'], mode='lines',
                             name='Predicted demand', line=dict(color=PROJECT_BLUE)))
    fig.add_trace(go.Scatter(x=[baseline_price], y=[baseline_q], mode='markers',
                             name='Observed average',
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
                             name='Observed average',
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


def candidate_queue_bar(df: pd.DataFrame, value_col: str = 'profit_lift_abs',
                        title: str = 'Top test priorities') -> go.Figure:
    """A quieter ranked queue chart for the cockpit page."""
    queue = df.sort_values(value_col, ascending=False).reset_index(drop=True).copy()
    queue['rank'] = np.arange(1, len(queue) + 1)
    labels = [
        f"#{row['rank']}  {row['brand_final']} {row['size_oz_rounded']:.0f}oz · S{int(row['STORE'])}"
        for _, row in queue.iterrows()
    ]
    colors = [SOFT_BLUE if rank == 1 else '#d8e6ee' for rank in queue['rank']]
    values = queue[value_col].astype(float)
    max_value = float(values.max()) if len(values) else 0.0

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation='h',
        marker=dict(color=colors, line=dict(color='white', width=1)),
        text=[f"${value:,.0f}/wk" for value in values],
        textposition='outside',
        cliponaxis=False,
        customdata=np.stack([
            queue['brand_final'],
            queue['size_oz_rounded'],
            queue['STORE'],
            queue['mean_p'].map(format_money),
            queue['opt_price'].map(format_money),
            queue['opt_hits_upper'],
        ], axis=-1),
        hovertemplate=(
            '<b>%{customdata[0]} %{customdata[1]:.0f}oz · Store %{customdata[2]}</b><br>'
            'Expected lift: $%{x:.0f}/wk<br>'
            'Current -> test: %{customdata[3]} -> %{customdata[4]}<br>'
            'At price ceiling: %{customdata[5]}<extra></extra>'
        ),
    ))
    fig.update_layout(
        title=dict(text=title, x=0, xanchor='left'),
        xaxis_title='Expected weekly profit lift under model',
        xaxis=dict(
            tickprefix='$',
            gridcolor=SOFT_BORDER,
            zeroline=False,
            range=[0, max_value * 1.22 if max_value else 1],
        ),
        yaxis=dict(
            autorange='reversed',
            title='',
            tickfont=dict(size=11, color=PLOT_TEXT),
        ),
        margin=dict(l=160, r=64, t=50, b=38),
        height=max(320, 25 * len(queue) + 90),
        showlegend=False,
    )
    return fig


def candidate_landscape(top_df: pd.DataFrame, exp_df: pd.DataFrame) -> go.Figure:
    """Top candidates by price move, expected lift, and risk status."""
    key_cols = ['brand_final', 'size_oz_rounded', 'STORE']
    exp_cols = key_cols + ['risk_flag', 'underpowered', 'recommended_test_type']
    df = top_df.merge(exp_df[exp_cols], on=key_cols, how='left').copy()
    df = df.sort_values('profit_lift_abs', ascending=False).reset_index(drop=True)
    df['rank'] = np.arange(1, len(df) + 1)
    df['price_move_pct'] = (df['opt_price'] / df['mean_p'] - 1) * 100
    df['risk_flag'] = df['risk_flag'].fillna('review')
    df['underpowered'] = df['underpowered'].fillna(False).astype(bool)
    df['recommended_test_type'] = df['recommended_test_type'].fillna('review')

    risk_order = ['high', 'medium', 'low', 'review']
    risk_colors = {
        'high': PROJECT_RED,
        'medium': '#d49a1d',
        'low': PROJECT_GREEN,
        'review': PROJECT_GRAY,
    }

    fig = go.Figure()
    for risk in risk_order:
        sub = df[df['risk_flag'] == risk]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub['price_move_pct'],
            y=sub['profit_lift_abs'],
            mode='markers+text',
            name=f'{risk.title()} risk',
            text=[f'#{rank}' for rank in sub['rank']],
            textposition='top center',
            customdata=np.stack([
                sub['brand_final'],
                sub['size_oz_rounded'],
                sub['STORE'],
                sub['mean_p'].map(format_money),
                sub['opt_price'].map(format_money),
                sub['underpowered'],
                sub['recommended_test_type'],
            ], axis=-1),
            hovertemplate=(
                '<b>%{customdata[0]} %{customdata[1]:.0f}oz · Store %{customdata[2]}</b><br>'
                'Price move: %{x:.1f}%<br>'
                'Expected lift: $%{y:.0f}/wk<br>'
                'Current -> test: %{customdata[3]} -> %{customdata[4]}<br>'
                'Needs longer test: %{customdata[5]}<br>'
                'Test type: %{customdata[6]}<extra></extra>'
            ),
            marker=dict(
                color=risk_colors[risk],
                size=np.clip(22 - sub['rank'], 12, 20),
                symbol=['x' if flag else 'circle' for flag in sub['underpowered']],
                line=dict(color='white', width=1),
            ),
        ))

    fig.add_vline(
        x=30,
        line=dict(color=PROJECT_GRAY, dash='dot', width=1),
        annotation_text='+30% price-move watch',
        annotation_position='top right',
    )
    fig.update_layout(
        xaxis_title='Candidate price move vs current',
        yaxis_title='Expected weekly profit lift under model',
        xaxis_ticksuffix='%',
        yaxis_tickprefix='$',
        margin=dict(l=10, r=10, t=10, b=10),
        height=390,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    return fig


def screening_funnel(cells_df: pd.DataFrame, top_df: pd.DataFrame,
                     exp_df: pd.DataFrame) -> go.Figure:
    """Compact funnel from all screened cells to test-ready candidates."""
    ready_now = int((~exp_df['underpowered'].astype(bool)).sum())
    labels = ['Screened cells', 'Shortlisted candidates', 'Sized for current plan']
    values = [len(cells_df), len(top_df), ready_now]
    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo='value',
        textfont=dict(color=PLOT_TEXT),
        marker=dict(
            color=[SOFT_BLUE, SOFT_BLUE_LIGHT, SOFT_GREEN],
            line=dict(color='white', width=1),
        ),
        connector=dict(line=dict(color=SOFT_BORDER, width=1)),
    ))
    fig.update_layout(
        title=dict(text='From panel to launchable test', x=0, xanchor='left'),
        margin=dict(l=10, r=10, t=54, b=18),
        height=310,
        showlegend=False,
    )
    return fig


def risk_validation_bars(exp_df: pd.DataFrame) -> go.Figure:
    """Stacked bar summary of shortlist risk and validation readiness."""
    high = int((exp_df['risk_flag'] == 'high').sum())
    medium = int((exp_df['risk_flag'] == 'medium').sum())
    low = int((exp_df['risk_flag'] == 'low').sum())
    ready = int((~exp_df['underpowered'].astype(bool)).sum())
    needs_longer = int(exp_df['underpowered'].astype(bool).sum())

    fig = go.Figure()
    stacks = [
        ('Ready now', 'Validation', ready, SOFT_GREEN),
        ('Needs longer test', 'Validation', needs_longer, SOFT_RED),
        ('Low risk', 'Risk', low, SOFT_GREEN),
        ('Medium risk', 'Risk', medium, SOFT_GOLD),
        ('High risk', 'Risk', high, SOFT_RED),
    ]
    for name, row, value, color in stacks:
        fig.add_trace(go.Bar(
            name=name,
            y=[row],
            x=[value],
            orientation='h',
            marker=dict(color=color, line=dict(color='white', width=1)),
            text=[value if value else ''],
            textposition='inside',
            textfont=dict(color=PLOT_TEXT),
            hovertemplate=f'{name}: {value}<extra></extra>',
        ))

    fig.update_layout(
        title=dict(text='Shortlist readiness', x=0, xanchor='left'),
        barmode='stack',
        xaxis_title='Top-10 candidates',
        xaxis=dict(range=[0, max(len(exp_df), 1)], dtick=2),
        yaxis=dict(autorange='reversed'),
        margin=dict(l=10, r=10, t=54, b=76),
        height=340,
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.28,
            xanchor='left',
            x=0,
        ),
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
    """n_storeweeks per arm vs MDE (% of observed weekly profit) at three power levels."""
    if mde_pct_grid is None:
        mde_pct_grid = np.linspace(10, 200, 39)
    fig = go.Figure()
    for power in [0.70, 0.80, 0.90]:
        n_grid = [n_per_arm(sigma, baseline_profit * pct / 100, power=power)
                  for pct in mde_pct_grid]
        fig.add_trace(go.Scatter(x=mde_pct_grid, y=n_grid, mode='lines',
                                 name=f'power = {power:.2f}'))
    fig.update_layout(
        xaxis_title='MDE (% of observed weekly profit)',
        yaxis_title='Required n_storeweeks per arm',
        yaxis_type='log',
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
    )
    return fig
