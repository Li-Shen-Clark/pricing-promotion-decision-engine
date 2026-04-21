# Pricing & Promotion Decision Engine

**Live app:** https://pricing-promotion-decision-engine.streamlit.app/  
**GitHub repo:** https://github.com/Li-Shen-Clark/pricing-promotion-decision-engine

An applied decision engine for retail pricing and promotion strategy. The project uses Dominick's Finer Foods cereal scanner data to estimate demand response, simulate counterfactual prices and promotions, and generate constrained raise-and-test pricing candidates under cost, inventory, margin, and experimentation constraints.

This is not a new econometric estimator. It is a transparent decision-support product that translates classic scanner-data demand estimation, cereal product differentiation research, pricing optimization, and A/B testing logic into a reproducible project.

The methodology deliberately separates formula provenance: DFF price, quantity, movement, and gross-margin fields are used for accounting transformations; the demand model is a standard reduced-form log-log fixed-effects approximation; Duan smearing is used for log-outcome retransformation; and the competitor-price index plus anchored counterfactual optimizer are project-specific implementation choices for decision support.

## Project Status

Current stage: portfolio-ready Streamlit MVP. The project now has cleaned panels, EDA, demand estimation, counterfactual simulation, profit optimization, A/B validation design, cannibalization robustness, IV sensitivity checks, tests, deployment notes, and an interactive local app.

- Raw data dictionary: [`rawData/README.md`](rawData/README.md)
- Cleaning notebook: [`notebooks/01_data_cleaning.ipynb`](notebooks/01_data_cleaning.ipynb)
- EDA notebook: [`notebooks/02_eda.ipynb`](notebooks/02_eda.ipynb)
- Demand estimation notebook: [`notebooks/03_demand_estimation.ipynb`](notebooks/03_demand_estimation.ipynb)
- Counterfactual notebook: [`notebooks/04_counterfactual.ipynb`](notebooks/04_counterfactual.ipynb)
- A/B design notebook: [`notebooks/05_ab_testing_design.ipynb`](notebooks/05_ab_testing_design.ipynb)
- Cleaning diagnostics: [`reports/data_cleaning_summary.md`](reports/data_cleaning_summary.md)
- Demand summary: [`reports/demand_model_summary.md`](reports/demand_model_summary.md)
- Counterfactual summary: [`reports/counterfactual_summary.md`](reports/counterfactual_summary.md)
- A/B validation plan: [`reports/ab_test_plan.md`](reports/ab_test_plan.md)
- Cannibalization robustness: [`reports/cannibalization_robustness_summary.md`](reports/cannibalization_robustness_summary.md)
- IV sensitivity: [`reports/iv_sensitivity_summary.md`](reports/iv_sensitivity_summary.md)
- End-to-end case study: [`reports/case_study.md`](reports/case_study.md)
- Methodology: [`docs/methodology.md`](docs/methodology.md), [`docs/methodology.tex`](docs/methodology.tex)
- Lightweight app artifacts: [`data/processed/`](data/processed/)
- Streamlit app: [`app.py`](app.py)

Roadmap items left outside the MVP are competitor-response sensitivity and dynamic promotion / stockpiling extensions.

## Business Problem

Retail pricing teams need to answer questions that pure sales forecasting does not answer:

- Is the current price too high or too low?
- Does a promotion increase units, revenue, or profit?
- How would quantity, revenue, and profit change under an alternative price?
- Which price and promotion status are worth testing under business constraints?
- What experiment is needed before rolling out a candidate action?

The final product lets a user select a product or brand, adjust effective price, promotion status, competitor price, unit cost, and inventory, then see predicted demand, revenue, profit, and a raise-and-test candidate action.

The Streamlit MVP supports user-defined demand, cost, competitor-price, inventory, and promo-fixed-cost scenarios layered on top of the frozen demand model; defaults are inert (BASELINE = offline notebook results), and any non-zero shock triggers live re-optimization across all eligible cells with risk-flag banners when the inputs leave a sane range. Multiplicative shocks must satisfy `demand_shock > -1`, `cost_shock > -1`, and `competitor_price_shock > -1`; risk flags use symmetric thresholds for demand, cost, and competitor-price shocks. See `docs/methodology.md` §8.1 for the overlay equations.

## Data

The project uses the Dominick's Finer Foods database from the James M. Kilts Center for Marketing at the University of Chicago Booth School of Business. The MVP focuses on the Ready-to-Eat Cereals category.

Raw files currently used:

- `rawData/wcer.csv`: weekly UPC-store movement data for cereals
- `rawData/upccer.csv`: cereal UPC attributes
- `rawData/dominicks_manual.pdf`: official codebook and field definitions

Core fields include `UPC`, `STORE`, `WEEK`, `MOVE`, `PRICE`, `QTY`, `SALE`, `PROFIT`, and `OK`. See [`rawData/README.md`](rawData/README.md) for the data dictionary, field rules, `SALE` code notes, `PROFIT` interpretation, and validation assertions.

**GitHub demo note.** The raw DFF CSV/PDF files and large generated parquet panels are not redistributed in this repository. The app runs from lightweight processed artifacts committed under `data/processed/`; users who want to rerun the full cleaning and modeling notebooks should download the DFF files separately following [`rawData/README.md`](rawData/README.md).

## Data Cleaning Snapshot

The first cleaning pass produced:

- `wcer.csv`: 6,602,582 rows loaded
- `OK=1`: 97.86% of raw rows
- Zero `MOVE` rows: 28.0%
- Rows retained after `OK=1`, valid margin, and positive price filters: 4,654,156
- Cleaned panel covers 486 UPCs, 93 stores, 366 weeks, and 36,199 UPC-store pairs
- Median UPC-store coverage is 78 weeks, which supports SKU-store fixed effects
- Zero-movement rows are all zero-price rows; a small number of additional zero-price rows have positive movement and are excluded as invalid price records
- UPC metadata join miss rate: 0.00%
- Cleaned panel saved locally as `data/processed/sku_store_week_panel.parquet` in the full development workspace; this large reconstruction panel is documented but not included in the lightweight GitHub demo repo.

Full diagnostics are in [`reports/data_cleaning_summary.md`](reports/data_cleaning_summary.md).

## Aggregation

The source-of-truth panel is `UPC x store x week`. The baseline demand model uses `brand x size_oz x store x week`, with the UPC-level panel retained for robustness.

At the brand-size level, quantity is summed, dollar sales are aggregated from DFF bundle prices, and effective price is `sales / quantity`, not a simple average. The aggregated unit-cost proxy is quantity-weighted. The baseline promotion variable is `promo_any`, with `promo_share` retained as a diagnostic.

## Relation to Prior Work

The project is positioned as an applied decision product rather than a structural IO replication.

- Scanner-data retail pricing: Dominick's is a classic public retail panel for shelf management and pricing research.
- Differentiated demand: BLP and Nevo's cereal work motivate the structural demand context and cereal-market substitution logic, but they are not the source of the MVP fixed-effects equation.
- Promotion behavior: Hendel and Nevo highlight that temporary sales may involve stockpiling, so a static weekly model should be interpreted carefully.
- Pricing optimization: revenue management and price optimization literature motivate combining demand, cost, inventory, and constraints in one decision problem; the MVP grid search is an implementation choice, not a new optimization method.
- Experimentation: observational price and promotion variation is not final causal evidence, so candidate actions need randomized tests or credible rollout designs.

## Method

The baseline demand model is a transparent fixed-effects model:

```text
log(quantity) ~ log(own effective price)
              + log(competitor price)
              + promo
              + SKU-store fixed effects
              + week fixed effects
              + optional controls
```

The app uses the fitted model to:

- estimate own-price elasticity, cross-price elasticity, and conditional sale-code effects;
- apply smearing correction when transforming log demand predictions back to quantity;
- simulate price and promotion counterfactuals;
- optimize profit with price band, margin, inventory, and optional promotion-cost constraints;
- surface uncertainty and identification caveats;
- design an A/B test for rollout validation.

Formula provenance matters for interpretation. Effective price and dollar sales are DFF accounting transformations (`PRICE/QTY` and `PRICE*MOVE/QTY`); `unit_cost` is derived from the DFF gross-margin field and should be read as an average-acquisition-cost proxy, not observed marginal cost. The competitor-price index is a project-specific competitive-environment measure, not a structural substitution matrix. The anchored counterfactual demand function is an algebraic implementation of the fitted log-log model, and revenue/profit use inventory-capped sold quantity before computing dollars.

When the app reports absolute candidate profit, the promo fixed cost enters as `profit = (price - cost) * sold_units - F * promo`. When it reports profit lift against the observed baseline, the same fixed cost is subtracted from both candidate and baseline profits, so the fixed cost only changes incremental lift when the candidate and baseline promotion states differ.

The main fixed-effects specification uses product-store and week fixed effects. The project also estimates a stricter store-week fixed-effects robustness version and Hausman-style other-store IV sensitivity check; the preferred OLS own-price elasticity is robust within 3% under these diagnostics, with the same-chain IV caveat documented in [`reports/iv_sensitivity_summary.md`](reports/iv_sensitivity_summary.md).

For the full demand model, counterfactual simulation logic, profit objective, optimization design, and identification caveats, see [`docs/methodology.md`](docs/methodology.md). A LaTeX version is available at [`docs/methodology.tex`](docs/methodology.tex).

## Project Structure

```text
pricing/
|
|-- README.md
|-- app.py
|-- requirements.txt
|-- pricing_promotion_decision_engine_plan.tex
|-- pricing_promotion_decision_engine_plan.pdf
|
|-- docs/
|   |-- app_wireframe.md
|   |-- methodology.md
|   |-- methodology.tex
|   |-- methodology.pdf
|
|-- rawData/
|   |-- README.md
|
|-- data/
|   |-- processed/
|   |   |-- cell_baselines.parquet
|   |   |-- model_coefficients.csv
|   |   |-- top_recommendations.csv
|   |   |-- top_recommendations_diverse.csv
|   |   |-- all_recommendations.csv
|   |   |-- experiment_candidates.csv
|   |   |-- sensitivity_grid.csv
|   |   |-- cannibalization_model_coefficients.csv
|   |   |-- iv_sensitivity_coefficients.csv
|   |   |-- iv_first_stage_diagnostics.csv
|
|-- notebooks/
|   |-- 01_data_cleaning.ipynb
|   |-- 02_eda.ipynb
|   |-- 03_demand_estimation.ipynb
|   |-- 04_counterfactual.ipynb
|   |-- 05_ab_testing_design.ipynb
|   |-- 07_cannibalization_robustness.ipynb
|   |-- 08_iv_sensitivity.ipynb
|
|-- pages/
|   |-- 1_Demand_Model.py
|   |-- 2_Counterfactual_Simulator.py
|   |-- 3_Profit_Optimizer.py
|   |-- 4_Experiment_Design.py
|   |-- 5_Limitations.py
|   |-- 6_Upload_and_Score.py
|
|-- reports/
|   |-- data_cleaning_summary.md
|   |-- eda_summary.md
|   |-- demand_model_summary.md
|   |-- counterfactual_summary.md
|   |-- ab_test_plan.md
|   |-- cannibalization_robustness_summary.md
|   |-- iv_sensitivity_summary.md
|   |-- case_study.md
|   |-- figures/
|
|-- src/
|   |-- data.py
|   |-- features.py
|   |-- validation.py
|   |-- scenario.py
|   |-- simulation.py
|   |-- optimization.py
|   |-- upload.py
```

## How to Reproduce

To rebuild from raw data, run the cleaning notebook first:

```bash
jupyter lab notebooks/01_data_cleaning.ipynb
```

Then run the downstream notebooks in order:

```bash
jupyter lab notebooks/02_eda.ipynb
jupyter lab notebooks/03_demand_estimation.ipynb
jupyter lab notebooks/04_counterfactual.ipynb
jupyter lab notebooks/05_ab_testing_design.ipynb
jupyter lab notebooks/07_cannibalization_robustness.ipynb
jupyter lab notebooks/08_iv_sensitivity.ipynb
```

The raw DFF files required by `01_data_cleaning.ipynb` are not committed to this GitHub demo repo; download them according to [`rawData/README.md`](rawData/README.md). The Streamlit app itself does not require the raw files.

To launch the local Streamlit MVP:

```bash
streamlit run app.py
```

## Limitations

- The data are historical and should be used for portfolio demonstration, not current business decisions.
- Inventory is not directly observed in DFF and will be treated as a scenario input.
- `PROFIT` supports a useful gross-margin-derived unit-cost proxy, but it is not observed marginal cost or replacement cost.
- Price, promotion, and competitor price are observational and may be endogenous.
- The MVP cross-price term is an aggregate competitor price index, not a full brand-pair substitution matrix.
- `promo_any` is a cleaned sale-code measure, not a randomized treatment; missing sale codes may still hide promotions.
- Store-week demand shocks can still confound observational price and promotion variation; the planned store-week-FE robustness check is meant to stress-test this risk.
- Any candidate action should be validated with randomized or quasi-experimental rollout before production use.

## Next Steps

1. Publish the Streamlit app and add the deployed URL to this README.
2. Record a 60-90 second GIF or video showing Executive Summary → Optimizer → Experiment Design → Limitations.
3. Optional roadmap: add competitor-response sensitivity and dynamic promotion / stockpiling diagnostics.
