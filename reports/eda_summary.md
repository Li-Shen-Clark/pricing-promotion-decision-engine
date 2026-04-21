# EDA Summary — brand mapping, size parsing, granularity
Generated: 2026-04-20T16:37:07

## Frozen decisions (entering `03_demand_estimation.ipynb`)

- **Baseline demand panel**: `brand_final × size_oz × store × week` → [`data/processed/brand_size_store_week_panel.parquet`](../data/processed/brand_size_store_week_panel.parquet) (2,690,548 rows).
- **Robustness panel**: `UPC × store × week` → [`data/processed/sku_store_week_panel.parquet`](../data/processed/sku_store_week_panel.parquet) (4,654,156 rows).
- **Main promo variable**: `promo_any` (cell-level on/off — 03 uses this as the headline promo regressor).
- **Auxiliary promo variable**: `promo_share` (reserved for robustness / sensitivity tables only; not in baseline model).
- **Confidence filter**: aggregation includes only `brand_confidence ∈ {high, medium}` and `size_kind ∈ {oz, oz_bundle}`; Unknown brand / ASST / CT rows excluded (retains 96.6% of UPC panel rows).

---



## 1. Load
- rows: 4,654,156, UPCs: 486, stores: 93, weeks: 366
- size_kind: {'oz': 4618200, 'invalid': 29495, 'assorted': 3643, 'count': 2818}
- OZ-parseable share: 99.2%
## 2. Manufacturer blocks
- distinct manufacturer blocks: 23
- blocks covering ≥10 UPCs: 7
- top 10 block sizes: {38000: 142, 16000: 111, 43000: 52, 30000: 51, 17800: 48, 38281: 26, 13130: 19, 791669: 9, 52000: 4, 42400: 4}
## 3. DESCRIP rule coverage (A)
- brand_rule counts: {'Unknown': 215, "Kellogg's": 117, 'Post': 40, 'Quaker': 38, 'Private Label': 24, 'Ralston': 20, 'General Mills': 19, 'Nabisco': 13}
- unknown share: 44.2%
- sample unknown DESCRIPs (≤15):
    · '$TONY THE TIGER T-SH'
    · 'NAB SHREDDED WHEAT'
    · 'NAB SPOON SIZE SHRED'
    · 'NAB RASPBERRY FRUIT'
    · 'NAB SHRED WHT W/OAT'
    · 'TEDDY GRAHAMS BRKFST'
    · 'NAB FROST WHEAT SQUA'
    · 'NAB FROSTED WHEAT'
    · 'TRIPLES/KRAFT MARSHM'
    · '$ GEN MILLS TRIPLES'
    · 'G. MILLS TRIPLES'
    · 'G. MILLS BENEFIT W/R'
    · 'G. MILLS BENEFIT CER'
    · 'G.M. BERRY BERRY KIX'
    · 'BERRY BERRY KIX'
## 4. Brand cross-validation (A × B)
- brand_confidence: {'high': 267, 'medium': 188, 'low': 31}
- brand_source: {'descrip_rule': 271, 'manufacturer_block': 188, 'unknown': 27}
- brand_final: {"Kellogg's": 142, 'General Mills': 111, 'Ralston': 57, 'Quaker': 51, 'Post': 48, 'Unknown': 27, 'Private Label': 27, 'Nabisco': 23}
- conflicts (rule vs block): 4
    · UPC=4300018005  DESCRIP='NABISCO SHREDDED WHE'  rule=Nabisco  block=Post
    · UPC=4300018032  DESCRIP='~NABISCO 100% BRAN'  rule=Nabisco  block=Post
    · UPC=4300018059  DESCRIP='NABISCO WHEAT N BRAN'  rule=Nabisco  block=Post
    · UPC=4300018155  DESCRIP='~NABISCO FROSTED WHE'  rule=Nabisco  block=Post
- saved: data/processed/brand_mapping.csv (486 UPCs)
## 5. SIZE parsing
- UPC-level size_kind: {'oz': 474, 'assorted': 7, 'count': 4, 'invalid': 1}
- row-level size_kind: {'oz': 4618200, 'invalid': 29495, 'assorted': 3643, 'count': 2818}
- UPC-level oz retention: 97.5%
- row-level oz retention: 99.2%
## 6. Price / promo / brand
- brand_final share (% of MOVE): {"Kellogg's": 37.7, 'General Mills': 28.8, 'Post': 10.8, 'Quaker': 8.2, 'Ralston': 5.3, 'Private Label': 5.3, 'Nabisco': 2.4, 'Unknown': 1.4}
- overall promo rate: 6.82%
## 7. Coverage
- UPC×store pairs: n=36,199, median weeks=78, p10=7, p90=343
- brand×size×store triples: n=17,790, median weeks=120, p10=14, p90=684
## 8. Aggregation source
- rows entering aggregation: 4,496,027 (96.6% of panel)
- aggregated rows: 2,690,548
- dominant_sale_type_all: {'missing': 2494418, 'bonus_buy': 138782, 'price_reduction': 50875, 'unknown_promo': 4051, 'coupon': 2422}
- dominant_promo_type: {'missing': 2447144, 'bonus_buy': 176203, 'price_reduction': 58773, 'unknown_promo': 5245, 'coupon': 3183}
- saved: data/processed/brand_size_store_week_panel.parquet (71.9 MB)
- flagged cells: 159,196 (5.9%)
## 9. UPC vs brand-size comparison
| metric | UPC × store × week | brand × size × store × week |
|---|---|---|
| rows | 4,654,156 | 2,690,548 |
| units (pair/triple) | 36,199 | 17,790 |
| median weeks/unit | 78 | 120 |
| median within-unit price CV | 0.073 | 0.081 |
## 10. Recommendation
- c1_sample_size_ok: True
- c2_price_variation_preserved: True
- c3_weeks_per_unit_ok: True
- c4_promo_signal_ok: False
- c5_brand_loss_ok: True
- criteria passed: 4/5
- **Recommended baseline panel**: `brand × size × store × week`
- **Secondary robustness panel**: `UPC × store × week`

**Rationale**: 用加 FE 的聚合面板作 baseline（更稳定），用 UPC 粒度作 robustness check（可识别尾部 SKU 弹性）。
- saved: reports/brand_mapping_review.md