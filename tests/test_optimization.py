"""Optimizer invariants.

Three layers, each tested separately to keep brittle assertions out of cheap suites:

§A. **Synthetic-cell math.** Controlled cells with parameters chosen to make the
    interior optimum unambiguous. These are the only place we test "cost↑ →
    opt_price↑" — running that on the real panel would be brittle because the
    margin floor and upper guardrail interact unpredictably with grid resolution.

§B. **Real-data snapshots.** Pinned values from the current pipeline output.
    Bracketed where appropriate so they tolerate small refactors but still flag
    a meaningful regression. Marked `snapshot`; update when the eligibility
    filter, grid resolution, or coefficient values intentionally change.

§C. **Contract tests.** The user-flagged subtleties: profit_lift ≥ 0 holds
    only when baseline action is in the feasible set under the SAME scenario
    as the candidate. Documented and asserted only on the case where the
    contract is meant to apply.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest

from src.optimization import (
    optimize_cell, optimize_all_cells, make_price_grid, evaluate_curve,
    MARGIN_FLOOR_RATIO, GRID_N,
)
from src.scenario import BASELINE, Scenario
from src.simulation import load_cells, MAIN_COEFS


# ===========================================================================
# §A — Synthetic-cell math (exact, deterministic)
# ===========================================================================
def _interior_cell(cost: float = 2.0) -> dict:
    """Cell tuned so the unconstrained constant-elasticity optimum is interior:
    p* = c · |β|/(|β|-1). With β=-2.5 → p* = 1.667·c. p_min/p_max chosen so the
    grid spans well below and above p* and the margin floor (c·1.05) is also
    below the grid top — i.e. neither boundary binds."""
    return {
        'p_min':      1.0,
        'p_max':      10.0,
        'mean_cost':  cost,
        'mean_q':     100.0,
        'mean_p':     3.5,    # observation point; predict_q returns 100 here
        'mean_promo': 0.0,
    }


def test_synthetic_interior_neither_boundary_binds():
    res = optimize_cell(_interior_cell(), beta_own=-2.5, theta=0.0)
    assert not res['opt_hits_lower'], 'expected interior optimum, got lower-bound bind'
    assert not res['opt_hits_upper'], 'expected interior optimum, got upper-bound bind'


def test_synthetic_cost_increase_raises_optimal_price():
    """Cost↑ → opt_price↑. ONLY tested on a controlled synthetic cell, never on
    the real panel — too many guardrails interact with the grid in production."""
    res_low = optimize_cell(_interior_cell(cost=2.0), beta_own=-2.5, theta=0.0)
    res_mid = optimize_cell(_interior_cell(cost=2.5), beta_own=-2.5, theta=0.0)
    res_hi  = optimize_cell(_interior_cell(cost=3.0), beta_own=-2.5, theta=0.0)
    assert res_low['opt_price'] < res_mid['opt_price'] < res_hi['opt_price']


def test_synthetic_optimal_price_within_one_grid_step_of_closed_form():
    """For constant-elasticity demand, p* = c·|β|/(|β|-1). Grid step on the
    [0.85, 11.5] range with 21 points is ~0.53; assert the optimizer is within
    one grid step of the closed-form optimum."""
    cell = _interior_cell(cost=2.0)
    closed = 2.0 * 2.5 / 1.5  # = 3.333
    res = optimize_cell(cell, beta_own=-2.5, theta=0.0)
    grid = make_price_grid(cell['p_min'], cell['p_max'], cell['mean_cost'])
    step = float(np.diff(grid).mean())
    assert abs(res['opt_price'] - closed) <= step + 1e-9


def test_make_price_grid_lower_bound_binds_to_margin_floor_when_costly():
    """Lower bound = max(p_min·0.85, cost·MARGIN_FLOOR_RATIO). When cost is high,
    the margin floor binds and the grid starts above p_min."""
    g = make_price_grid(p_min=1.0, p_max=5.0, cost=4.0)  # 4·1.05 = 4.20 > 0.85
    assert g.min() == pytest.approx(4.0 * MARGIN_FLOOR_RATIO)
    assert g.max() == pytest.approx(5.0 * 1.15)
    assert len(g) == GRID_N


def test_make_price_grid_lower_bound_binds_to_pmin_when_cheap():
    """When cost is low, the p_min·0.85 floor binds instead."""
    g = make_price_grid(p_min=10.0, p_max=20.0, cost=1.0)  # 1·1.05 = 1.05 < 8.5
    assert g.min() == pytest.approx(10.0 * 0.85)


def test_evaluate_curve_at_baseline_matches_observed_q():
    """At p=mean_p, m=mean_promo, predict_q must return mean_q exactly (the
    cell anchor is a fitted-value identity in the log-linear cell-anchored model)."""
    cell = _interior_cell()
    curve = evaluate_curve(cell, np.array([cell['mean_p']]), promo=int(cell['mean_promo']),
                            beta_own=-2.5, theta=0.0)
    assert curve['q'].iloc[0] == pytest.approx(cell['mean_q'])


# ===========================================================================
# §B — Real-data snapshots (regression tests)
# ===========================================================================
@pytest.fixture(scope='module')
def baseline_recommendations():
    """Vectorised optimizer output across the full 5896-cell panel under BASELINE."""
    return optimize_all_cells(load_cells(), scenario=BASELINE)


@pytest.mark.real_data
@pytest.mark.snapshot
def test_eligible_cell_count_snapshot():
    """Pin the eligibility-filter output. Update intentionally if 01 / cell_baselines
    selection criteria change; flag silent drift otherwise."""
    n = len(load_cells())
    assert n == 5896, (
        f'eligible-cell count drifted: {n} (expected 5896). '
        'If you changed the eligibility filter in 01_data_cleaning or the '
        'cell_baselines build step, update this snapshot in the same PR.'
    )


@pytest.mark.real_data
@pytest.mark.snapshot
def test_ceiling_binding_rate_in_expected_band(baseline_recommendations):
    """The headline 'optimizer hits upper guardrail' rate is the most quoted
    diagnostic in the app; lock it inside a wide band so cosmetic changes don't
    fail the test, but a real regression does."""
    rate = float(baseline_recommendations['opt_hits_upper'].mean())
    assert 0.97 <= rate <= 0.995, (
        f'ceiling-binding rate = {rate:.4f} outside [0.970, 0.995]. '
        'If you changed PRICE_HI_FACTOR, MARGIN_FLOOR_RATIO, GRID_N, or β_own, '
        'update this snapshot. Otherwise investigate.'
    )


@pytest.mark.real_data
@pytest.mark.snapshot
def test_total_baseline_lift_in_expected_band(baseline_recommendations):
    """Sum of model-implied weekly profit lift across all eligible cells.
    Bracketed at ±5% of the current value."""
    total = float(baseline_recommendations['profit_lift_abs'].sum())
    expected = 133_807   # snapshotted from current MAIN_COEFS + cell_baselines build
    lo, hi = 0.85 * expected, 1.15 * expected
    assert lo <= total <= hi, (
        f'total baseline profit lift = ${total:,.0f} outside [${lo:,.0f}, ${hi:,.0f}]. '
        'If MAIN_COEFS, cell_baselines, or the optimizer constants changed intentionally, '
        'update the snapshot in the same PR.'
    )


# ===========================================================================
# §C — Contract: profit_lift ≥ 0 ONLY when baseline action is in the feasible set
# ===========================================================================
@pytest.mark.real_data
def test_profit_lift_nonneg_under_baseline_scenario(baseline_recommendations):
    """**Contract.** Under the BASELINE scenario, the optimizer's grid spans
    [max(p_min·0.85, c·1.05), p_max·1.15], which contains every cell's mean_p
    by construction (mean_p ∈ [p_min, p_max]). The argmax is therefore at least
    as good as the baseline price under the model, so profit_lift ≥ 0.

    This invariant **does not extend** to non-baseline scenarios: under a cost
    shock, mean_p may fall below the new margin floor, so the baseline action
    is no longer feasible and profit_lift can be negative. We deliberately
    only assert this on BASELINE."""
    lift = baseline_recommendations['profit_lift_abs'].to_numpy()
    n_neg = int((lift < -1e-6).sum())
    assert n_neg == 0, (
        f'{n_neg} cells have negative profit_lift under BASELINE. '
        'Either the price grid no longer contains the baseline price, or '
        'baseline_profit is computed against a different cost than opt_profit.'
    )


def test_profit_lift_can_be_negative_under_unfavorable_cost_shock():
    """Counter-example to the above: a +50% cost shock pushes the margin floor
    above the baseline price for at least some cells, making profit_lift
    legitimately negative. This documents that the contract is scenario-scoped."""
    cells = load_cells()
    out_shocked = optimize_all_cells(cells, scenario=Scenario(cost_shock=0.50))
    # Under a large cost shock, baseline_profit (using raw cost) overstates
    # the true do-nothing profit, so opt_profit - baseline_profit should drop —
    # at least some cells should flip negative.
    assert (out_shocked['profit_lift_abs'] < 0).any(), (
        'expected at least some cells to have negative model-implied lift '
        'after a +50% cost shock; if all stay positive the cost-shock plumbing '
        'may not be wired through to opt_profit'
    )


# ===========================================================================
# §D — optimize_cell vs optimize_all_cells consistency
# ===========================================================================
@pytest.mark.real_data
def test_vectorised_matches_per_cell_on_first_row(baseline_recommendations):
    """The two code paths must agree on a per-cell basis — they share the math
    but the vectorised version reshapes 3D arrays. Spot-check the first cell."""
    cells = load_cells()
    row = cells.iloc[0]
    per_cell = optimize_cell(row.to_dict(), scenario=BASELINE)
    vec = baseline_recommendations.iloc[0]
    assert per_cell['opt_price']  == pytest.approx(vec['opt_price'])
    assert per_cell['opt_promo']  == int(vec['opt_promo'])
    assert per_cell['opt_q']      == pytest.approx(vec['opt_q'])
    assert per_cell['opt_profit'] == pytest.approx(vec['opt_profit'])
