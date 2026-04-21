"""Assertions on Dominick's Cereals frames.

Mirrors the 16 checks in rawData/README §3.8. Each function returns None
on success and raises AssertionError on failure. Thresholds that are
"sanity ranges" (not hard constraints) return a string warning via `check_*`
helpers — callers decide whether to raise or log.
"""
from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

WCER_REQUIRED_COLS: set[str] = {
    'STORE', 'UPC', 'WEEK', 'MOVE', 'QTY', 'PRICE', 'SALE', 'PROFIT', 'OK',
}
UPCCER_REQUIRED_COLS: set[str] = {
    'COM_CODE', 'UPC', 'DESCRIP', 'SIZE', 'CASE', 'NITEM',
}
SALE_ALLOWED: set[str] = {'B', 'C', 'S', 'G', 'L'}
PROFIT_SANITY_RANGE: tuple[float, float] = (5.0, 30.0)


def validate_wcer_schema(df: pd.DataFrame) -> None:
    missing = WCER_REQUIRED_COLS - set(df.columns)
    assert not missing, f'wcer missing columns: {missing}'
    assert df['OK'].isin([0, 1]).all(), 'OK not in {0,1}'
    assert df['WEEK'].between(1, 400).all(), 'WEEK out of [1,400]'
    assert df['QTY'].ge(1).all(), 'QTY < 1'
    assert df['MOVE'].ge(0).all(), 'MOVE < 0'
    assert df['PRICE'].ge(0).all(), 'PRICE < 0'


def validate_upccer_schema(df: pd.DataFrame) -> None:
    missing = UPCCER_REQUIRED_COLS - set(df.columns)
    assert not missing, f'upccer missing columns: {missing}'
    assert df['UPC'].is_unique, 'upccer.UPC not unique'


def validate_sale_codes(df: pd.DataFrame) -> Optional[str]:
    """Return a warning string if unknown SALE codes appear; None otherwise."""
    observed = set(df['SALE'].dropna().unique().tolist()) - {''}
    unknown = observed - SALE_ALLOWED
    if unknown:
        return f'Unknown SALE codes observed: {unknown}'
    return None


def validate_uniqueness(df: pd.DataFrame,
                         keys: Iterable[str] = ('UPC', 'STORE', 'WEEK')) -> None:
    dup = df.duplicated(subset=list(keys)).sum()
    assert dup == 0, f'{dup} duplicate rows on {list(keys)}'


def check_profit_sanity(df: pd.DataFrame) -> Optional[str]:
    """Return warning if post-filter PROFIT median is outside the sanity range.

    Hard filter (PROFIT ∈ [0, 99)) lives in data.apply_filters;
    this is a plausibility check for DFF retail gross margin on Cereals.
    """
    lo, hi = PROFIT_SANITY_RANGE
    med = float(df['PROFIT'].median())
    if lo <= med <= hi:
        return None
    return f'PROFIT median = {med:.1f}% outside sanity range [{lo}, {hi}]'


def validate_join_coverage(wcer: pd.DataFrame, upccer: pd.DataFrame) -> None:
    wcer_upcs = set(wcer['UPC'].astype('int64').unique())
    upccer_upcs = set(upccer['UPC'].astype('int64').unique())
    unmatched = wcer_upcs - upccer_upcs
    assert not unmatched, f'{len(unmatched)} wcer UPCs have no upccer metadata'


def validate_bundle_formula(df: pd.DataFrame, rtol: float = 1e-4) -> None:
    """Sanity: Manual revenue formula PRICE × MOVE / QTY matches derived column."""
    sample = df[(df['QTY'] > 1) & (df['MOVE'] > 0) & df.get('revenue', pd.Series()).notna()]
    if sample.empty:
        return  # nothing to check; not an error
    row = sample.iloc[0]
    manual = row['PRICE'] * row['MOVE'] / row['QTY']
    assert abs(manual - row['revenue']) / max(abs(manual), 1e-9) < rtol, (
        f'bundle formula mismatch: manual={manual:.4f} vs derived={row["revenue"]:.4f}'
    )


def run_all(wcer: pd.DataFrame, upccer: pd.DataFrame,
             cleaned: Optional[pd.DataFrame] = None) -> list[str]:
    """Run every check; return a list of warnings (empty on clean data)."""
    warnings: list[str] = []

    validate_wcer_schema(wcer)
    validate_upccer_schema(upccer)
    validate_uniqueness(wcer)
    validate_join_coverage(wcer, upccer)

    w = validate_sale_codes(wcer)
    if w:
        warnings.append(w)

    if cleaned is not None:
        w = check_profit_sanity(cleaned)
        if w:
            warnings.append(w)
        validate_bundle_formula(cleaned)

    return warnings
