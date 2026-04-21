# Brand mapping review

Generated: 2026-04-20T16:38:14

## Known caveat: manufacturer_code `43000` Post/Nabisco conflict

Four UPCs with DESCRIP prefix `NABISCO...` live in manufacturer_code `43000`, whose block majority is **Post**. These get `brand_source='descrip_rule'`, `brand_final='Nabisco'`, and `brand_confidence='low'` (the DESCRIP is explicit but disagrees with the block). Possible explanations:

- Post acquired the Nabisco cereals line in late 1995 (Kraft→Post rebrand window), and DFF's UPC prefix stuck with the legacy manufacturer but DESCRIP was updated as product labels changed.
- Or DFF's UPC manufacturer coding is not strictly by owner-at-time-of-sale.

**How this affects modeling**: when building cross-brand competitor price indices in `03_demand_estimation`, the four `NABISCO`-DESCRIP UPCs may appear as "competitor" to Post in the brand-size panel because they're labeled `Nabisco`. This is probably the right behavior for shelf-substitution analysis — a shopper sees "Nabisco Shredded Wheat", not the UPC manufacturer code. But it should be called out in the memo as a data lineage subtlety.

---

## Rule set used

| Regex | Brand |
|---|---|
| `\bKELL` | Kellogg's |
| `\bK /?G\b` | Kellogg's |
| `\bGEN +M\b` | General Mills |
| `\bGM\b` | General Mills |
| `\bGENERAL` | General Mills |
| `\bPOST\b` | Post |
| `\bQUAKER\b` | Quaker |
| `\bQKR\b` | Quaker |
| `\bRALSTN?\b` | Ralston |
| `\bRALSTON\b` | Ralston |
| `\bNABISCO\b` | Nabisco |
| `\bNABSC?\b` | Nabisco |
| `\bDOM\b` | Private Label |
| `\bDOMIN` | Private Label |
| `\bDFF\b` | Private Label |
| `\bHEALTH +VALL?\b` | Health Valley |
| `\bNUTRI +GRAIN\b` | Kellogg's |

## Confidence distribution

| brand_confidence | count |
|---|---|
| high | 267 |
| medium | 188 |
| low | 31 |

## Source distribution

| brand_source | count |
|---|---|
| descrip_rule | 271 |
| manufacturer_block | 188 |
| unknown | 27 |

## Low-confidence UPCs (first 20)

| UPC | manufacturer_code | DESCRIP | brand_rule | block_majority_brand | brand_final |
|---|---|---|---|---|---|
| 317 | 0 | $TONY THE TIGER T-SH | Unknown | Unknown | Unknown |
| 1862702345 | 18627 | KASHI PUFFED CEREAL | Unknown | Unknown | Unknown |
| 1862702346 | 18627 | KASHI MEDLEY CEREAL | Unknown | Unknown | Unknown |
| 1862702349 | 18627 | HONEY PUFFED KASHI | Unknown | Unknown | Unknown |
| 2430003155 | 24300 | SUNBELT BERRY BASIC | Unknown | Unknown | Unknown |
| 2430003165 | 24300 | SUNBELT GRANOLA CERE | Unknown | Unknown | Unknown |
| 2430003175 | 24300 | SUNBELT MUESLI CEREA | Unknown | Unknown | Unknown |
| 2480000119 | 24800 | KRETSCHMER WHEAT GER | Unknown | Unknown | Unknown |
| 3680011885 | 36800 | W.C. X-RAISIN BRAN C | Unknown | Unknown | Unknown |
| 4165345678 | 41653 | UNCLE SAM CEREAL | Unknown | Unknown | Unknown |
| 4240090520 | 42400 | MALT O MEAL CRISP N | Unknown | Unknown | Unknown |
| 4240090620 | 42400 | MALT O MEAL CORN FLA | Unknown | Unknown | Unknown |
| 4240091020 | 42400 | MALT O MEAL SUG FROS | Unknown | Unknown | Unknown |
| 4240091320 | 42400 | MALT O MEAL TOOTIE F | Unknown | Unknown | Unknown |
| 4300018005 | 43000 | NABISCO SHREDDED WHE | Nabisco | Post | Nabisco |
| 4300018032 | 43000 | ~NABISCO 100% BRAN | Nabisco | Post | Nabisco |
| 4300018059 | 43000 | NABISCO WHEAT N BRAN | Nabisco | Post | Nabisco |
| 4300018155 | 43000 | ~NABISCO FROSTED WHE | Nabisco | Post | Nabisco |
| 5200034844 | 52000 | POPEYE PUFFED WHEAT | Unknown | Unknown | Unknown |
| 5200034847 | 52000 | POPEYE PUFFED RICE | Unknown | Unknown | Unknown |