# Tests

```bash
pytest                    # full suite (~3 s)
pytest -m "not real_data" # cheap unit tests only (~0.5 s; no parquet I/O)
pytest -m snapshot        # only the pinned-value regressions
```

## Suites

| File | What it covers | Style |
|---|---|---|
| `test_scenario.py` | Scenario overlay math: BASELINE identity, `demand_shock` multiplicative on Q, `inventory_cap` binds as min, `cost_shock` shifts effective cost AND the price-grid margin floor, `promo_fixed_cost` accounting on absolute profit AND the lift-side cancellation. | Synthetic, deterministic. |
| `test_optimization.py` | Three layers — §A synthetic-cell math (closed-form constant-elasticity optimum, cost↑→price↑ ONLY here), §B real-data snapshots (eligible cell count, ceiling-binding rate band, total lift band), §C contract for `profit_lift ≥ 0` (asserted on BASELINE; counter-example shown for cost-shock scenarios where the contract is no longer expected to hold). | Mix. Uses `data/processed/cell_baselines.parquet`. |
| `test_upload.py` | Validator schema, synonym map, blocking errors vs warnings, MAX_ROWS gate, scorer column contract, action-vs-shock decomposition under cost shock. | Synthetic. |
| `test_simulation.py` | `predict_q` cell-anchor identity + log-linearity in price + promo effect = exp(θ); `n_per_arm` against textbook two-sample t-test value, scaling laws, edge cases. | Cheap, deterministic. |

## Marker conventions

- `@pytest.mark.real_data` — touches `data/processed/`. Skip with `-m "not real_data"` when iterating.
- `@pytest.mark.snapshot` — pinned to current pipeline output; **update intentionally** when:
  - eligibility filter (`01_data_cleaning`) changes the cell count
  - optimizer constants (`PRICE_HI_FACTOR`, `MARGIN_FLOOR_RATIO`, `GRID_N`) change
  - frozen `MAIN_COEFS` change

  Update the assertion in the same PR as the upstream change.

## Snapshots currently pinned

| Test | Value | Tolerance |
|---|---|---|
| eligible cell count | 5,896 | exact |
| ceiling-binding rate (BASELINE) | 0.985 | bracket [0.970, 0.995] |
| total weekly profit lift (BASELINE) | ≈ \$133,807 | bracket [0.85×, 1.15×] |

## Why some assertions are deliberately loose

- **Ceiling rate** is bracketed, not pinned to 0.985 exactly, because grid resolution (`GRID_N`) and floor placement nudge the rate by fractions of a percent.
- **Cost↑ → opt_price↑** is tested only on synthetic cells. On the real panel, the margin floor and upper guardrail can clamp prices so the relationship is not strictly monotone — testing it on real data would be brittle without value.
- **`profit_lift ≥ 0`** is asserted only under the BASELINE scenario. We include a counter-example (cost shock) showing the contract legitimately breaks under non-baseline scenarios — to prevent a future "let's tighten this" refactor from extending the assertion past where it holds.
