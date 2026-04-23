"""Schema validation + standardization for user-uploaded CSVs (Page 6 — Upload & Score).

This is **scoring-only**: we never re-fit the demand model on uploaded data.
Each uploaded row is treated as its own cell anchor (mean_p / mean_q / mean_promo
all come from the row itself) and scored against the frozen Dominick's cereal
coefficients in `MAIN_COEFS`.

Scope guardrails (intentional):
- No model re-estimation. Uploaded β_own / β_cross / θ would require a full
  panel + identification design; out of MVP scope.
- No causal claims on the user's own data. Predictions are conditional on the
  DFF coefficients applying to the user's category — surface this explicitly
  in the UI banner.
- Strict pre-flight validation. Validation errors block scoring; warnings are
  surfaced but do not block.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import io
import numpy as np
import pandas as pd


REQUIRED_COLUMNS: dict[str, type] = {
    'product_id':       str,
    'store_id':         str,
    'quantity':         float,
    'price':            float,
    'unit_cost':        float,
    'promo':            int,
    'competitor_price': float,
}

OPTIONAL_COLUMNS: dict[str, type] = {
    'brand':     str,
    'size_oz':   float,
    'inventory': float,
}

# Tolerant column-name standardization. Keys are lowercased before lookup.
COLUMN_SYNONYMS: dict[str, str] = {
    'sku':           'product_id',
    'upc':           'product_id',
    'product':       'product_id',
    'item_id':       'product_id',
    'store':         'store_id',
    'location_id':   'store_id',
    'outlet_id':     'store_id',
    'units':         'quantity',
    'qty':           'quantity',
    'units_sold':    'quantity',
    'q':             'quantity',
    'sale_price':    'price',
    'shelf_price':   'price',
    'p':             'price',
    'cost':          'unit_cost',
    'cogs':          'unit_cost',
    'aac':           'unit_cost',
    'on_promo':      'promo',
    'promotion':     'promo',
    'sale':          'promo',
    'p_comp':        'competitor_price',
    'comp_price':    'competitor_price',
    'competitor':    'competitor_price',
    'package_size':  'size_oz',
    'oz':            'size_oz',
    'stock':         'inventory',
    'inv':           'inventory',
}

MAX_ROWS = 50_000   # MVP cap


@dataclass
class ValidationReport:
    ok: bool
    errors:   list[str] = field(default_factory=list)   # blocking
    warnings: list[str] = field(default_factory=list)   # non-blocking
    n_rows_in:  int = 0
    n_rows_out: int = 0
    standardized: Optional[pd.DataFrame] = None
    detected_synonyms: dict[str, str] = field(default_factory=dict)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
_BOOL_MAP = {'1': 1, '0': 0, 'true': 1, 'false': 0, 'yes': 1, 'no': 0,
             'y': 1, 'n': 0, 'on': 1, 'off': 0, 't': 1, 'f': 0}


def _standardize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    renamed: dict[str, str] = {}
    new_cols = []
    for c in df.columns:
        target = COLUMN_SYNONYMS.get(c, c)
        if target != c:
            renamed[c] = target
        new_cols.append(target)
    df.columns = new_cols
    # de-duplicate columns: if synonyms collapsed two columns into one, keep first
    df = df.loc[:, ~df.columns.duplicated()]
    return df, renamed


def _coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col, dtype in REQUIRED_COLUMNS.items():
        if col not in df.columns:
            continue
        if dtype is float:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        elif dtype is int:
            if df[col].dtype == object:
                df[col] = (df[col].astype(str).str.strip().str.lower()
                                  .map(_BOOL_MAP))
            df[col] = pd.to_numeric(df[col], errors='coerce')
        else:  # str
            df[col] = df[col].astype(str).str.strip()
    for col, dtype in OPTIONAL_COLUMNS.items():
        if col in df.columns and dtype is float:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def validate(raw: pd.DataFrame, *, max_rows: int = MAX_ROWS) -> ValidationReport:
    """Run schema + range checks. Returns a report; `standardized` is None on hard failure."""
    report = ValidationReport(ok=False, n_rows_in=len(raw))

    if len(raw) == 0:
        report.errors.append('Uploaded file is empty.')
        return report
    if len(raw) > max_rows:
        report.errors.append(
            f'Uploaded file has {len(raw):,} rows; MVP scoring cap is {max_rows:,}.'
        )
        return report

    df, renamed = _standardize_columns(raw)
    report.detected_synonyms = renamed

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        report.errors.append(
            f'Missing required columns after standardization: {missing}. '
            f'Required schema: {list(REQUIRED_COLUMNS)}. '
            'See the downloadable template for an example.'
        )
        return report

    df = _coerce_types(df)

    # Drop NaN in required cols (after coercion: bad strings → NaN)
    nan_mask = df[list(REQUIRED_COLUMNS)].isna().any(axis=1)
    if nan_mask.any():
        report.warnings.append(
            f'Dropping {int(nan_mask.sum()):,} rows with non-numeric or missing values '
            'in required columns.'
        )
        df = df.loc[~nan_mask].copy()

    # Range checks
    bad_q  = df['quantity'] <= 0
    bad_p  = df['price'] <= 0
    bad_c  = df['unit_cost'] <= 0
    bad_pc = df['competitor_price'] <= 0
    bad_m  = ~df['promo'].isin([0, 1])
    drop_mask = bad_q | bad_p | bad_c | bad_pc | bad_m
    if drop_mask.any():
        report.warnings.append(
            f'Dropping {int(drop_mask.sum()):,} rows with invalid values '
            f'(qty≤0: {int(bad_q.sum())}, price≤0: {int(bad_p.sum())}, '
            f'cost≤0: {int(bad_c.sum())}, comp_price≤0: {int(bad_pc.sum())}, '
            f'promo not in {{0,1}}: {int(bad_m.sum())}).'
        )
        df = df.loc[~drop_mask].copy()

    if len(df) == 0:
        report.errors.append('No valid rows remaining after type coercion + range checks.')
        return report

    # Soft sanity flags
    neg_margin = int((df['price'] <= df['unit_cost']).sum())
    if neg_margin:
        report.warnings.append(
            f'{neg_margin:,} rows have price ≤ unit_cost (non-positive margin). '
            'Profit estimates will be ≤ 0 for these rows.'
        )
    promo_share = float(df['promo'].mean())
    if promo_share > 0.8:
        report.warnings.append(
            f'Promo share is {promo_share:.0%} — unusually high; verify the `promo` column.'
        )
    if (df['competitor_price'] / df['price'] > 5).any() or (df['price'] / df['competitor_price'] > 5).any():
        report.warnings.append(
            'Some rows have price vs. competitor_price ratios outside [0.2, 5]. '
            'Cross-price prediction will extrapolate β_cross outside its training range.'
        )

    df = df.reset_index(drop=True)
    df['promo']      = df['promo'].astype(int)
    df['product_id'] = df['product_id'].astype(str)
    df['store_id']   = df['store_id'].astype(str)

    report.ok = True
    report.n_rows_out = len(df)
    report.standardized = df
    return report


# ----------------------------------------------------------------------------
# Scoring (no re-fit). Uses cell-anchored prediction with each row as its own
# anchor. Caller passes coefficients + Scenario; we never touch the model.
# ----------------------------------------------------------------------------
def score(df: pd.DataFrame,
          *,
          beta_own: float, beta_cross: float, theta: float,
          price_multiplier: float = 0.0,    # e.g. +0.05 = candidate price is 5% above current
          promo_action: str = 'keep',       # 'keep' | 'on' | 'off'
          scenario=None) -> pd.DataFrame:
    """Per-row scoring under a uniform action + scenario overlay.

    Returns a DataFrame with the original required columns plus:
        cand_price, cand_promo, cand_q, cand_revenue, cand_profit,
        baseline_profit, profit_lift_abs, profit_lift_pct.
    """
    from .scenario import (
        BASELINE, apply_demand_overlay, effective_cost, compute_profit,
    )
    if scenario is None:
        scenario = BASELINE

    out = df.copy()
    price = out['price'].to_numpy(dtype='float64')
    qty   = out['quantity'].to_numpy(dtype='float64')
    promo = out['promo'].to_numpy(dtype='float64')
    cost  = out['unit_cost'].to_numpy(dtype='float64')
    pcomp = out['competitor_price'].to_numpy(dtype='float64')

    cand_price = price * (1.0 + price_multiplier)
    if promo_action == 'on':
        cand_promo = np.ones_like(promo)
    elif promo_action == 'off':
        cand_promo = np.zeros_like(promo)
    else:
        cand_promo = promo.copy()

    log_pc_delta = scenario.log_p_comp_delta   # competitor shock, scalar
    log_term = (
        beta_own   * (np.log(cand_price) - np.log(price))
        + theta    * (cand_promo - promo)
        + beta_cross * log_pc_delta
    )
    q_model = qty * np.exp(log_term)
    q_sold  = apply_demand_overlay(q_model, scenario)

    cost_eff = effective_cost(cost, scenario)
    cand_profit = compute_profit(
        cand_price, q_sold, cost_eff=cost_eff,
        promo=cand_promo, scenario=scenario,
    )
    # Do-nothing benchmark: keep the uploaded row's current price/promo/quantity
    # under the same scenario shocks, so lift isolates the proposed action.
    baseline_q       = apply_demand_overlay(qty, scenario)
    baseline_profit  = compute_profit(
        price, baseline_q, cost_eff=cost_eff,
        promo=promo, scenario=scenario,
    )
    lift_abs = cand_profit - baseline_profit
    lift_pct = np.where(np.abs(baseline_profit) > 1e-9,
                        100.0 * lift_abs / baseline_profit, np.nan)

    out['cand_price']      = cand_price
    out['cand_promo']      = cand_promo.astype(int)
    out['cand_q']          = q_sold
    out['cand_revenue']    = q_sold * cand_price
    out['cand_profit']     = cand_profit
    out['baseline_profit'] = baseline_profit
    out['profit_lift_abs'] = lift_abs
    out['profit_lift_pct'] = lift_pct
    return out


# ----------------------------------------------------------------------------
# Downloadable template
# ----------------------------------------------------------------------------
def template_csv() -> str:
    sample = pd.DataFrame({
        'product_id':       ['SKU001', 'SKU001', 'SKU002', 'SKU002'],
        'store_id':         ['STORE_A', 'STORE_B', 'STORE_A', 'STORE_B'],
        'quantity':         [12.5, 8.2, 21.0, 15.4],
        'price':            [3.99, 4.19, 2.49, 2.59],
        'unit_cost':        [2.20, 2.20, 1.40, 1.40],
        'promo':            [0, 1, 0, 0],
        'competitor_price': [3.79, 3.85, 2.55, 2.55],
        'brand':            ['BrandX', 'BrandX', 'BrandY', 'BrandY'],
        'size_oz':          [12.0, 12.0, 18.0, 18.0],
        'inventory':        [100, 100, 150, 150],
    })
    buf = io.StringIO()
    sample.to_csv(buf, index=False)
    return buf.getvalue()
