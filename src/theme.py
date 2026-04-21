"""Shared visual language for the Streamlit app.

Centralises palette, Plotly template, and a small set of markup helpers so
every page looks like part of the same product rather than a notebook wrapper.
Each page that wants the polished look calls :func:`apply_page_theme` once at
the top (after ``st.set_page_config``); downstream renders use ``page_intro``,
``insight_row``, ``metric_card``, ``section_header``, and ``status_pill``.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
PALETTE = {
    'brand':        '#2c5fa8',
    'brand_soft':   '#3a78b8',
    'brand_deep':   '#1e4d82',
    'surface':      '#ffffff',
    'surface_2':    '#f4f6fa',
    'surface_card': '#f8f9fc',
    'border':       '#e4e9f2',
    'text':         '#1f2933',
    'text_muted':   '#5b6b82',
    'ok_fg':        '#1e7e5a',
    'ok_bg':        '#e8f4ef',
    'warn_fg':      '#a36a0a',
    'warn_bg':      '#fcf3e0',
    'alert_fg':     '#a63a3a',
    'alert_bg':     '#fbeaea',
    'note_fg':      '#3a78b8',
    'note_bg':      '#eaf1fa',
    'neutral_fg':   '#5b6b82',
    'neutral_bg':   '#f4f6fa',
}

_TONE_CLASSES = {
    'ok':      ('ok_fg',      'ok_bg'),
    'warn':    ('warn_fg',    'warn_bg'),
    'alert':   ('alert_fg',   'alert_bg'),
    'note':    ('note_fg',    'note_bg'),
    'brand':   ('brand',      'surface_card'),
    'neutral': ('neutral_fg', 'neutral_bg'),
}


# ---------------------------------------------------------------------------
# Plotly template
# ---------------------------------------------------------------------------
_COLORWAY = [
    PALETTE['brand'],
    PALETTE['ok_fg'],
    PALETTE['warn_fg'],
    PALETTE['alert_fg'],
    PALETTE['brand_soft'],
    PALETTE['neutral_fg'],
]

_PRICING_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                  color=PALETTE['text'], size=12),
        colorway=_COLORWAY,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor=PALETTE['border'],
                   zeroline=False, ticks='outside',
                   tickcolor=PALETTE['border']),
        yaxis=dict(showgrid=True, gridcolor=PALETTE['border'],
                   zeroline=False, ticks='outside',
                   tickcolor=PALETTE['border']),
        legend=dict(bgcolor='rgba(0,0,0,0)', borderwidth=0,
                    font=dict(color=PALETTE['text'])),
        margin=dict(l=12, r=12, t=32, b=12),
    )
)


def register_plotly_template() -> None:
    """Register + set the pricing-engine template as the default."""
    pio.templates['pricing_engine'] = _PRICING_TEMPLATE
    pio.templates.default = 'pricing_engine'


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def _css() -> str:
    p = PALETTE
    return f"""
    <style>
      :root {{
        --brand: {p['brand']};
        --brand-soft: {p['brand_soft']};
        --brand-deep: {p['brand_deep']};
        --surface: {p['surface']};
        --surface-2: {p['surface_2']};
        --surface-card: {p['surface_card']};
        --border: {p['border']};
        --text: {p['text']};
        --text-muted: {p['text_muted']};
      }}

      .block-container {{ padding-top: 1.8rem; }}

      h1, h2, h3, h4 {{ color: var(--text); letter-spacing: -0.01em; }}
      h1 {{ font-weight: 700; }}
      h2, h3 {{ font-weight: 600; }}

      /* --- Page intro --- */
      .pe-intro {{
          display: flex; gap: 1.1rem; align-items: flex-start;
          padding: 1.1rem 1.2rem 1.2rem 1.2rem;
          background: var(--surface-card);
          border: 1px solid var(--border);
          border-radius: 14px;
          margin-bottom: 1.4rem;
      }}
      .pe-intro .icon {{
          font-size: 1.8rem; line-height: 1; padding-top: 0.15rem;
      }}
      .pe-intro .body {{ flex: 1; }}
      .pe-intro .kicker {{
          font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
          color: var(--brand); text-transform: uppercase; margin-bottom: 0.2rem;
      }}
      .pe-intro .title {{
          font-size: 1.45rem; font-weight: 700; color: var(--text);
          margin-bottom: 0.35rem; line-height: 1.25;
      }}
      .pe-intro .tagline {{
          color: var(--text-muted); font-size: 0.95rem; line-height: 1.45;
          margin-bottom: 0.65rem;
      }}
      .pe-chips {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
      .pe-chip {{
          font-size: 0.8rem; color: var(--text);
          background: var(--surface); border: 1px solid var(--border);
          padding: 0.2rem 0.6rem; border-radius: 999px;
      }}

      /* --- Insight cards (full-width row block) --- */
      .pe-insight {{
          display: flex; flex-direction: column; gap: 0.3rem;
          padding: 0.95rem 1rem; border-radius: 12px;
          border: 1px solid var(--border); border-left-width: 4px;
          background: var(--surface-card); height: 100%;
      }}
      .pe-insight .label {{
          font-size: 0.72rem; letter-spacing: 0.07em; font-weight: 600;
          text-transform: uppercase;
      }}
      .pe-insight .headline {{
          font-size: 1.05rem; font-weight: 600; color: var(--text);
          line-height: 1.3;
      }}
      .pe-insight .detail {{
          font-size: 0.85rem; color: var(--text-muted); line-height: 1.4;
      }}

      /* --- Status pills --- */
      .pe-pill {{
          display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
          font-size: 0.75rem; font-weight: 600; letter-spacing: 0.02em;
          border: 1px solid transparent;
      }}

      /* --- Section header --- */
      .pe-section {{
          margin: 1.4rem 0 0.5rem 0; padding-bottom: 0.35rem;
          border-bottom: 1px solid var(--border);
      }}
      .pe-section .title {{ font-size: 1.1rem; font-weight: 600; color: var(--text); }}
      .pe-section .caption {{ font-size: 0.85rem; color: var(--text-muted); margin-top: 0.1rem; }}

      /* --- Sidebar brand --- */
      section[data-testid="stSidebar"] .pe-brand {{
          padding: 0.5rem 0 0.9rem 0;
          border-bottom: 1px solid var(--border); margin-bottom: 0.9rem;
      }}
      section[data-testid="stSidebar"] .pe-brand .name {{
          font-size: 1.02rem; font-weight: 700; color: var(--text);
      }}
      section[data-testid="stSidebar"] .pe-brand .tag {{
          font-size: 0.78rem; color: var(--text-muted);
      }}
      section[data-testid="stSidebar"] .pe-badges {{
          display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.4rem;
      }}
      section[data-testid="stSidebar"] .pe-badge {{
          display: inline-block; padding: 0.15rem 0.5rem; border-radius: 6px;
          background: var(--surface-2); border: 1px solid var(--border);
          font-size: 0.78rem; font-family: "SF Mono", "Menlo", monospace;
          color: var(--text);
      }}
      section[data-testid="stSidebar"] .pe-nav {{
          font-size: 0.88rem; color: var(--text-muted); line-height: 1.55;
      }}
      section[data-testid="stSidebar"] .pe-nav .step {{ color: var(--brand); font-weight: 600; }}

      /* Make Streamlit's native alerts feel less shouty when we still use them */
      [data-testid="stAlert"] {{ border-radius: 10px; }}

      /* Metric tightening */
      [data-testid="stMetricValue"] {{ font-weight: 700; color: var(--text); }}
      [data-testid="stMetricLabel"] {{ color: var(--text-muted); font-weight: 500; }}
    </style>
    """


def apply_page_theme() -> None:
    """Inject CSS + register Plotly template. Call once per page."""
    if not st.session_state.get('_pe_theme_applied'):
        register_plotly_template()
        st.session_state['_pe_theme_applied'] = True
    st.markdown(_css(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Component helpers
# ---------------------------------------------------------------------------
def _escape(text: str) -> str:
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))


def page_intro(*, icon: str, kicker: str, title: str, tagline: str,
               chips: Optional[Iterable[str]] = None) -> None:
    """Render a consistent page header block.

    kicker — small uppercase label (e.g. "Workflow · Step 3")
    title  — plain page title
    tagline — one-line positioning
    chips  — optional list of short "what you can do here" items
    """
    chip_html = ''
    if chips:
        chip_html = '<div class="pe-chips">' + ''.join(
            f'<span class="pe-chip">{_escape(c)}</span>' for c in chips
        ) + '</div>'
    st.markdown(
        f"""
        <div class="pe-intro">
          <div class="icon">{icon}</div>
          <div class="body">
            <div class="kicker">{_escape(kicker)}</div>
            <div class="title">{_escape(title)}</div>
            <div class="tagline">{_escape(tagline)}</div>
            {chip_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@dataclass
class Insight:
    label: str
    headline: str
    detail: str
    tone: str = 'brand'   # 'ok' | 'warn' | 'alert' | 'note' | 'brand' | 'neutral'


def _insight_html(card: Insight) -> str:
    fg_key, bg_key = _TONE_CLASSES.get(card.tone, _TONE_CLASSES['brand'])
    fg, bg = PALETTE[fg_key], PALETTE[bg_key]
    return (
        f'<div class="pe-insight" style="background:{bg};border-left-color:{fg};">'
        f'  <div class="label" style="color:{fg};">{_escape(card.label)}</div>'
        f'  <div class="headline">{_escape(card.headline)}</div>'
        f'  <div class="detail">{_escape(card.detail)}</div>'
        f'</div>'
    )


def insight_row(cards: Iterable[Insight]) -> None:
    """Render 2–4 insight cards side-by-side in equal columns."""
    cards = list(cards)
    if not cards:
        return
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        with col:
            st.markdown(_insight_html(card), unsafe_allow_html=True)


def status_pill(text: str, tone: str = 'neutral') -> str:
    """Return an inline HTML pill. Call with ``st.markdown(..., unsafe_allow_html=True)``."""
    fg_key, bg_key = _TONE_CLASSES.get(tone, _TONE_CLASSES['neutral'])
    fg, bg = PALETTE[fg_key], PALETTE[bg_key]
    return (f'<span class="pe-pill" style="color:{fg};background:{bg};'
            f'border-color:{fg}33;">{_escape(text)}</span>')


def section_header(title: str, caption: Optional[str] = None) -> None:
    cap_html = f'<div class="caption">{_escape(caption)}</div>' if caption else ''
    st.markdown(
        f'<div class="pe-section"><div class="title">{_escape(title)}</div>{cap_html}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------------------------
def sidebar_brand(*, name: str, tag: str, badges: Optional[Iterable[tuple[str, str]]] = None,
                  workflow: Optional[Iterable[tuple[int, str, bool]]] = None) -> None:
    """Render the branded sidebar header + optional workflow nav.

    badges — iterable of (label, value) pairs rendered as monospace chips
    workflow — iterable of (step_number, page_name, is_current) triples
    """
    with st.sidebar:
        badges_html = ''
        if badges:
            badges_html = '<div class="pe-badges">' + ''.join(
                f'<span class="pe-badge">{_escape(lbl)} {_escape(val)}</span>'
                for lbl, val in badges
            ) + '</div>'
        st.markdown(
            f"""
            <div class="pe-brand">
              <div class="name">{_escape(name)}</div>
              <div class="tag">{_escape(tag)}</div>
              {badges_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if workflow:
            items = []
            for step, name_, current in workflow:
                style = ' style="color: var(--brand); font-weight: 600;"' if current else ''
                items.append(f'<div{style}><span class="step">{step}.</span> {_escape(name_)}</div>')
            st.markdown(
                f'<div class="pe-nav">{"".join(items)}</div>',
                unsafe_allow_html=True,
            )
