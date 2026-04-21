"""Cell-anchored demand prediction + sample-size helpers.

Used by both `04_counterfactual.ipynb`/`05_ab_testing_design.ipynb` style
notebooks and by the Streamlit app. The contract intentionally mirrors §3 of
04 so the app and the notebooks produce identical numbers from the same
coefficients.
"""
from __future__ import annotations
from pathlib import Path
from typing import Mapping
import numpy as np
import pandas as pd
from scipy.stats import norm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED    = PROJECT_ROOT / 'data' / 'processed'
REPORTS      = PROJECT_ROOT / 'reports'
FIGURES      = REPORTS / 'figures'
DOCS         = PROJECT_ROOT / 'docs'

MAIN_COEFS: Mapping[str, float] = {
    'beta_own':   -1.7276,
    'beta_cross': +0.6449,
    'theta_promo':+0.4269,
    'smearing_FE':+1.1395,
}

SENSITIVITY_GRID = {
    'beta_own':    [-1.90, -1.73, -1.50],
    'beta_cross':  [0.0, 0.50, 0.65],
    'theta_promo': [0.30, 0.43, 0.51],
}


def predict_q(p, m, *, mean_q, mean_p, mean_promo,
              beta_own=MAIN_COEFS['beta_own'],
              theta=MAIN_COEFS['theta_promo'],
              beta_cross=0.0,
              log_p_comp_delta=0.0,
              smearing=1.0):
    """Cell-anchored demand prediction.

    Q_hat(p, m) = mean_q * exp[ beta_own*(log p - log mean_p)
                              + theta   *(m   - mean_promo)
                              + beta_cross * log_p_comp_delta ] * smearing

    smearing defaults to 1.0 because mean_q is an empirical level and already
    absorbs E[exp(epsilon)]. Multiplying by S would double-count. The
    FE-based S=1.14 is exposed via MAIN_COEFS['smearing_FE'] for callers that
    need it (e.g. holdout reconstruction in 03), not for cell-anchor use.
    """
    p = np.asarray(p, dtype='float64')
    m = np.asarray(m, dtype='float64')
    log_term = (beta_own * (np.log(p) - np.log(mean_p))
                + theta    * (m - mean_promo)
                + beta_cross * log_p_comp_delta)
    return mean_q * np.exp(log_term) * smearing


def n_per_arm(sigma: float, delta: float, alpha: float = 0.05,
              power: float = 0.80) -> float:
    """Two-sample equal-variance t-test sample size (per arm), store-week unit."""
    if delta <= 0 or sigma <= 0:
        return float('inf')
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    return float(2 * (z_a + z_b) ** 2 * sigma ** 2 / delta ** 2)


def load_cells() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / 'cell_baselines.parquet')


def load_top_recommendations() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / 'top_recommendations_diverse.csv')


def load_all_recommendations() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / 'all_recommendations.csv')


def load_experiment_candidates() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / 'experiment_candidates.csv')


def load_coefficients() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / 'model_coefficients.csv')


def read_markdown(path: Path) -> str:
    return path.read_text(encoding='utf-8')
