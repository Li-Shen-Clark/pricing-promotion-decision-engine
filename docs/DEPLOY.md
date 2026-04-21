# Deploying the Pricing & Promotion Decision Engine

The MVP is a multi-page Streamlit app with a small read-only runtime dataset baked into the repo. It targets **Streamlit Community Cloud** as the zero-cost demo host, but runs the same way locally.

---

## 1. Local development

```bash
# from repo root
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. The sidebar lists six pages: Demand Model, Counterfactual Simulator, Profit Optimizer, Experiment Design, Limitations, Upload & Score.

---

## 2. Preflight before deploy

Run these in order. Each catches a different class of failure that the deploy host will silently turn into a vague error.

### 2.1 Python syntax + import preflight

```bash
python -m py_compile app.py pages/*.py src/*.py
```

Expected: silent exit 0. Any failure here means the deploy slug will not boot.

### 2.2 Runtime data preflight

The app reads a small set of runtime files. Confirm the core files exist:

```bash
ls -la data/processed/cell_baselines.parquet \
       data/processed/top_recommendations_diverse.csv \
       data/processed/all_recommendations.csv \
       data/processed/experiment_candidates.csv \
       data/processed/model_coefficients.csv \
       reports/{counterfactual_summary,demand_model_summary,ab_test_plan,cannibalization_robustness_summary}.md
```

These runtime data files and markdown reports total only a few MB in the GitHub demo repo.

### 2.3 Test preflight

```bash
pytest tests/ -q
```

See [`tests/README.md`](../tests/README.md) for what each suite asserts. CI should run this on every push.

### 2.4 End-to-end smoke (manual, takes ~60s)

```bash
streamlit run app.py
```

Click through every page; on Page 6 upload `data/processed/upload_template_smoke.csv` (or any small CSV with `product_id, store_id, quantity, price, unit_cost, promo`) and confirm the per-row table renders without warnings.

---

## 3. Deploy slug — what is included / excluded

This GitHub release is intentionally lightweight. It includes the app, source code, reports, tests, notebooks, figures, and the small processed artifacts needed at runtime. It excludes raw DFF files and large reconstruction/modeling parquet panels.

### Files needed AT RUNTIME (must ship)

| Path | Size | Used by |
|---|---:|---|
| `data/processed/cell_baselines.parquet` | 900 KB | `load_cells()` (Pages 3, app) |
| `data/processed/top_recommendations_diverse.csv` | ~1 KB | `load_top_recommendations()` (app) |
| `data/processed/all_recommendations.csv` | 1.1 MB | `load_all_recommendations()` (Page 1) |
| `data/processed/experiment_candidates.csv` | ~2 KB | `load_experiment_candidates()` (Page 4, app) |
| `data/processed/model_coefficients.csv` | <1 KB | `load_coefficients()` (Page 1) |
| `data/processed/sensitivity_grid.csv` | ~18 KB | sensitivity diagnostics |
| `data/processed/*_coefficients.csv`, `iv_first_stage_diagnostics.csv` | small | robustness summaries |
| `reports/*.md` | <1 MB | embedded in Limitations + Experiment Design tabs |
| `reports/figures/*.png` | <1 MB | report / case-study figures |

**Runtime footprint: small enough for regular GitHub and Streamlit Community Cloud. No Git LFS is required for this release.**

### Files NOT needed at runtime (notebook-only)

| Path | Size | Produced by | Consumed by |
|---|---:|---|---|
| `data/processed/brand_size_store_week_panel.parquet` | 69 MB | nb 01 | nb 02–04 |
| `data/processed/demand_modeling_dataset.parquet` | 32 MB | nb 03 | nb 03, nb 07 |
| `data/processed/sku_store_week_panel.parquet` | 30 MB | nb 01 | nb 02 |
| `data/processed/cannibalization_diagnostics.parquet` | 28 MB | nb 07 | (diagnostic only) |
| `rawData/wcer.csv`, `rawData/upccer.csv`, `rawData/dominicks_manual.pdf` | ~3 GB | upstream | nb 01 |

These are reproducible from the notebooks once the user downloads DFF data separately. **They should not live in the GitHub demo repo or deploy slug.**

**Do NOT do:** push the raw `rawData/` directory to GitHub. It is large, may violate data-redistribution expectations, and is unnecessary for the frozen Streamlit app.

---

## 4. Streamlit Community Cloud deploy

1. **Push** the repo to GitHub (public or private — Streamlit Cloud supports both).
2. Visit https://share.streamlit.io and sign in with GitHub.
3. **New app** → pick the repo, branch (`main`), main file (`app.py`).
4. **Advanced settings** → Python version `3.11` (matches local; tested on 3.9 and 3.11).
5. Click **Deploy**. First boot pulls the repo, runs `pip install -r requirements.txt`, and starts the app — typically 60–90 s.

**Secrets:** none. The model is frozen, the lightweight runtime artifacts are in-repo, and there are no API keys.

**Memory:** Streamlit Cloud's free tier provides ~1 GB. The app's resident set is ~250 MB after warm-up (pandas + pyarrow + linearmodels). Comfortable margin.

---

## 5. Common deploy failures + fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` on Streamlit Cloud | Working directory not on `sys.path` | Already handled — every page does `sys.path.insert(0, str(PROJECT_ROOT))` at import time. If this re-surfaces, check `app.py` line 9. |
| `FileNotFoundError: data/processed/*.parquet` | Slug missing the runtime files | Re-check §3. The runtime files must be committed and must not be ignored by `.gitignore`. |
| `MemoryError` on Page 3 first load | Cache key collision after a code change | `st.cache_data.clear()` from the app menu, or bump the function's source. |
| Page 6 upload silently 413s | Uploaded CSV exceeds `maxUploadSize` in `.streamlit/config.toml` | Raise the cap in config OR ask the user to split. The validator's `MAX_ROWS` is the user-facing limit; the slug-side cap is a hard floor. |
| LaTeX-rendered methodology PDF missing | `.pdf` blocked by `.gitignore` | Confirm `pricing_promotion_decision_engine_plan.pdf` is committed; the page links to it but does not embed. |
| `ImportError: cannot import name 'AbsorbingLS' from 'linearmodels'` | linearmodels major version change | Pin `linearmodels==6.1` in requirements.txt (currently `>=6.0`). |

---

## 6. Production-readiness gaps (not blocking the demo)

- **No auth.** App is public-by-default on Streamlit Cloud.
- **No request logging.** Page 6 uploads are processed in-memory and discarded; nothing is persisted.
- **No model retraining endpoint.** The frozen coefficients ship with the slug; updating them requires a re-deploy.
- **No background jobs.** Notebook 07 runs locally only — its outputs are checked into the slug as static artifacts.

These are intentional MVP scope cuts, not bugs. They are listed in [`pages/5_Limitations.py`](../pages/5_Limitations.py) for the user-facing version.
