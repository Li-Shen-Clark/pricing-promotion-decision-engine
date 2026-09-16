"""Product Brief — PM framing for the Pricing Engine."""
from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header, safe_page_link,
)

apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag='Decision product for pricing teams',
)

page_intro(
    icon='',
    kicker='Research notes',
    title='Product Brief',
    tagline=(
        'The portfolio essay behind the cockpit: user, problem, MVP scope, '
        'success metrics, trade-offs, and roadmap.'
    ),
    chips=[
        'Decision product',
        'Pricing + experimentation',
        'Healthcare pricing next',
    ],
)

section_header(
    'Product thesis',
    caption='Pricing teams need a testable decision queue, not another static elasticity table.',
)
insight_row([
    Insight(
        label='User',
        headline='Pricing or revenue decision owner',
        detail=('A PM, category manager, pricing analyst, or revenue lead deciding '
                'which price/promo action deserves a controlled test.'),
        tone='brand',
    ),
    Insight(
        label='Job to be done',
        headline='Choose the next price test with confidence',
        detail=('Move from many possible actions to a prioritized queue with '
                'business impact, guardrails, and evidence quality attached.'),
        tone='ok',
    ),
    Insight(
        label='Risk',
        headline='A profitable model output can still be a bad product decision',
        detail=('The product makes uncertainty visible: causality, price ceilings, '
                'power, cannibalization, inventory, and cost quality.'),
        tone='warn',
    ),
])

section_header('Reviewer path')
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.markdown('**1. Model Evidence**')
    st.caption('Can we trust the price-response signal enough to use it?')
    safe_page_link('views/1_Evidence.py', 'Open Model Evidence')
with r2:
    st.markdown('**2. Cockpit**')
    st.caption('Which actions rise to the top of the test queue?')
    safe_page_link('views/3_Optimize.py', 'Open Cockpit')
with r3:
    st.markdown('**3. Validate**')
    st.caption('How much test evidence is needed before rollout?')
    safe_page_link('views/4_Validate.py', 'Open Validate')
with r4:
    st.markdown('**4. Trust & Boundaries**')
    st.caption('What should the product refuse to claim?')
    safe_page_link('views/5_Boundaries.py', 'Open Trust & Boundaries')

section_header('Product decisions')
scope_tab, metrics_tab, roadmap_tab = st.tabs(['MVP Scope', 'Success Metrics', 'Roadmap'])

with scope_tab:
    st.markdown(
        """
| Decision | In this MVP | Why |
|---|---|---|
| **User workflow** | Model Evidence -> Simulator / Cockpit -> Validation -> Trust & Boundaries | Mirrors how a team should move from analysis to a test decision. |
| **Recommendation type** | Ranked test candidates | Avoids pretending the model can safely auto-deploy prices. |
| **Model choice** | Interpretable fixed-effects demand model | Easier for business reviewers to audit than a black-box forecast. |
| **Validation** | Store-level A/B test sizing | Keeps every action tied to a launch decision rule. |
| **Out of scope** | Live deployment, live costs, live inventory, competitor retaliation | These are roadmap items, not hidden assumptions. |
"""
    )

with metrics_tab:
    st.markdown(
        """
| Metric family | Example metric |
|---|---|
| **Activation** | % of users who reach a candidate and validation card |
| **Decision velocity** | Time from product selection to test-ready recommendation |
| **Decision quality** | % of recommendations with visible risk flags and power status |
| **Experiment quality** | Underpowered tests avoided or resized |
| **Business outcome** | Validated weekly profit lift from launched tests |
"""
    )

with roadmap_tab:
    st.markdown(
        """
| Stage | Product focus | What changes |
|---|---|---|
| **Current** | Retail price/promotion test engine | Demand, profit, risk flags, and A/B test planning from scanner data. |
| **Next** | Healthcare pricing and access decision engine | Add payer constraints, reimbursement logic, patient affordability, value evidence, and access risk. |
| **Longer-term PM path** | Data-heavy product management | Own products where analytics, economics, regulation, and user workflows meet. |
"""
    )

with st.expander('Key product trade-offs', expanded=False):
    st.markdown(
        """
- **Interpretable first, predictive second.** A pricing PM needs an action a stakeholder can inspect, not just a high-scoring forecast.
- **Test recommendation, not price automation.** The product deliberately stops before deployment and pushes every candidate through validation.
- **One workflow beats many notebooks.** The app compresses cleaning, modeling, optimization, and experiment design into a repeatable decision surface.
"""
    )

st.caption(
    'This is why the current project is framed as a product case study: the core skill is '
    'turning ambiguous pricing decisions into a workflow that helps teams decide what to test, '
    'what to trust, and what to do next.'
)
