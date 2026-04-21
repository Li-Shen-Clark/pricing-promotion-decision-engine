"""Feature derivation from raw metadata.

Currently focuses on SIZE parsing. Brand extraction from DESCRIP,
price_per_oz, competitor price, and holiday flags are added in 02_eda.ipynb
and promoted here once stable.
"""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd

# Observed dirty SIZE values in upccer (see reports/data_cleaning_summary.md §5):
#   truncated OZ:   '11.25O', '1.25 O', '17.4 Z', '19.25Z'    (Z = O typo)
#   suffix missing: '14.8', '16.4', '19.25', '12.75'
#   count packs:    '1 CT', '25 CT', '144 CT'
#   assorted:       'ASST', 'ASSTD'
#   bundle:         '2/20 O'  (2-pack of 20 oz)
#   data error:     'end', '1.0'

_SIZE_BUNDLE_RE = re.compile(r'^\s*\d+\s*/\s*(\d+(?:\.\d+)?)\s*O', re.IGNORECASE)
_SIZE_NUM_RE = re.compile(r'(\d+(?:\.\d+)?)')


def parse_size(raw: Optional[str]) -> tuple[float, str]:
    """Return (size_oz, size_kind). size_oz is NaN when unit isn't weight.

    size_kind ∈ {'oz', 'oz_bundle', 'count', 'assorted', 'invalid', 'missing'}.
    """
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return (np.nan, 'missing')
    s = str(raw).strip().upper()
    if s == '' or s == 'END':
        return (np.nan, 'invalid')
    if s.startswith('ASST'):  # 'ASST', 'ASSTD'
        return (np.nan, 'assorted')
    if 'CT' in s:  # '1 CT', '25 CT', '144 CT'
        return (np.nan, 'count')

    # bundle form: '2/20 O' → 20 oz per unit
    m = _SIZE_BUNDLE_RE.match(s)
    if m:
        return (float(m.group(1)), 'oz_bundle')

    # everything else: grab the first number. Applies to '11.25O', '14.8',
    # '17.4 Z' (Z = typo for O), '1.0' (treat as 1.0 oz trial pack).
    m = _SIZE_NUM_RE.search(s)
    if m:
        try:
            return (float(m.group(1)), 'oz')
        except ValueError:
            return (np.nan, 'invalid')
    return (np.nan, 'invalid')


def attach_size_fields(df: pd.DataFrame, size_col: str = 'SIZE') -> pd.DataFrame:
    """Add size_oz (float32) and size_kind (category) columns in place-of-copy."""
    parsed = df[size_col].apply(parse_size)
    out = df.copy()
    out['size_oz'] = parsed.apply(lambda x: x[0]).astype('float32')
    out['size_kind'] = parsed.apply(lambda x: x[1]).astype('category')
    return out


def clean_descrip(descrip: Optional[str]) -> str:
    """Strip DFF-specific control chars (`# < ~ $ *`) and trailing spaces."""
    if descrip is None or (isinstance(descrip, float) and np.isnan(descrip)):
        return ''
    return re.sub(r'[#<~$*]', '', str(descrip)).strip()


def attach_descrip_clean(df: pd.DataFrame, col: str = 'DESCRIP') -> pd.DataFrame:
    out = df.copy()
    out['descrip_clean'] = out[col].apply(clean_descrip).astype('string')
    return out


# ---------------------------------------------------------------------------
# Manufacturer code + brand rules
# ---------------------------------------------------------------------------

def manufacturer_code(upc: int | pd.Series) -> int | pd.Series:
    """UPC // 100000 → manufacturer block. UPC's last 5 digits are product code
    (manual p.9); the remaining high digits identify the manufacturer.
    Using integer division (rather than string-slicing) preserves leading zeros.
    """
    if isinstance(upc, pd.Series):
        return (upc.astype('int64') // 100_000).rename('manufacturer_code')
    return int(upc) // 100_000


# DESCRIP keyword → canonical brand. Ordered: first hit wins.
# Seeded from DFF/Dominick's community conventions; validated in 02_eda
# against manufacturer_code blocks, so this is the *initial* rule set.
BRAND_RULES: list[tuple[str, str]] = [
    (r'\bKELL',                 "Kellogg's"),
    (r'\bK /?G\b',              "Kellogg's"),
    (r'\bGEN +M\b',             'General Mills'),
    (r'\bGM\b',                 'General Mills'),
    (r'\bGENERAL',              'General Mills'),
    (r'\bPOST\b',               'Post'),
    (r'\bQUAKER\b',             'Quaker'),
    (r'\bQKR\b',                'Quaker'),
    (r'\bRALSTN?\b',            'Ralston'),
    (r'\bRALSTON\b',            'Ralston'),
    (r'\bNABISCO\b',            'Nabisco'),
    (r'\bNABSC?\b',             'Nabisco'),
    (r'\bDOM\b',                'Private Label'),
    (r'\bDOMIN',                'Private Label'),
    (r'\bDFF\b',                'Private Label'),
    (r'\bHEALTH +VALL?\b',      'Health Valley'),
    (r'\bNUTRI +GRAIN\b',       "Kellogg's"),
]
_BRAND_RULES_COMPILED: list[tuple[re.Pattern, str]] = [
    (re.compile(p), b) for p, b in BRAND_RULES
]


def extract_brand(descrip: Optional[str]) -> tuple[str, str]:
    """Match cleaned DESCRIP against BRAND_RULES. Returns (brand, source).

    source ∈ {'descrip_rule', 'unknown'}. The downstream cross-check with
    manufacturer_code in 02_eda upgrades unknown → 'manufacturer_block' where
    possible and produces the confidence tag.
    """
    if descrip is None or (isinstance(descrip, float) and np.isnan(descrip)):
        return ('Unknown', 'unknown')
    s = clean_descrip(descrip).upper()
    if not s:
        return ('Unknown', 'unknown')
    for pat, brand in _BRAND_RULES_COMPILED:
        if pat.search(s):
            return (brand, 'descrip_rule')
    return ('Unknown', 'unknown')


if __name__ == '__main__':
    # smoke tests against values observed in rawData
    cases = [
        ('11.25O',  (11.25, 'oz')),
        ('1.25 O',  (1.25,  'oz')),
        ('17.4 Z',  (17.4,  'oz')),
        ('19.25Z',  (19.25, 'oz')),
        ('14.8',    (14.8,  'oz')),
        ('12.75',   (12.75, 'oz')),
        ('2/20 O',  (20.0,  'oz_bundle')),
        ('ASST',    (np.nan, 'assorted')),
        ('ASSTD',   (np.nan, 'assorted')),
        ('1 CT',    (np.nan, 'count')),
        ('144 CT',  (np.nan, 'count')),
        ('end',     (np.nan, 'invalid')),
        (None,      (np.nan, 'missing')),
    ]
    for raw, (exp_v, exp_k) in cases:
        v, k = parse_size(raw)
        ok = ((np.isnan(v) and np.isnan(exp_v)) or v == exp_v) and k == exp_k
        print(f'{"OK " if ok else "FAIL"} parse_size({raw!r:>12}) -> ({v}, {k!r})')
    print()
    for d, exp_brand in [
        ('KELL CORN FLAKES',   "Kellogg's"),
        ('GEN M CHEERIOS',     'General Mills'),
        ('POST GRAPE NUTS',    'Post'),
        ('QUAKER OATS',        'Quaker'),
        ('DOM CORN CHEX',      'Private Label'),
        ('MYSTERY BRAND',      'Unknown'),
    ]:
        b, src = extract_brand(d)
        print(f'{"OK " if b == exp_brand else "FAIL"} extract_brand({d!r}) -> ({b!r}, {src!r})')
