"""Build the README hero image directly from the project's data artifacts.

Output: ``reports/figures/readme_hero.png`` (1500x500, suitable for a
GitHub README header). Three panels, left → right:

1. **What** — top-10 raise-and-test candidates ranked by expected weekly profit lift.
2. **Robust?** — own-price elasticity under four identification specs (OLS, store-week FE, two IVs).
3. **How to test?** — required store-weeks per arm vs detectable effect size, drawn from the median top-10 candidate.

Everything is rendered from the same CSVs the live app reads, so the
hero stays in sync with whatever the model currently says — no
screenshot to forget to refresh.

Run from the repo root::

    python3 scripts/build_readme_hero.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT     = Path(__file__).resolve().parent.parent
DATA     = ROOT / 'data' / 'processed'
OUT      = ROOT / 'reports' / 'figures' / 'readme_hero.png'

# ---- Brand palette mirrors src/theme.py so the hero looks like the app ----
BRAND      = '#2c5fa8'
BRAND_SOFT = '#3a78b8'
WARN       = '#a36a0a'
TEXT       = '#1f2933'
MUTED      = '#5b6b82'
BORDER     = '#eef0f5'
SURFACE    = '#fbfcfd'

plt.rcParams.update({
    'font.family':       'sans-serif',
    'font.size':          11,
    'axes.titlesize':     12,
    'axes.labelsize':     10,
    'axes.titleweight':   'bold',
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.spines.left':   False,
    'axes.edgecolor':     BORDER,
    'axes.titlecolor':    TEXT,
    'axes.labelcolor':    MUTED,
    'xtick.color':        MUTED,
    'ytick.color':        MUTED,
    'xtick.major.size':   0,
    'ytick.major.size':   0,
    'figure.facecolor':   '#ffffff',
    'axes.facecolor':     '#ffffff',
})


def _panel_top10(ax: plt.Axes) -> None:
    df = pd.read_csv(DATA / 'top_recommendations.csv')
    df = df.sort_values('profit_lift_abs', ascending=True).tail(10)
    # All top-10 happen to be Kellogg's in this run — call that out in the subtitle
    # rather than repeating the brand on every row.
    only_brand = df['brand_final'].nunique() == 1
    if only_brand:
        labels = [f"{r['size_oz_rounded']:.0f}oz · Store {int(r['STORE'])}" for _, r in df.iterrows()]
        title  = f"1 · What to test — top-10 ({df['brand_final'].iloc[0]})"
    else:
        labels = [f"{r['brand_final'][:8]} {r['size_oz_rounded']:.0f}oz · St{int(r['STORE'])}"
                  for _, r in df.iterrows()]
        title  = '1 · What to test — top-10 by expected weekly lift'
    ax.barh(labels, df['profit_lift_abs'], color=BRAND, edgecolor='none', height=0.7)
    ax.set_title(title, loc='left', pad=10)
    ax.set_xlabel('Expected lift ($/week, model)')
    ax.tick_params(axis='y', labelsize=9)
    ax.grid(axis='x', color=BORDER, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    top = df.iloc[-1]
    ax.text(top['profit_lift_abs'], len(df) - 1,
            f"  ${top['profit_lift_abs']:.0f}/wk",
            va='center', fontsize=9, color=TEXT, fontweight='bold')


def _panel_iv(ax: plt.Axes) -> None:
    df = pd.read_csv(DATA / 'iv_sensitivity_coefficients.csv')
    pretty = {
        'M0':  'OLS',
        'M0b': 'OLS\n+ store-week FE',
        'M1':  'IV\n(Hausman)',
        'M2':  'IV\n(over-ID)',
    }
    df['label'] = df['spec'].map(pretty)
    colors = [BRAND, WARN, BRAND_SOFT, BRAND_SOFT]
    bars = ax.bar(df['label'], df['beta_own'], color=colors, width=0.6)
    ax.errorbar(df['label'], df['beta_own'], yerr=df['se'] * 1.96,
                fmt='none', ecolor=MUTED, elinewidth=1, capsize=3)
    ax.axhline(df['beta_own'].iloc[0], color=BORDER, linestyle='--', linewidth=1, zorder=0)
    ax.set_title('2 · Robust? — β_own under 4 specs', loc='left', pad=10)
    ax.set_ylabel('Own-price elasticity (β_own)')
    ax.set_ylim(-2.0, -1.55)
    ax.tick_params(axis='x', labelsize=8.5)
    ax.grid(axis='y', color=BORDER, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for bar, val in zip(bars, df['beta_own']):
        ax.text(bar.get_x() + bar.get_width() / 2, val - 0.025,
                f'{val:.2f}', ha='center', va='top', fontsize=9, color=TEXT, fontweight='bold')


def _panel_sample_size(ax: plt.Axes) -> None:
    cand = pd.read_csv(DATA / 'experiment_candidates.csv')
    sigma = float(cand['profit_std_wk'].median())
    baseline = float(cand['baseline_profit'].median())
    deltas = np.linspace(baseline * 0.25, baseline * 1.0, 60)
    z_alpha = norm.ppf(1 - 0.05 / 2)
    z_beta  = norm.ppf(0.80)
    n = ((z_alpha + z_beta) ** 2) * 2.0 * (sigma ** 2) / (deltas ** 2)
    ax.plot(deltas, n, color=BRAND, linewidth=2.2)
    ax.fill_between(deltas, n, alpha=0.08, color=BRAND)
    delta_50 = baseline * 0.5
    n_50 = ((z_alpha + z_beta) ** 2) * 2.0 * (sigma ** 2) / (delta_50 ** 2)
    ax.scatter([delta_50], [n_50], color=WARN, s=60, zorder=5)
    ax.annotate(f'  50% MDE ≈ {n_50:.0f} store-weeks',
                xy=(delta_50, n_50), xytext=(8, 10),
                textcoords='offset points', fontsize=9, color=TEXT)
    ax.set_title('3 · How to test? — sample size needed', loc='left', pad=10)
    ax.set_xlabel('Smallest weekly lift to detect ($)')
    ax.set_ylabel('Required store-weeks per arm')
    ax.set_yscale('log')
    ax.grid(True, color=BORDER, linewidth=0.8, which='both', zorder=0)
    ax.set_axisbelow(True)


def main() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2),
                             gridspec_kw={'width_ratios': [1.15, 1, 1]})
    _panel_top10(axes[0])
    _panel_iv(axes[1])
    _panel_sample_size(axes[2])

    fig.suptitle(
        'Pricing & Promotion Decision Engine',
        fontsize=15, fontweight='bold', color=TEXT, x=0.5, y=1.00, ha='center',
    )
    fig.text(0.5, 0.945,
             'What the model says · how robust it is · what an A/B test for it would look like',
             fontsize=10.5, color=MUTED, ha='center', style='italic')
    fig.text(0.5, 0.005,
             'Generated from data/processed/*.csv  ·  reproduce with `python scripts/build_readme_hero.py`',
             fontsize=8, color=MUTED, ha='center', style='italic')

    fig.subplots_adjust(left=0.08, right=0.97, top=0.83, bottom=0.13, wspace=0.34)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=180, facecolor='white')
    print(f'wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB)')


if __name__ == '__main__':
    main()
