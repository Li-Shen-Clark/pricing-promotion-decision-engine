# Deploying the Pricing & Promotion Decision Engine

The MVP is a multi-page Streamlit app with a small read-only dataset baked into the repo. It targets **Streamlit Community Cloud** as the zero-cost demo host, but runs the same way locally.

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

The app reads only **five small files** at runtime. Confirm they exist:

```bash
ls -la data/processed/cell_baselines.parquet \
       data/processed/top_recommendations_diverse.csv \
       data/processed/all_recommendations.csv \
       data/processed/experiment_candidates.csv \
       data/processed/model_coefficients.csv \
       reports/{counterfactual_summary,demand_model_summary,ab_test_plan,cannibalization_robustness_summary}.md
```

These five data files plus the four markdown reports total **< 2 MB**.

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

## 3. Deploy slug — what to include / exclude

This is the most common foot-gun. The repo contains ~160 MB of large parquet files that the **app does not read at runtime** (they are notebook inputs only). Including them in the deploy slug wastes the host's disk quota, slows boot, and risks tripping Streamlit Cloud's per-app file-size limit.

### Files needed AT RUNTIME (must ship)

| Path | Size | Used by |
|---|---:|---|
| `data/processed/cell_baselines.parquet` | 900 KB | `load_cells()` (Pages 3, app) |
| `data/processed/top_recommendations_diverse.csv` | 4 KB | `load_top_recommendations()` (app) |
| `data/processed/all_recommendations.csv` | 1.1 MB | `load_all_recommendations()` (Page 1) |
| `data/processed/experiment_candidates.csv` | 4 KB | `load_experiment_candidates()` (Page 4, app) |
| `data/processed/model_coefficients.csv` | 4 KB | `load_coefficients()` (Page 1) |
| `reports/*.md` (4 files) | ~30 KB | embedded in Limitations + Experiment Design tabs |
| `reports/figures/*.png` | ~150 KB | rendered by Page 1 + Page 5 |

**Runtime footprint: < 2 MB.**

### Files NOT needed at runtime (notebook-only)

| Path | Size | Produced by | Consumed by |
|---|---:|---|---|
| `data/processed/brand_size_store_week_panel.parquet` | 69 MB | nb 01 | nb 02–04 |
| `data/processed/demand_modeling_dataset.parquet` | 32 MB | nb 03 | nb 03, nb 07 |
| `data/processed/sku_store_week_panel.parquet` | 30 MB | nb 01 | nb 02 |
| `data/processed/cannibalization_diagnostics.parquet` | 28 MB | nb 07 | (diagnostic only) |
| `rawData/wcer.csv`, `rawData/upccer.csv`, `rawData/dominicks_manual.pdf` | ~3 GB | upstream | nb 01 |

These are reproducible from the notebooks. **They should not live in the deploy slug.**

### Recommended approach: Git LFS for the big parquet files

Streamlit Community Cloud supports Git LFS-backed files transparently as long as the LFS budget is not exhausted. The pattern:

```bash
git lfs install
git lfs track "rawData/*.csv" "rawData/*.pdf"
git lfs track "data/processed/brand_size_store_week_panel.parquet"
git lfs track "data/processed/demand_modeling_dataset.parquet"
git lfs track "data/processed/sku_store_week_panel.parquet"
git lfs track "data/processed/cannibalization_diagnostics.parquet"
git add .gitattributes
```

The five small runtime files stay in regular git history, so the deploy slug pulls them with the normal clone and the LFS files are fetched lazily (or skipped entirely on the deploy host since the app code never opens them).

**Alternative (simpler, but heavier slug):** keep everything in regular git. Streamlit Cloud will check the repo out fully and the runtime cost is just disk; boot time is unaffected because nothing reads the large files.

**Do NOT do:** push the raw `rawData/` directory (~3 GB) to GitHub at all. It exceeds the 100 MB-per-file hard limit on regular git and the 2 GB-per-file LFS limit on free Git LFS.

---

## 4. Streamlit Community Cloud deploy

1. **Push** the repo to GitHub (public or private — Streamlit Cloud supports both).
2. Visit https://share.streamlit.io and sign in with GitHub.
3. **New app** → pick the repo, branch (`main`), main file (`app.py`).
4. **Advanced settings** → Python version `3.11` (matches local; tested on 3.9 and 3.11).
5. Click **Deploy**. First boot pulls the repo, runs `pip install -r requirements.txt`, and starts the app — typically 60–90 s.

**Secrets:** none. The model is frozen, the data is in-repo, and there are no API keys.

**Memory:** Streamlit Cloud's free tier provides ~1 GB. The app's resident set is ~250 MB after warm-up (pandas + pyarrow + linearmodels). Comfortable margin.

---

## 5. Common deploy failures + fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` on Streamlit Cloud | Working directory not on `sys.path` | Already handled — every page does `sys.path.insert(0, str(PROJECT_ROOT))` at import time. If this re-surfaces, check `app.py` line 9. |
| `FileNotFoundError: data/processed/*.parquet` | Slug missing the runtime files | Re-check §3. The five runtime files must NOT be in `.gitignore` or LFS-tracked-but-skipped. |
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
