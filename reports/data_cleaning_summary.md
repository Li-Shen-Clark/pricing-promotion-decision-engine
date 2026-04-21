# Data Cleaning Summary — Dominick's Cereals
Generated: 2026-04-20T16:09:34

## Key findings carried forward
- `PRICE=0` and `MOVE=0` almost perfectly overlap: all 1,850,703 zero-movement rows also have zero price; 677 additional rows have `PRICE=0` but positive movement and are treated as invalid price records. The `PRICE>0` filter is therefore retained for the demand sample.
- `SALE` includes undocumented `G` and `L` codes. `G` is frequent enough to keep as `unknown_promo`; `L` appears once and is treated as missing.
- `PROFIT` median is 13.7%, so the validation sanity range should be `[5, 30]`, not `[20, 50]`.
- `COM_CODE` is constant at 311 for all UPC rows, so no additional subcategory filtering is needed.
- `SIZE` parsing requires robust rules: strict OZ parsing succeeds for 72.2%, while values such as `11.25O`, `1.25 O`, `ASST`, `1 CT`, and `end` need special handling or exclusion from `price_per_oz`.
- Cleaned panel granularity is sufficient for SKU-store fixed effects: 486 UPCs, 93 stores, 366 weeks, 36,199 UPC-store pairs, with median coverage of 78 weeks per pair.

## 1. Load
- `wcer.csv`: 6,602,582 rows × 9 cols, memory ~139 MB
- `upccer.csv`: 490 rows × 6 cols
## 2. Schema validation
- All schema assertions passed
## 3. Row-level diagnostics (wcer)
- OK flag: {0: 141285, 1: 6461297} ({0: 2.14, 1: 97.86} %)
- MOVE: zero-move rows = 28.0%, max = 18688, p99 = 103
- QTY: bundle rows (QTY>1) = 0.08%, distinct QTY values = [1, 2, 3, 4]
- PRICE: zero-price rows = 28.04%, max = $26.02, p99 = $4.75
- PRICE/MOVE overlap: all zero-MOVE rows have PRICE=0; 677 rows have PRICE=0 and MOVE>0
- PROFIT: median = 13.7%, < 0 = 0.80%, > 99 = 0.01%, NaN = 0.00%
- SALE value counts (incl. NaN): {nan: 6242568, 'B': 254261, 'S': 91259, 'G': 11075, 'C': 3418, 'L': 1}
  **WARNING**: unexpected SALE codes: {'G', 'L'}
## 4. Uniqueness
- duplicate (UPC, STORE, WEEK) rows: 0
## 5. UPC file diagnostics
- COM_CODE value_counts: {311: 490}
- SIZE: OZ-parseable rate = 72.2%, distinct non-OZ SIZE values = ['1 CT', '1.0', '1.25 O', '1.35 O', '1.45 O', '10.9 O', '11.1 O', '11.25O', '11.4 O', '11.5 O', '11.9 O', '12.1 O', '12.2 O', '12.3 O', '12.5 O', '12.7 O', '12.75', '12.8 O', '13.1 O', '13.3 O', '13.7 O', '13.75O', '13.8 O', '14.1 O', '14.2 O', '14.25', '14.5 O', '14.75O', '14.8', '14.8 O', '144 CT', '15.1 O', '15.3 O', '15.5 O', '15.7 O', '15.75O', '15.8 O', '15.9 O', '16.1 O', '16.2 O', '16.4', '16.8 O', '17.2 O', '17.3 O', '17.4 Z', '17.5 O', '17.6 O', '17.8 O', '17.9 O', '18.25O', '18.3 O', '18.5 O', '18.7 O', '18.75O', '18.8 O', '18.9 O', '19.1', '19.2 O', '19.25', '19.25Z', '19.7 O', '2/20 O', '20.2 O', '20.3 O', '20.4 O', '20.5 O', '21.25O', '21.3 O', '21.5 O', '21.7 O', '23.45O', '23.6 O', '25 CT', '25.5 O', '8.25 O', '8.56 O', '8.75 O', 'ASST', 'ASSTD', 'end']
- DESCRIP special char counts: {'#': 0, '<': 0, '~': 36, '$': 8, '*': 0}
## 6. Cleaning filters applied
- before: 6,602,582 rows
- after (OK=1 & 0≤PROFIT<99 & PRICE>0): 4,654,156 rows (70.5% retained, 1,948,426 dropped)
- sale_type_clean counts (post-filter): {'missing': 4336690, 'bonus_buy': 234444, 'price_reduction': 72923, 'unknown_promo': 6777, 'coupon': 3322}
## 7. Sanity check (bundle formula)
- sample row: UPC=1600064360, STORE=5, WEEK=146, PRICE=5.00, QTY=2, MOVE=12
- manual formula revenue = 30.00
- derived column revenue = 30.00
- **PASS**: derived revenue matches manual formula
- PROFIT median sanity: 16.7% ∈ [5, 30] → OK
## 8. Join wcer × upccer
- panel rows: 4,654,156
- rows with no UPC metadata match: 0 (0.00%)
## 9. WEEK → date
- date range: 1989-09-14 to 1997-05-01
- years covered: [1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997]
## 10. Granularity preview
- panel rows (UPC × store × week, after cleaning): 4,654,156
- distinct UPC × store pairs: 36,199
- distinct UPCs: 486
- distinct stores: 93
- distinct weeks: 366
- weeks per UPC-store pair: median = 78, p10 = 7, p90 = 343
## 11. Saved processed panel
- path: `data/processed/sku_store_week_panel.parquet`
- size on disk: 31.6 MB
