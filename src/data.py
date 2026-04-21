"""Loaders for Dominick's Cereals raw files.

Encapsulates the dtype maps, SALE code cleanup, cost/revenue derivations,
and WEEK→date mapping that live in `notebooks/01_data_cleaning.ipynb`.
Keeps the dirty CSV details in one place so downstream notebooks and
src/demand_model.py can just call `load_panel()`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

WCER_DTYPES: dict[str, str] = {
    'STORE':  'int16',
    'UPC':    'int64',
    'WEEK':   'int16',
    'MOVE':   'int32',
    'QTY':    'int8',
    'PRICE':  'float32',
    'SALE':   'category',
    'PROFIT': 'float32',
    'OK':     'int8',
}
WCER_USECOLS: list[str] = list(WCER_DTYPES.keys())

UPCCER_DTYPES: dict[str, str] = {
    'COM_CODE': 'int32',
    'UPC':      'int64',
    'DESCRIP':  'string',
    'SIZE':     'string',
    'CASE':     'int16',
    'NITEM':    'int64',
}

# Manual documents B/C/S only. G (~11K rows, price/volume behaves like promo)
# and L (1 row) are observed in raw but undocumented. See rawData/README §3.3.
SALE_MAP: dict[str, str] = {
    'B': 'bonus_buy',
    'C': 'coupon',
    'S': 'price_reduction',
    'G': 'unknown_promo',
    'L': 'missing',
}

WEEK_EPOCH = pd.Timestamp('1989-09-14')


def load_wcer(raw_dir: Path) -> pd.DataFrame:
    """Load wcer.csv with the project dtype map; HEX cols skipped."""
    df = pd.read_csv(
        raw_dir / 'wcer.csv',
        dtype=WCER_DTYPES,
        usecols=WCER_USECOLS,
        na_values=[''],
    )
    df['UPC'] = df['UPC'].astype('category')
    return df


def load_upccer(raw_dir: Path) -> pd.DataFrame:
    """Load upccer.csv. Uses latin-1 because raw bytes include 0xd5 ('Õ')."""
    return pd.read_csv(
        raw_dir / 'upccer.csv',
        dtype=UPCCER_DTYPES,
        encoding='latin-1',
    )


def apply_filters(wcer: pd.DataFrame) -> pd.DataFrame:
    """Drop invalid-quality and zero-price rows. Keeps MOVE=0 for now
    (filter at demand-estimation stage, not here).
    """
    mask = (
        (wcer['OK'] == 1) &
        wcer['PROFIT'].between(0, 99) &
        (wcer['PRICE'] > 0)
    )
    return wcer.loc[mask].copy()


def derive_sale_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Produce sale_code_raw (original char) + sale_type_clean (cat) + promo (bool)."""
    out = df.copy()
    out['sale_code_raw'] = out['SALE'].astype('string')
    out['sale_type_clean'] = (
        out['SALE'].astype('string').map(SALE_MAP).fillna('missing').astype('category')
    )
    out['promo'] = out['sale_type_clean'] != 'missing'
    return out


def derive_cost_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """unit_price / unit_cost / revenue per manual §3.4 formulas."""
    out = df.copy()
    out['unit_price'] = out['PRICE'].astype('float32') / out['QTY']
    out['unit_cost'] = out['unit_price'] * (1 - out['PROFIT'] / 100)
    out['revenue'] = out['unit_price'] * out['MOVE']
    return out


def attach_week_date(df: pd.DataFrame) -> pd.DataFrame:
    """Add week_start_date / year / month via Manual §5 decode (Week 1 = 1989-09-14)."""
    out = df.copy()
    out['week_start_date'] = WEEK_EPOCH + pd.to_timedelta((out['WEEK'].astype('int32') - 1) * 7, unit='D')
    out['year'] = out['week_start_date'].dt.year
    out['month'] = out['week_start_date'].dt.month.astype('int8')
    return out


def join_upccer(wcer: pd.DataFrame, upccer: pd.DataFrame) -> pd.DataFrame:
    """Left-join upccer metadata onto wcer, preserving UPC-store-week grain."""
    meta_cols = ['UPC', 'COM_CODE', 'DESCRIP', 'SIZE', 'NITEM']
    base = wcer.copy()
    base['_upc_int'] = base['UPC'].astype('int64')
    out = base.merge(
        upccer[meta_cols], left_on='_upc_int', right_on='UPC', how='left',
        suffixes=('', '_meta'),
    )
    return out.drop(columns=['_upc_int', 'UPC_meta'])


def load_panel(raw_dir: Path) -> pd.DataFrame:
    """End-to-end: load → filter → derive sale + cost + date → join upccer.

    Returns the full UPC-store-week panel (no aggregation).
    """
    wcer = load_wcer(raw_dir)
    upccer = load_upccer(raw_dir)
    wcer = apply_filters(wcer)
    wcer = derive_sale_fields(wcer)
    wcer = derive_cost_revenue(wcer)
    wcer = attach_week_date(wcer)
    panel = join_upccer(wcer, upccer)
    return panel
