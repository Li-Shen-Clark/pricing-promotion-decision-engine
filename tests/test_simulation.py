"""Demand-prediction + sample-size primitives in src/simulation.py.

Cheap, deterministic, no external state."""
from __future__ import annotations
import math
import numpy as np
import pytest

from src.simulation import predict_q, n_per_arm, MAIN_COEFS


# ---------------------------------------------------------------------------
# predict_q
# ---------------------------------------------------------------------------
def test_predict_q_at_anchor_returns_mean_q():
    """Cell anchor identity: at p=mean_p, m=mean_promo, comp_delta=0,
    predict_q returns mean_q exactly."""
    q = predict_q(p=3.0, m=0.0, mean_q=100.0, mean_p=3.0, mean_promo=0.0,
                  beta_own=-1.5, theta=0.5)
    assert float(q) == pytest.approx(100.0)


def test_predict_q_log_linear_in_price():
    """For a 1% price increase, log-q changes by exactly β_own × 0.01 (small-shock limit)."""
    base = float(predict_q(p=3.00, m=0.0, mean_q=100.0, mean_p=3.00,
                           mean_promo=0.0, beta_own=-1.5, theta=0.0))
    bumped = float(predict_q(p=3.03, m=0.0, mean_q=100.0, mean_p=3.00,
                             mean_promo=0.0, beta_own=-1.5, theta=0.0))
    expected_ratio = (3.03 / 3.00) ** -1.5
    assert bumped / base == pytest.approx(expected_ratio)


def test_predict_q_promo_effect():
    """At m=1 vs m=0 with mean_promo=0, ratio should equal exp(theta)."""
    base = float(predict_q(p=3.0, m=0.0, mean_q=100.0, mean_p=3.0,
                           mean_promo=0.0, beta_own=-1.5, theta=0.43))
    promo = float(predict_q(p=3.0, m=1.0, mean_q=100.0, mean_p=3.0,
                            mean_promo=0.0, beta_own=-1.5, theta=0.43))
    assert promo / base == pytest.approx(math.exp(0.43))


# ---------------------------------------------------------------------------
# n_per_arm
# ---------------------------------------------------------------------------
def test_n_per_arm_known_value():
    """Standard textbook two-sample t-test sample size at α=0.05, power=0.80,
    effect size d = δ/σ = 0.5 → ~63 per arm. Formula: 2(z_α + z_β)² σ²/δ²."""
    n = n_per_arm(sigma=10.0, delta=5.0, alpha=0.05, power=0.80)
    # 2 * (1.96 + 0.8416)^2 * 100 / 25 ≈ 62.79
    assert 62 <= n <= 64


def test_n_per_arm_quartic_in_inverse_delta():
    """Doubling δ should quarter n (n ∝ 1/δ²)."""
    n_small = n_per_arm(sigma=10.0, delta=2.0)
    n_big   = n_per_arm(sigma=10.0, delta=4.0)
    assert n_small / n_big == pytest.approx(4.0, rel=1e-6)


def test_n_per_arm_returns_inf_for_nonpositive_delta():
    assert n_per_arm(sigma=10.0, delta=0.0)  == float('inf')
    assert n_per_arm(sigma=10.0, delta=-1.0) == float('inf')


def test_n_per_arm_higher_power_needs_more_samples():
    n80 = n_per_arm(sigma=10.0, delta=5.0, power=0.80)
    n90 = n_per_arm(sigma=10.0, delta=5.0, power=0.90)
    n95 = n_per_arm(sigma=10.0, delta=5.0, power=0.95)
    assert n80 < n90 < n95


# ---------------------------------------------------------------------------
# MAIN_COEFS sanity (pinning the frozen model)
# ---------------------------------------------------------------------------
def test_main_coefs_signs():
    """β_own < -1 (elastic), β_cross > 0 (substitutes), θ_promo > 0."""
    assert MAIN_COEFS['beta_own']    < -1.0
    assert MAIN_COEFS['beta_cross']  > 0.0
    assert MAIN_COEFS['theta_promo'] > 0.0
