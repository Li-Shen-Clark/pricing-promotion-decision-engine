"""Product Brief — PM framing for the Pricing Engine."""
from __future__ import annotations
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.theme import (
    apply_page_theme, page_intro, insight_row, Insight,
    sidebar_brand, section_header,
)

st.set_page_config(page_title='Product Brief', page_icon='📌', layout='wide')
apply_page_theme()

sidebar_brand(
    name='Pricing Engine',
    tag='Decision product for pricing teams',
)

page_intro(
    icon='',
    kicker='PM case study',
    title='Product Brief',
    tagline=(
        'A product-management read of the Pricing Engine: user, problem, MVP scope, '
        'success metrics, trade-offs, and roadmap.'
    ),
    chips=[
        'Decision product',
        'Pricing + experimentation',
        'Healthcare pricing next',
    ],
)

section_header('Product thesis')
st.markdown(
    """
Pricing teams do not need another static elasticity table. They need a workflow
that turns pricing evidence into a short list of actions worth testing, explains
where the recommendation could fail, and defines the validation plan before any
rollout decision.
"""
)

section_header('User and problem')
insight_row([
    Insight(
        label='Primary user',
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

section_header(
    'MVP scope',
    caption='The scope is intentionally conservative: prove the decision loop before broadening the domain.',
)
st.markdown(
    """
| Decision | In this MVP | Why |
|---|---|---|
| **User workflow** | Evidence -> Simulate / Optimize -> Validate -> Boundaries | Mirrors how a team should move from analysis to a test decision. |
| **Recommendation type** | Ranked test candidates | Avoids pretending the model can safely auto-deploy prices. |
| **Model choice** | Interpretable fixed-effects demand model | Easier for business reviewers to audit than a black-box forecast. |
| **Optimization** | Bounded grid search across product-store cells | Fast, transparent, and robust enough for interactive scenario testing. |
| **Validation** | Store-level A/B test sizing | Keeps every action tied to a launch decision rule. |
| **Out of scope** | Live deployment, live costs, live inventory, competitor retaliation | These are roadmap items, not hidden assumptions. |
"""
)

section_header('Reviewer path')
r1, r2, r3, r4 = st.columns(4)
with r1:
    st.markdown('**1. Evidence**')
    st.caption('Can we trust the price-response signal enough to use it?')
    st.page_link('pages/1_Evidence.py', label='Open Evidence')
with r2:
    st.markdown('**2. Optimize**')
    st.caption('Which actions rise to the top of the test queue?')
    st.page_link('pages/3_Optimize.py', label='Open Optimize')
with r3:
    st.markdown('**3. Validate**')
    st.caption('How much test evidence is needed before rollout?')
    st.page_link('pages/4_Validate.py', label='Open Validate')
with r4:
    st.markdown('**4. Boundaries**')
    st.caption('What should the product refuse to claim?')
    st.page_link('pages/5_Boundaries.py', label='Open Boundaries')

section_header('Success metrics')
st.markdown(
    """
| Metric family | Example metric | Product reason |
|---|---|---|
| **Activation** | % of users who reach a candidate and validation card | Measures whether the workflow is understandable. |
| **Decision velocity** | Time from product selection to test-ready recommendation | Pricing work often gets stuck between analysis and action. |
| **Decision quality** | % of recommendations with visible risk flags and power status | Prevents model output from becoming unreviewed launch advice. |
| **Experiment quality** | Underpowered tests avoided or resized | Keeps tests from wasting stores, time, and stakeholder trust. |
| **Business outcome** | Validated weekly profit lift from launched tests | Connects the product to economic value. |
"""
)

section_header('Key product trade-offs')
insight_row([
    Insight(
        label='Explainability',
        headline='Interpretable first, predictive second',
        detail=('A pricing PM needs an action a stakeholder can inspect, not just '
                'a high-scoring forecast.'),
        tone='brand',
    ),
    Insight(
        label='Safety',
        headline='Test recommendation, not price automation',
        detail=('The product deliberately stops before deployment and pushes every '
                'candidate through validation.'),
        tone='warn',
    ),
    Insight(
        label='Product shape',
        headline='One workflow beats many notebooks',
        detail=('The app compresses cleaning, modeling, optimization, and experiment '
                'design into a repeatable decision surface.'),
        tone='ok',
    ),
])

section_header(
    'Roadmap: retail pricing -> healthcare pricing & access',
    caption='The next project should reuse the decision-product pattern in a regulated, payer-driven domain.',
)
st.markdown(
    """
| Stage | Product focus | What changes |
|---|---|---|
| **Current** | Retail price/promotion test engine | Demand, profit, risk flags, and A/B test planning from scanner data. |
| **Next** | Healthcare pricing and access decision engine | Add payer constraints, reimbursement logic, patient affordability, value evidence, and access risk. |
| **Longer-term PM path** | Data-heavy product management | Own products where analytics, economics, regulation, and user workflows meet. |
"""
)

st.caption(
    'This is why the current project is framed as a product case study: the core skill is '
    'turning ambiguous pricing decisions into a workflow that helps teams decide what to test, '
    'what to trust, and what to do next.'
)
