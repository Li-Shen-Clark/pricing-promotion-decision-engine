"""Scenario overlay: user-defined business shocks layered on top of the frozen demand model.

Design contract
---------------
- A `Scenario` is a dataclass of multiplicative shocks (and one absolute cap).
- All defaults are inert (`0.0` / `None`), so passing `BASELINE` is equivalent
  to no overlay — the optimizer and simulator must produce *identical* numbers.
- Shocks are applied **after** the model prediction, not by re-fitting:
      q_scenario        = predict_q(...) * (1 + demand_shock)
      q_sold            = min(q_scenario, inventory_cap)
      cost_effective    = unit_cost * (1 + cost_shock)
      profit            = (price - cost_effective) * q_sold
                          - promo_fixed_cost * promo_on
- Competitor price shock feeds the `log_p_comp_delta` argument of `predict_q`
  (i.e. it acts through `beta_cross`, not as a post-hoc multiplier).

This keeps `predict_q` a pure model function and confines all business overlay
logic to a single module.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Optional, Sequence
import numpy as np


@dataclass(frozen=True)
class Scenario:
    demand_shock: float = 0.0              # multiplicative on Q_hat
    cost_shock: float = 0.0                # multiplicative on unit cost
    competitor_price_shock: float = 0.0    # multiplicative on competitor price
    inventory_cap: Optional[float] = None  # absolute units/week ceiling on Q
    promo_fixed_cost: float = 0.0          # $/week deducted when promo == 1

    @property
    def is_baseline(self) -> bool:
        return (self.demand_shock == 0.0
                and self.cost_shock == 0.0
                and self.competitor_price_shock == 0.0
                and self.inventory_cap is None
                and self.promo_fixed_cost == 0.0)

    @property
    def log_p_comp_delta(self) -> float:
        """Log-change in the competitor price index implied by the % shock."""
        return float(np.log1p(self.competitor_price_shock))

    def with_(self, **changes) -> 'Scenario':
        return replace(self, **changes)


BASELINE = Scenario()


def apply_demand_overlay(q, scenario: Scenario):
    """Apply demand_shock then inventory_cap. Vectorised over q."""
    q = np.asarray(q, dtype='float64') * (1.0 + scenario.demand_shock)
    if scenario.inventory_cap is not None:
        q = np.minimum(q, float(scenario.inventory_cap))
    return q


def effective_cost(unit_cost, scenario: Scenario):
    """Cost-shocked unit cost. Returns scalar or array matching input."""
    return np.asarray(unit_cost, dtype='float64') * (1.0 + scenario.cost_shock)


def compute_profit(price, q_sold, *, cost_eff, promo, scenario: Scenario):
    """Per-period profit with optional promo fixed cost."""
    price   = np.asarray(price,   dtype='float64')
    q_sold  = np.asarray(q_sold,  dtype='float64')
    cost_eff = np.asarray(cost_eff, dtype='float64')
    promo_arr = np.asarray(promo, dtype='float64')
    profit = q_sold * (price - cost_eff)
    if scenario.promo_fixed_cost:
        profit = profit - float(scenario.promo_fixed_cost) * promo_arr
    return profit


# --- Risk flags surfaced in the UI when the scenario leaves a sane range ----

DEMAND_STRESS_THRESHOLD = 0.20      # |demand_shock| > 20%
COST_STRESS_THRESHOLD   = 0.25      # cost_shock > +25%
COMP_STRESS_THRESHOLD   = 0.15      # |competitor_price_shock| > 15%


def scenario_warnings(scenario: Scenario,
                      *,
                      baseline_q: Optional[float] = None) -> list[str]:
    """Return human-readable risk flags for the current scenario."""
    flags: list[str] = []
    if scenario.is_baseline:
        return flags
    if abs(scenario.demand_shock) > DEMAND_STRESS_THRESHOLD:
        flags.append(
            f'Demand shock {scenario.demand_shock:+.0%} outside ±20% — treat as stress test, not forecast.'
        )
    if scenario.cost_shock > COST_STRESS_THRESHOLD:
        flags.append(
            f'Cost shock {scenario.cost_shock:+.0%} above +25% — recommendation is highly sensitive to cost assumption.'
        )
    if abs(scenario.competitor_price_shock) > COMP_STRESS_THRESHOLD:
        flags.append(
            f'Competitor price shock {scenario.competitor_price_shock:+.0%} outside historical ±15% — '
            'extrapolation on β_cross.'
        )
    if (scenario.inventory_cap is not None
            and baseline_q is not None
            and scenario.inventory_cap < baseline_q):
        flags.append(
            f'Inventory cap ({scenario.inventory_cap:.0f} units/wk) below baseline mean Q '
            f'({baseline_q:.1f}) — profit estimate is capacity-constrained.'
        )
    if scenario.promo_fixed_cost > 0:
        flags.append(
            f'Promo fixed cost ${scenario.promo_fixed_cost:.0f}/wk active — '
            'promo will be recommended only when its incremental margin clears this cost.'
        )
    return flags
