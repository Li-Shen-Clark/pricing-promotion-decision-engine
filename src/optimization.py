"""Profit optimizer over a (price × promo) grid for a single brand-size-store cell.

Mirrors §6–§7 of `04_counterfactual.ipynb` so the app reproduces the same
candidate prices as the offline notebook for the same coefficients.

Scenario overlay
----------------
All entry points accept an optional `scenario: Scenario` argument (see
`src.scenario`). With `scenario=BASELINE` the math is identical to the offline
notebook. With a non-baseline scenario the demand prediction is post-multiplied
by `(1 + demand_shock)`, capped at `inventory_cap`; the unit cost is shifted by
`(1 + cost_shock)`; competitor prices feed `beta_cross` via `log(1 + competitor_price_shock)`;
and promotion incurs an optional `promo_fixed_cost`.
"""
from __future__ import annotations
from typing import Mapping, Optional
import numpy as np
import pandas as pd

from .simulation import predict_q, MAIN_COEFS
from .scenario import (
    Scenario, BASELINE,
    apply_demand_overlay, effective_cost, compute_profit,
)

GRID_N = 21
MARGIN_FLOOR_RATIO = 1.05   # candidate price >= 1.05 * effective unit cost
PRICE_LO_FACTOR    = 0.85
PRICE_HI_FACTOR    = 1.15


def make_price_grid(p_min: float, p_max: float, cost: float,
                    n: int = GRID_N) -> np.ndarray:
    """Bounded price grid for the optimizer.

    Lower bound = max(p_min * 0.85, cost * MARGIN_FLOOR_RATIO).
    Upper bound = p_max * 1.15.
    `cost` here should be the *effective* cost (post-`cost_shock`) when the
    caller has a non-baseline scenario, so that the margin floor moves with it.
    """
    lo = max(p_min * PRICE_LO_FACTOR, cost * MARGIN_FLOOR_RATIO)
    hi = p_max * PRICE_HI_FACTOR
    if lo >= hi:
        return np.array([max(lo, hi)])
    return np.linspace(lo, hi, n)


def _scenario_log_p_comp(scenario: Scenario, fallback: float) -> float:
    """Use the scenario's competitor shock if non-zero, else the legacy arg."""
    if scenario.competitor_price_shock != 0.0:
        return scenario.log_p_comp_delta
    return fallback


def optimize_cell(row: Mapping,
                  *,
                  beta_own: float = MAIN_COEFS['beta_own'],
                  theta: float    = MAIN_COEFS['theta_promo'],
                  beta_cross: float = 0.0,
                  log_p_comp_delta: float = 0.0,
                  scenario: Scenario = BASELINE) -> dict:
    """Grid-search the (price, promo) pair maximising expected gross profit
    under the given scenario overlay.

    Expects `row` to expose: p_min, p_max, mean_cost, mean_q, mean_p, mean_promo.
    Returns a dict with `opt_price`, `opt_promo`, `opt_q`, `opt_rev`, `opt_profit`,
    `opt_hits_upper`, `opt_hits_lower`, plus `cost_eff` and `inventory_binds`
    diagnostics.
    """
    cost_eff = float(effective_cost(row['mean_cost'], scenario))
    grid_p = make_price_grid(row['p_min'], row['p_max'], cost_eff)
    grid_m = np.array([0, 1])
    P, M = np.meshgrid(grid_p, grid_m, indexing='ij')
    log_pc = _scenario_log_p_comp(scenario, log_p_comp_delta)
    Q_model = predict_q(P, M,
                        mean_q=row['mean_q'], mean_p=row['mean_p'],
                        mean_promo=row['mean_promo'],
                        beta_own=beta_own, theta=theta,
                        beta_cross=beta_cross,
                        log_p_comp_delta=log_pc)
    Q_sold = apply_demand_overlay(Q_model, scenario)
    profit = compute_profit(P, Q_sold, cost_eff=cost_eff, promo=M, scenario=scenario)
    rev    = Q_sold * P
    flat_idx = int(np.argmax(profit))
    i, j = np.unravel_index(flat_idx, profit.shape)
    grid_hi = float(grid_p.max())
    grid_lo = float(grid_p.min())
    inventory_binds = bool(
        scenario.inventory_cap is not None
        and Q_sold[i, j] >= float(scenario.inventory_cap) - 1e-9
    )
    return {
        'opt_price':       float(P[i, j]),
        'opt_promo':       int(M[i, j]),
        'opt_q':           float(Q_sold[i, j]),
        'opt_rev':         float(rev[i, j]),
        'opt_profit':      float(profit[i, j]),
        'opt_hits_upper':  bool(P[i, j] >= grid_hi - 1e-9),
        'opt_hits_lower':  bool(P[i, j] <= grid_lo + 1e-9),
        'cost_eff':        cost_eff,
        'inventory_binds': inventory_binds,
    }


def evaluate_curve(row: Mapping, prices: np.ndarray, promo: int,
                   *, beta_own=MAIN_COEFS['beta_own'],
                   theta=MAIN_COEFS['theta_promo'],
                   beta_cross: float = 0.0,
                   log_p_comp_delta: float = 0.0,
                   scenario: Scenario = BASELINE) -> pd.DataFrame:
    """Return a DataFrame of [price, q, revenue, profit] over `prices` under scenario."""
    cost_eff = float(effective_cost(row['mean_cost'], scenario))
    log_pc = _scenario_log_p_comp(scenario, log_p_comp_delta)
    promo_arr = np.full_like(prices, promo, dtype='float64')
    Q_model = predict_q(prices, promo_arr,
                        mean_q=row['mean_q'], mean_p=row['mean_p'],
                        mean_promo=row['mean_promo'],
                        beta_own=beta_own, theta=theta,
                        beta_cross=beta_cross, log_p_comp_delta=log_pc)
    Q_sold = apply_demand_overlay(Q_model, scenario)
    profit = compute_profit(prices, Q_sold, cost_eff=cost_eff,
                            promo=promo_arr, scenario=scenario)
    return pd.DataFrame({
        'price':   prices,
        'q':       Q_sold,
        'revenue': Q_sold * prices,
        'profit':  profit,
    })


# ---------------------------------------------------------------------------
# Vectorised batch re-optimization for the whole cell panel.
# Used by the Profit Optimizer page when the user activates a non-baseline
# scenario and we need to recompute candidates on the fly across ~6k cells.
# ---------------------------------------------------------------------------

def optimize_all_cells(cells: pd.DataFrame,
                       *,
                       beta_own: float = MAIN_COEFS['beta_own'],
                       theta: float    = MAIN_COEFS['theta_promo'],
                       beta_cross: float = 0.0,
                       scenario: Scenario = BASELINE,
                       n_grid: int = GRID_N) -> pd.DataFrame:
    """Vectorised optimizer across every row of `cells`.

    Returns a DataFrame mirroring the columns the app expects from the cached
    `top_recommendations_*` artifacts: brand_final, size_oz_rounded, STORE,
    n_weeks, mean_p, mean_q, mean_cost, baseline_profit,
    opt_price, opt_promo, opt_q, opt_rev, opt_profit,
    profit_lift_abs, profit_lift_pct, q_lift_ratio, opt_hits_upper.

    Memory: builds a (N_cells × n_grid × 2) array of profits — at 5896 cells,
    21 grid pts, 2 promo states this is ~250k floats, well under 10MB.
    """
    cells = cells.reset_index(drop=True)
    N = len(cells)

    p_min  = cells['p_min'].to_numpy(dtype='float64')
    p_max  = cells['p_max'].to_numpy(dtype='float64')
    mean_c = cells['mean_cost'].to_numpy(dtype='float64')
    mean_p = cells['mean_p'].to_numpy(dtype='float64')
    mean_q = cells['mean_q'].to_numpy(dtype='float64')
    mean_m = cells['mean_promo'].to_numpy(dtype='float64')

    cost_eff = mean_c * (1.0 + scenario.cost_shock)         # (N,)
    lo = np.maximum(p_min * PRICE_LO_FACTOR, cost_eff * MARGIN_FLOOR_RATIO)
    hi = p_max * PRICE_HI_FACTOR
    # Degenerate cells (lo >= hi): clamp to a single point so the grid is well-defined.
    hi = np.where(hi <= lo, lo + 1e-6, hi)

    # Grid: shape (N, n_grid). Each row is its own linspace.
    t = np.linspace(0.0, 1.0, n_grid)                       # (G,)
    P = lo[:, None] + (hi - lo)[:, None] * t[None, :]       # (N, G)

    # Build (N, G, 2) tensors for the two promo states.
    P3 = np.repeat(P[:, :, None], 2, axis=2)                # (N, G, 2)
    M3 = np.zeros_like(P3)
    M3[:, :, 1] = 1.0

    log_pc = scenario.log_p_comp_delta                      # scalar
    log_term = (
        beta_own  * (np.log(P3) - np.log(mean_p)[:, None, None])
        + theta   * (M3 - mean_m[:, None, None])
        + beta_cross * log_pc
    )
    Q_model = mean_q[:, None, None] * np.exp(log_term)
    Q_sold  = Q_model * (1.0 + scenario.demand_shock)
    if scenario.inventory_cap is not None:
        Q_sold = np.minimum(Q_sold, float(scenario.inventory_cap))
    profit = Q_sold * (P3 - cost_eff[:, None, None])
    if scenario.promo_fixed_cost:
        profit = profit - float(scenario.promo_fixed_cost) * M3

    # Argmax over (G, 2) per cell.
    flat = profit.reshape(N, -1)
    flat_idx = flat.argmax(axis=1)
    g_idx, m_idx = np.unravel_index(flat_idx, (n_grid, 2))
    rows = np.arange(N)
    opt_p = P3[rows, g_idx, m_idx]
    opt_m = M3[rows, g_idx, m_idx].astype(int)
    opt_q = Q_sold[rows, g_idx, m_idx]
    opt_pi = profit[rows, g_idx, m_idx]
    opt_rev = opt_q * opt_p

    baseline_profit = mean_q * (mean_p - mean_c)   # observational baseline (uses raw cost)
    lift_abs = opt_pi - baseline_profit
    lift_pct = np.where(baseline_profit > 0,
                        100.0 * lift_abs / baseline_profit, np.nan)
    q_ratio = np.where(mean_q > 0, opt_q / mean_q, np.nan)
    hits_upper = opt_p >= P[rows, -1] - 1e-9

    out = pd.DataFrame({
        'brand_final':      cells['brand_final'].values,
        'size_oz_rounded':  cells['size_oz_rounded'].values,
        'STORE':            cells['STORE'].values,
        'n_weeks':          cells['n_weeks'].values,
        'mean_p':           mean_p,
        'mean_q':           mean_q,
        'mean_cost':        mean_c,
        'cost_eff':         cost_eff,
        'baseline_profit':  baseline_profit,
        'opt_price':        opt_p,
        'opt_promo':        opt_m,
        'opt_q':            opt_q,
        'opt_rev':          opt_rev,
        'opt_profit':       opt_pi,
        'profit_lift_abs':  lift_abs,
        'profit_lift_pct':  lift_pct,
        'q_lift_ratio':     q_ratio,
        'opt_hits_upper':   hits_upper,
        # Echo p_min/p_max so downstream evaluate_curve calls work without
        # a re-merge against the original cells dataframe.
        'p_min':            p_min,
        'p_max':            p_max,
        'mean_promo':       mean_m,
    })
    return out
