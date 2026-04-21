"""Upload-and-Score validator + scorer (Page 6 backend).

The validator is the public API contract for the only mutable input the app
accepts. These tests pin:

- column-name synonym mapping
- blocking errors vs warnings
- MAX_ROWS gate
- score(...) output shape and the lift-vs-baseline accounting under the BASELINE
  scenario (apples-to-apples: action lift, not action+shock lift)
"""
from __future__ import annotations
import io
import numpy as np
import pandas as pd
import pytest

from src.upload import (
    validate, score, template_csv,
    REQUIRED_COLUMNS, OPTIONAL_COLUMNS, MAX_ROWS,
)
from src.simulation import MAIN_COEFS
from src.scenario import Scenario, BASELINE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _good_row(**overrides) -> dict:
    base = {
        'product_id':       'SKU001',
        'store_id':         'STORE_A',
        'quantity':         10.0,
        'price':            3.00,
        'unit_cost':        1.50,
        'promo':            0,
        'competitor_price': 3.00,
    }
    base.update(overrides)
    return base


def _good_df(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame([_good_row(quantity=10.0 + i) for i in range(n)])


# ===========================================================================
# §1 — Validator: schema + synonyms + range checks
# ===========================================================================
def test_template_csv_round_trips_through_validator():
    """The template we hand the user must itself pass validation — otherwise
    the 'download template, upload it back' demo silently fails."""
    raw = pd.read_csv(io.StringIO(template_csv()))
    rep = validate(raw)
    assert rep.ok, f'template failed validation: errors={rep.errors}'
    assert rep.standardized is not None
    assert len(rep.standardized) == len(raw)


def test_synonyms_are_applied():
    raw = pd.DataFrame([{
        'sku':         'SKU001',     # → product_id
        'store':       'A',          # → store_id
        'qty':         10.0,         # → quantity
        'sale_price':  3.00,         # → price
        'cogs':        1.50,         # → unit_cost
        'on_promo':    0,            # → promo
        'p_comp':      3.10,         # → competitor_price
    }])
    rep = validate(raw)
    assert rep.ok, rep.errors
    assert set(rep.detected_synonyms.keys()) >= {
        'sku', 'store', 'qty', 'sale_price', 'cogs', 'on_promo', 'p_comp'
    }
    assert all(c in rep.standardized.columns for c in REQUIRED_COLUMNS)


def test_missing_required_column_blocks_with_named_error():
    df = _good_df(3).drop(columns=['unit_cost'])
    rep = validate(df)
    assert rep.ok is False
    assert any('unit_cost' in e for e in rep.errors), rep.errors
    assert rep.standardized is None


def test_empty_dataframe_blocks():
    rep = validate(pd.DataFrame(columns=list(REQUIRED_COLUMNS)))
    assert rep.ok is False
    assert any('empty' in e.lower() for e in rep.errors)


def test_max_rows_gate_blocks():
    """Build a DataFrame with one more row than MAX_ROWS allows. We don't
    actually allocate MAX_ROWS·N values — we copy a single row a lot of times."""
    df = pd.DataFrame([_good_row()] * (MAX_ROWS + 1))
    rep = validate(df)
    assert rep.ok is False
    assert any('rows' in e.lower() for e in rep.errors)


def test_negative_price_dropped_with_warning():
    df = pd.concat([_good_df(3), pd.DataFrame([_good_row(price=-1.0)])], ignore_index=True)
    rep = validate(df)
    assert rep.ok is True
    assert rep.n_rows_in == 4
    assert rep.n_rows_out == 3
    assert any('invalid values' in w for w in rep.warnings)


def test_promo_not_in_zero_one_dropped():
    df = pd.concat([_good_df(2), pd.DataFrame([_good_row(promo=2)])], ignore_index=True)
    rep = validate(df)
    assert rep.ok is True
    assert rep.n_rows_out == 2


def test_promo_string_truthy_coerces():
    """The validator should accept common bool-like strings ('yes', 'true', '1')."""
    df = pd.DataFrame([_good_row(promo='yes'), _good_row(promo='no'), _good_row(promo='true')])
    rep = validate(df)
    assert rep.ok is True
    assert rep.n_rows_out == 3
    assert set(rep.standardized['promo'].unique()) <= {0, 1}


def test_negative_margin_row_kept_with_warning():
    """price ≤ unit_cost is allowed (the row scores to non-positive profit)
    but should fire a warning."""
    df = pd.concat([_good_df(2),
                    pd.DataFrame([_good_row(price=1.50, unit_cost=2.00)])],
                   ignore_index=True)
    rep = validate(df)
    assert rep.ok is True
    assert rep.n_rows_out == 3   # not dropped
    assert any('non-positive margin' in w for w in rep.warnings)


# ===========================================================================
# §2 — Scoring contract
# ===========================================================================
SCORE_OUTPUT_COLS = {
    'cand_price', 'cand_promo', 'cand_q', 'cand_revenue',
    'cand_profit', 'baseline_profit', 'profit_lift_abs', 'profit_lift_pct',
}


def test_score_adds_expected_columns():
    df = _good_df(4)
    out = score(df, beta_own=MAIN_COEFS['beta_own'],
                beta_cross=0.0, theta=MAIN_COEFS['theta_promo'],
                price_multiplier=0.05, promo_action='keep',
                scenario=BASELINE)
    assert SCORE_OUTPUT_COLS.issubset(out.columns)
    assert len(out) == len(df)


def test_score_zero_action_under_baseline_yields_zero_lift():
    """Action = 'keep' price + 'keep' promo + BASELINE scenario ⇒ candidate ≡ baseline ⇒ lift = 0."""
    df = _good_df(5)
    out = score(df, beta_own=MAIN_COEFS['beta_own'],
                beta_cross=0.0, theta=MAIN_COEFS['theta_promo'],
                price_multiplier=0.0, promo_action='keep',
                scenario=BASELINE)
    np.testing.assert_allclose(out['profit_lift_abs'].to_numpy(), 0.0, atol=1e-9)


def test_score_promo_action_overrides_uploaded_promo():
    df = pd.DataFrame([_good_row(promo=0), _good_row(promo=1)])
    out_on  = score(df, beta_own=MAIN_COEFS['beta_own'], beta_cross=0.0,
                    theta=MAIN_COEFS['theta_promo'], price_multiplier=0.0,
                    promo_action='on', scenario=BASELINE)
    out_off = score(df, beta_own=MAIN_COEFS['beta_own'], beta_cross=0.0,
                    theta=MAIN_COEFS['theta_promo'], price_multiplier=0.0,
                    promo_action='off', scenario=BASELINE)
    assert (out_on['cand_promo'] == 1).all()
    assert (out_off['cand_promo'] == 0).all()


def test_score_negative_margin_yields_nonpositive_cand_profit():
    df = pd.DataFrame([_good_row(price=1.0, unit_cost=2.0)])
    out = score(df, beta_own=MAIN_COEFS['beta_own'], beta_cross=0.0,
                theta=MAIN_COEFS['theta_promo'],
                price_multiplier=0.0, promo_action='keep', scenario=BASELINE)
    assert out['cand_profit'].iloc[0] <= 0


def test_score_price_increase_yields_lower_quantity_for_negative_beta():
    """Sanity: with β_own < 0, raising price reduces predicted q."""
    df = _good_df(3)
    out_up   = score(df, beta_own=-1.5, beta_cross=0.0, theta=0.0,
                     price_multiplier=+0.10, promo_action='keep', scenario=BASELINE)
    out_flat = score(df, beta_own=-1.5, beta_cross=0.0, theta=0.0,
                     price_multiplier=+0.00, promo_action='keep', scenario=BASELINE)
    assert (out_up['cand_q'] < out_flat['cand_q']).all()


def test_score_baseline_lift_decomposes_correctly_under_cost_shock():
    """User-flagged subtlety: under a cost shock, 'baseline' = do-nothing under the
    SAME shock (uses cost_eff, not raw cost). So the lift number isolates the
    *action* from the *shock*. With price_multiplier=0 and promo='keep', the
    lift should be exactly 0 even when cost_shock != 0."""
    df = _good_df(4)
    sc = Scenario(cost_shock=0.20)
    out = score(df, beta_own=MAIN_COEFS['beta_own'], beta_cross=0.0,
                theta=MAIN_COEFS['theta_promo'],
                price_multiplier=0.0, promo_action='keep', scenario=sc)
    np.testing.assert_allclose(out['profit_lift_abs'].to_numpy(), 0.0, atol=1e-9)
