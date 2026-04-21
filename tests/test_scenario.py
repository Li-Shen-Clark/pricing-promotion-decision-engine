"""Scenario overlay invariants.

Covers:
- BASELINE is identity (overlay equals raw model output).
- demand_shock is multiplicative on Q.
- inventory_cap binds as min(Q, cap).
- cost_shock moves the effective cost (and therefore the margin floor) the right way.
- promo_fixed_cost subtracts F·m at the absolute-profit level, and the implied
  effect on profit_lift is exactly -F·(m_cand - m_baseline). This is the
  user-flagged "subtracts once" check, restated more precisely.
"""
from __future__ import annotations
import numpy as np
import pytest

from src.scenario import (
    BASELINE, Scenario,
    apply_demand_overlay, effective_cost, compute_profit, scenario_warnings,
)
from src.optimization import MARGIN_FLOOR_RATIO, make_price_grid


# ---------------------------------------------------------------------------
# §1 — BASELINE is identity
# ---------------------------------------------------------------------------
def test_baseline_is_baseline_flag():
    assert BASELINE.is_baseline is True


def test_demand_overlay_identity_under_baseline():
    q = np.array([10.0, 20.0, 30.0])
    np.testing.assert_array_equal(apply_demand_overlay(q, BASELINE), q)


def test_effective_cost_identity_under_baseline():
    c = np.array([1.5, 2.0, 2.5])
    np.testing.assert_array_equal(effective_cost(c, BASELINE), c)


def test_compute_profit_identity_under_baseline():
    p, q, c, m = np.array([3.0]), np.array([10.0]), np.array([2.0]), np.array([0])
    assert compute_profit(p, q, cost_eff=c, promo=m, scenario=BASELINE)[0] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# §2 — demand_shock is multiplicative
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('shock,expected_ratio', [
    (0.0,   1.00),
    (0.10,  1.10),
    (-0.20, 0.80),
    (0.30,  1.30),
])
def test_demand_shock_is_multiplicative(shock, expected_ratio):
    q = np.array([100.0, 50.0])
    out = apply_demand_overlay(q, Scenario(demand_shock=shock))
    np.testing.assert_allclose(out / q, expected_ratio)


# ---------------------------------------------------------------------------
# §3 — inventory_cap binds as min(Q, cap)
# ---------------------------------------------------------------------------
def test_inventory_cap_binds():
    q = np.array([10.0, 50.0, 100.0])
    out = apply_demand_overlay(q, Scenario(inventory_cap=40.0))
    np.testing.assert_array_equal(out, np.array([10.0, 40.0, 40.0]))


def test_inventory_cap_after_demand_shock():
    """Order of operations: demand_shock first, then inventory_cap."""
    q = np.array([30.0, 40.0])
    sc = Scenario(demand_shock=0.50, inventory_cap=50.0)  # 30→45 (uncapped), 40→60→capped to 50
    out = apply_demand_overlay(q, sc)
    np.testing.assert_allclose(out, np.array([45.0, 50.0]))


# ---------------------------------------------------------------------------
# §4 — cost_shock moves effective_cost AND the margin floor in the price grid
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('shock', [0.0, 0.10, -0.10, 0.40, -0.20])
def test_cost_shock_is_multiplicative(shock):
    c = np.array([1.0, 2.5])
    np.testing.assert_allclose(effective_cost(c, Scenario(cost_shock=shock)), c * (1.0 + shock))


def test_cost_shock_moves_margin_floor_in_price_grid():
    """The price grid's lower bound is max(p_min*0.85, cost_eff*MARGIN_FLOOR_RATIO).
    When cost_eff dominates the floor, raising cost_shock raises the grid's lo."""
    p_min, p_max = 1.0, 5.0
    base_cost = 4.0  # floor = 4*1.05 = 4.20 > p_min*0.85 = 0.85, so margin floor binds
    grid_no_shock = make_price_grid(p_min, p_max, base_cost)
    grid_up_shock = make_price_grid(p_min, p_max, base_cost * 1.20)
    assert grid_up_shock.min() > grid_no_shock.min() + 1e-6
    # Specifically: floor moves by exactly 1.20× when margin floor is the binding term.
    expected_lo_no = base_cost * MARGIN_FLOOR_RATIO
    expected_lo_up = base_cost * 1.20 * MARGIN_FLOOR_RATIO
    assert grid_no_shock.min() == pytest.approx(expected_lo_no)
    assert grid_up_shock.min() == pytest.approx(expected_lo_up)


# ---------------------------------------------------------------------------
# §5 — promo_fixed_cost: absolute and lift-side accounting
# ---------------------------------------------------------------------------
def test_promo_fixed_cost_subtracts_F_times_m_in_absolute_profit():
    """compute_profit(p, q | promo=m, F) = q·(p-c) - F·m. Test both promo states."""
    F = 25.0
    sc = Scenario(promo_fixed_cost=F)
    p = np.array([3.0]); q = np.array([10.0]); c = np.array([1.5])
    pi_promo_off = compute_profit(p, q, cost_eff=c, promo=np.array([0]), scenario=sc)[0]
    pi_promo_on  = compute_profit(p, q, cost_eff=c, promo=np.array([1]), scenario=sc)[0]
    assert pi_promo_off == pytest.approx(15.0)            # 10 * (3 - 1.5) - F*0 = 15
    assert pi_promo_on  == pytest.approx(15.0 - F)        # 10 * (3 - 1.5) - F*1 = -10


def test_promo_fixed_cost_lift_drops_by_minus_F_when_action_turns_promo_on():
    """User's precise formulation:
        cand_profit_F  - cand_profit_0  = -F · m_cand
        baseline_profit_F - baseline_profit_0 = -F · m_baseline
        ⇒ profit_lift_F - profit_lift_0 = -F · (m_cand - m_baseline)

    Concretely: when the candidate action turns promo ON (m_cand=1) and the
    baseline has promo OFF (m_baseline=0), introducing F should reduce the
    *lift* by exactly F. When both promo states match, lift is invariant to F.
    """
    F = 30.0
    p = np.array([3.0]); q = np.array([10.0]); c = np.array([1.5])

    def lift(promo_cand, promo_base, fixed_cost):
        sc = Scenario(promo_fixed_cost=fixed_cost)
        cand = compute_profit(p, q, cost_eff=c, promo=np.array([promo_cand]), scenario=sc)[0]
        base = compute_profit(p, q, cost_eff=c, promo=np.array([promo_base]), scenario=sc)[0]
        return cand - base

    # Action turns promo on (0 → 1): introducing F drops lift by exactly F.
    lift_no_F  = lift(promo_cand=1, promo_base=0, fixed_cost=0.0)
    lift_with_F = lift(promo_cand=1, promo_base=0, fixed_cost=F)
    assert (lift_with_F - lift_no_F) == pytest.approx(-F)

    # Action turns promo off (1 → 0): introducing F INCREASES lift by F (the
    # baseline pays F, the candidate doesn't).
    lift_no_F2  = lift(promo_cand=0, promo_base=1, fixed_cost=0.0)
    lift_with_F2 = lift(promo_cand=0, promo_base=1, fixed_cost=F)
    assert (lift_with_F2 - lift_no_F2) == pytest.approx(+F)

    # No promo state change (1 → 1): F cancels in the lift.
    lift_no_F3  = lift(promo_cand=1, promo_base=1, fixed_cost=0.0)
    lift_with_F3 = lift(promo_cand=1, promo_base=1, fixed_cost=F)
    assert (lift_with_F3 - lift_no_F3) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# §6 — competitor_price_shock feeds beta_cross via log(1+s)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('shock,expected_log', [
    (0.0,   0.0),
    (0.10,  np.log(1.10)),
    (-0.10, np.log(0.90)),
])
def test_log_p_comp_delta_property(shock, expected_log):
    sc = Scenario(competitor_price_shock=shock)
    assert sc.log_p_comp_delta == pytest.approx(expected_log)


# ---------------------------------------------------------------------------
# §7 — scenario_warnings only fires outside the published thresholds
# ---------------------------------------------------------------------------
def test_no_warnings_for_baseline():
    assert scenario_warnings(BASELINE) == []


def test_warning_fires_for_demand_shock_above_threshold():
    flags = scenario_warnings(Scenario(demand_shock=0.30))
    assert any('Demand shock' in f for f in flags)


def test_no_warning_for_demand_shock_at_or_below_threshold():
    # Threshold is strict (>0.20). 0.20 itself should not fire.
    flags = scenario_warnings(Scenario(demand_shock=0.20))
    assert not any('Demand shock' in f for f in flags)


def test_inventory_cap_warning_requires_baseline_q():
    flags = scenario_warnings(Scenario(inventory_cap=5.0), baseline_q=10.0)
    assert any('Inventory cap' in f for f in flags)
    # Without baseline_q the inventory warning cannot fire.
    flags2 = scenario_warnings(Scenario(inventory_cap=5.0))
    assert not any('Inventory cap' in f for f in flags2)
