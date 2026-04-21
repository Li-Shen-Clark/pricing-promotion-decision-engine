# Raw Data README — Dominick's Finer Foods Cereals

本文件只说明 `rawData/` 目录中的原始数据、字段定义、manual 摘要和读取规则。整个 Pricing & Promotion Decision Engine 项目的业务问题、方法、运行方式和路线图见根目录 [`README.md`](../README.md)。

本文件夹存放 **Dominick's Finer Foods (DFF)** 零售面板的 Cereals 品类数据，用于 Pricing & Promotion Decision Engine 项目。所有字段定义来自官方 manual（`dominicks_manual.pdf`），本文件只是摘录与加工说明。

---

## 1. 数据来源与引用要求

- **提供方**：James M. Kilts Center for Marketing, University of Chicago Booth School of Business
- **主页**：<https://www.chicagobooth.edu/research/kilts/research-data/dominicks>
- **授权**：仅限学术研究使用。任何 working paper 或 publication **必须致谢** Kilts Center。
- **历史数据**：产品已不再销售，UPC 编号仅作历史记录。
- **时间范围**：1989-09-14 起，共约 400 周（至 1997-05 左右）。
- **门店范围**：Chicago 地区 Dominick's 门店，约 85 家门店参与研究项目（总计约 100 家）。

---

## 2. 文件清单

| 文件 | 大小 | 行数 | 内容 |
|---|---|---|---|
| `wcer.csv` | 437 MB | 6,602,583 | Cereals 周级 UPC-store 交易数据 |
| `wcer.zip` | 40 MB | — | 上文件的压缩版本 |
| `upccer.csv` | 25 KB | 491 | Cereals UPC 到商品属性的映射表 |
| `demo.dta` | 308 KB | — | 门店人口学特征（Stata 格式） |
| `demo_stata.zip` | 165 KB | — | 上文件的压缩版本 |
| `ccount.dta` | 97 MB | — | 门店-周客流量与各品类销售额（Stata 格式） |
| `ccount_stata.zip` | 40 MB | — | 上文件的压缩版本 |
| `dominicks_manual.pdf` | 9.7 MB | 524 pages | 官方数据手册与 codebook |

---

## 3. 字段定义

### 3.1 `wcer.csv` —— 周级交易主数据（完整字典）

| 原字段 | dtype (pandas) | 含义 | 清洗后字段 | 规则 / 转换 | 备注 | 手册页 |
|---|---|---|---|---|---|---|
| `STORE` | `int16` | 门店编号 | `store_id` | 保留原值 | 部分门店中途关闭 | p.11 |
| `UPC` | `int64` → `category` | 商品 UPC | `upc` | cast 为 category；join `upccer.csv` | 末 5 位标识产品，余位标识厂商 | p.9, p.11 |
| `WEEK` | `int16` | DFF 内部周编号 | `week`, `week_start_date` | 通过 §5 decode table 映射到日期 | week 1 = 1989-09-14 | p.21 |
| `MOVE` | `int32` | 本周**单品**售出数（不是 bundle 数） | `quantity` | log 回归前 `MOVE > 0` 过滤 | 零销量周几乎全部对应 `PRICE=0`，见 §8 | p.10 |
| `QTY` | `int8` | Bundle 大小 | `bundle_size` | 用于 `unit_price = PRICE/QTY` | 绝大多数为 1 | p.10 |
| `PRICE` | `float32` | **Bundle** 零售价（美元，非单价） | `unit_price = PRICE/QTY` | 除以 `QTY` 得单位价；需求样本要求 `PRICE > 0` | `PRICE=0` 主要是无流转/无有效价格标记，另有极少数正销量零价格异常 | p.10 |
| `SALE` | `category` (nullable) | 促销代码 `''/B/C/S` | `promo` (bool), `promo_type` (cat) | `promo = SALE.notna() & SALE != ''` | B/C/S 全称 manual 未写，社区约定 Bonus/Coupon/Simple，需 EDA 验证 | p.11 |
| `PROFIT` | `float32` | Gross margin (%) | `unit_cost = unit_price × (1 - PROFIT/100)` | `PROFIT ∈ [0, 99]` 外视为缺失 | **AAC 不等于 marginal cost**（见 §3.4） | p.10 |
| `OK` | `int8` | 数据质量标记 | filter | **仅保留 `OK = 1`** | 0 = "trash"（manual 原文） | p.11 |
| `PRICE_HEX` | `str` | PRICE 的十六进制全精度 | MVP 跳过（`usecols` 排除） | 需精确复现 SAS 结果时使用 | 读入会显著增加内存 | p.3 |
| `PROFIT_HEX` | `str` | PROFIT 的十六进制全精度 | 同上 | 同上 | | p.3 |

**排序**：Manual 声明按 `UPC, STORE, WEEK` 升序，但 Step 2 需显式验证。

**零销量 / 零价格诊断**：Step 2 显示 raw `MOVE=0` 行共 1,850,703，全部同时满足 `PRICE=0`；raw `PRICE=0` 行共 1,851,380，其中 677 行 `MOVE>0`。因此 `PRICE=0` 基本是无流转或无有效成交价标记，少量 `PRICE=0, MOVE>0` 更像异常价格记录。主需求样本使用 `PRICE>0` 与 `MOVE>0` 过滤。

### 3.2 `upccer.csv` —— UPC 属性映射（完整字典）

| 原字段 | dtype (pandas) | 含义 | 清洗后字段 | 规则 / 转换 | 备注 | 手册页 |
|---|---|---|---|---|---|---|
| `COM_CODE` | `int16` | DFF 子品类代码 | `com_code` | Step 2 确认为单值 `311` | 当前 Cereals UPC 不存在子品类混杂，不需额外按 `COM_CODE` 过滤 | p.9 |
| `UPC` | `int64` → `category` | UPC 编号 | `upc` | join key to `wcer` | 末 5 位标识产品 | p.9 |
| `DESCRIP` | `str` (≤20) | 商品名称 | `descrip_clean`, `brand` | 1) 去除 `# < ~ $ *`；2) 前缀/关键词匹配提取品牌 | `#` = Combo store 专供；`~` = 停产；`<` = 试用装 | p.9 |
| `SIZE` | `str` | 包装规格 | `size_oz` | 用鲁棒正则提取 OZ 数值 | 存在截断 OZ 字符串（如 `11.25O`, `1.25 O`）和脏值（如 `ASST`, `1 CT`, `end`），需单独处理或剔除 | p.9 |
| `CASE` | `int16` | 每箱件数 | MVP 不用 | — | 消费者不可见 | p.9 |
| `NITEM` | `int32` | DFF item 追踪码 | `nitem_family = NITEM // 10` | 末位 0 = 厂家直送，1 = DFF 仓储 | 末位之外相同 = 同款 | p.9 |

### 3.3 `SALE` 促销代码

Manual 只列出 `SALE` 取值为 `B`、`C`、`S`（外加空值代表非促销周）。但 raw data 里**实际观察到 `G`（~11K 次，占 promo 行 3%）和 `L`（1 次）** 两个 manual 未记录的代码。

社区约定 + 本项目处理规则：

| 原始取值 | 频次（raw） | 解码 | `sale_type_clean` | 备注 |
|---|---|---|---|---|
| 空 / NA | 6,242,568 | 无促销 | `missing` | — |
| `B` | 254,261 | Bonus Buy（买赠类促销） | `bonus_buy` | 社区约定 |
| `S` | 91,259 | Simple price reduction（直接降价） | `price_reduction` | 社区约定 |
| `G` | 11,075 | **未记录**，价格行为类似 promo（median unit_price 较 NaN 行低 ~36%，median MOVE 高 ~4×） | `unknown_promo` | 保留但不解读含义 |
| `C` | 3,418 | Coupon（优惠券） | `coupon` | 社区约定 |
| `L` | 1 | **录入错误**（只出现 1 行） | `missing` | 并入缺失 |

> **警告**：B/C/S 全称 manual 未写，`G` 完全未记录。以上是研究社区通行解码 + 本项目基于 price/volume 行为的判断。在 EDA 阶段需**验证各代码出现频率与价格行为的一致性**。

**清洗规则**：
```python
# 二元 promo（MVP 用）
promo = sale_type_clean != 'missing'   # G 算 promo，L 不算

# 分类 promo_type（异质性分析用）
SALE_MAP = {
    'B': 'bonus_buy',
    'C': 'coupon',
    'S': 'price_reduction',
    'G': 'unknown_promo',  # observed but undocumented
    'L': 'missing',        # 1-row data error
}
sale_type_clean = SALE.map(SALE_MAP).fillna('missing')
```

Processed panel 同时保留 `sale_code_raw`（原始字符，含 G/L）和 `sale_type_clean`（分类），避免后续分析把 G 当噪声扔掉。

### 3.4 `PROFIT` 与成本反推

- `PROFIT` 是 gross margin (%)，如 `PROFIT=25.3` 意味着 DFF 每美元销售获得 25.3 美分利润，cost of goods sold 为 74.7 美分。
- **单位价格**：`unit_price = PRICE / QTY`
- **单位成本**：`unit_cost = unit_price × (1 - PROFIT/100)`
- **销售额**：`revenue = PRICE × MOVE / QTY = unit_price × MOVE`（Manual 公式）

> **重要 caveat：AAC 不等于 marginal cost**  
> DFF 的 wholesale cost 是 **Average Acquisition Cost (AAC)**：  
> $AAC_{t+1} = \frac{(\text{Inventory bought in } t) \cdot \text{Price paid}_t + (\text{Inventory, end of } t-1 - \text{sales}_t) \cdot AAC_t}{\text{Total inventory}_{t+1}}$  
>  
> AAC 有两处系统性偏离 replacement cost：
> 1. **调整迟滞**：上游降价要靠高价库存消化后才反映到 AAC；
> 2. **前置囤货**：厂家通知临时促销时，DFF 会低库存倒出 → 再大量进货，导致 AAC 在真实成本回升后仍停留在低位。
>
> 做利润优化时 `unit_cost` 是合理代理，但严格意义上不是"最优定价理论"中的边际成本。Memo 中应披露。

### 3.5 `DESCRIP` 特殊字符

| 字符 | 含义 |
|---|---|
| `#` | 仅在 Combo store（带药房的门店）促销 |
| `<` | 试用装（manual 标注"不准确"） |
| `~` | 已停产 |
| `$`、`*` | 无实际意义 |

解析 brand 时应先清理这些字符。

### 3.6 `OK` 标志

- `OK = 1`：有效记录。
- `OK = 0`：垃圾数据（Manual 原文 "trash"），**必须过滤掉**。

### 3.7 推荐的 `pd.read_csv` dtype 映射

`wcer.csv` 有 660 万行；naive `pd.read_csv` 默认把所有数值读成 `int64`/`float64`，再把字符串读成 `object`，内存占用约 **3–4 GB**。显式 dtype map + `usecols` 跳过 HEX 列可以压到 **~180 MB**：

```python
import pandas as pd

WCER_DTYPES = {
    "STORE":  "int16",
    "UPC":    "int64",    # 读入后 cast 为 category
    "WEEK":   "int16",
    "MOVE":   "int32",
    "QTY":    "int8",
    "PRICE":  "float32",
    "SALE":   "category", # pandas 默认把空字符串读成 NaN，category 处理正确
    "PROFIT": "float32",
    "OK":     "int8",
}
WCER_USECOLS = list(WCER_DTYPES.keys())   # 跳过 PRICE_HEX, PROFIT_HEX

wcer = pd.read_csv(
    "rawData/wcer.csv",
    dtype=WCER_DTYPES,
    usecols=WCER_USECOLS,
    na_values=[""],      # SALE 空串 → NaN
)
wcer["UPC"] = wcer["UPC"].astype("category")

UPCCER_DTYPES = {
    "COM_CODE": "int16",
    "UPC":      "int64",
    "DESCRIP":  "string",
    "SIZE":     "string",
    "CASE":     "int16",
    "NITEM":    "int32",
}
# upccer.csv 含非 UTF-8 字节（如 0xd5 = 'Õ'），必须显式指定 encoding
upccer = pd.read_csv("rawData/upccer.csv", dtype=UPCCER_DTYPES, encoding="latin-1")
```

### 3.8 Validation assertions（未来 `src/validation.py` 的种子）

以下断言在 notebook 诊断阶段**应全部显式执行**，稳定后迁移到 `src/validation.py`：

**`wcer` 层：**
1. 列集合 = `{STORE, UPC, WEEK, MOVE, QTY, PRICE, SALE, PROFIT, OK, PRICE_HEX, PROFIT_HEX}`
2. `OK ∈ {0, 1}`；记录 `OK=0` 占比
3. `WEEK ∈ [1, 400]`
4. `QTY ≥ 1`；`QTY > 1` 的占比（bundle 频率）
5. `MOVE ≥ 0`；`MOVE = 0` 占比
6. `PRICE ≥ 0`；记录 `PRICE = 0` 与 `MOVE = 0` 的重合程度。当前 raw data 中所有 `MOVE=0` 行都同时为 `PRICE=0`，但有 677 行 `PRICE=0, MOVE>0`，应作为无效价格记录过滤。
7. `PROFIT` 中位数应在 `[5, 30]` 之间（DFF 零售 gross margin 经验值；注意这是 sanity range，不是硬过滤——超出只触发 inspection；**硬过滤规则**：`PROFIT < 0` 或 `PROFIT ≥ 99` 视为异常，不进入 `unit_cost` / profit 计算）。**不要** 把 Nevo (2001) 里 cereal industry 的 price-cost margin 和这里的 DFF 零售 AAC-based gross margin 混为一谈。
8. `SALE` 取值集合 ⊆ `{NaN, '', 'B', 'C', 'S', 'G', 'L'}`（实际观察到 G 和 L，manual 未记录；L 仅 1 行，视为录入错误）。
9. **唯一性**：`(UPC, STORE, WEEK)` 组合必须唯一
10. **Bundle 公式 sanity**：抽一行 `QTY > 1` 的记录，手算 `revenue = PRICE × MOVE / QTY` 与 `unit_price × MOVE` 是否一致

**`upccer` 层：**
11. `UPC` 唯一
12. `COM_CODE.value_counts()`：当前应为 `{311: 490}`；若未来版本返回多个值，决定是否收窄到 Cereals 主 com_code
13. `SIZE` 正则匹配成功率（非 OZ 和截断单位值需列出）
14. `DESCRIP` 非空比例；特殊字符 (`#/</~/$/*`) 频率

**SIZE 解析规则**：不要只匹配严格的 `OZ` 后缀。实际数据中存在 `11.25O`、`1.25 O`、`19.25Z` 这类截断单位，也存在 `ASST`、`ASSTD`、`1 CT`、`end` 和 `2/20 O` 等需要人工规则或剔除的值。进入 `price_per_oz` 和竞争价格指数前，必须记录 `size_oz` 解析成功率，并把失败样本从 per-oz 特征中排除或手动修复。

**Join 层：**
15. `wcer.UPC` ⊆ `upccer.UPC`（左连接后无未匹配 UPC）
16. 左连接前后行数守恒

---

## 4. 关键公式（Manual 原文）

| 指标 | 公式 |
|---|---|
| 单位价格 | `unit_price = PRICE / QTY` |
| 销售额 | `revenue = PRICE × MOVE / QTY` |
| 单位成本 | `unit_cost = unit_price × (1 - PROFIT/100)` |
| 单位利润 | `unit_margin = unit_price - unit_cost = unit_price × PROFIT/100` |
| 周利润 | `profit = unit_margin × MOVE` |

---

## 5. `WEEK` 编码

Week 是整数，1 开始，对应如下日历周：

| WEEK | 起始日 | 结束日 | 特殊事件 |
|---|---|---|---|
| 1 | 1989-09-14 | 1989-09-20 | — |
| 7 | 1989-10-26 | 1989-11-01 | Halloween |
| 11 | 1989-11-23 | 1989-11-29 | Thanksgiving |
| 15 | 1989-12-21 | 1989-12-27 | Christmas |
| 16 | 1989-12-28 | 1990-01-03 | New-Year |
| 400 | 1997-05-08 | 1997-05-14 | — |

> 完整对照表见 manual 第 21--28 页（Part 8: Week's Decode Table）。  
> Holiday 列被标注的周：Halloween、Thanksgiving、Christmas、New-Year、Presidents Day、Easter、Memorial Day、4th of July、Labor Day。

建议在处理阶段构造 `week_start_date`、`year`、`month`、`is_holiday` 字段。

---

## 6. 精度说明（CSV vs SAS）

- CSV 中 `PRICE`、`PROFIT` 为**截断精度**；`PRICE_HEX`、`PROFIT_HEX` 是对应的**全精度十六进制**。
- 如需 100% 复现已有 SAS 研究结果，应使用 HEX 列解码后替代。
- 本项目 MVP 用截断精度即可（弹性估计对第 3 位小数不敏感）。

---

## 7. 关联数据

### 7.1 `demo.dta` —— 门店人口学
基于 1990 U.S. Census，Market Metrics 处理。字段包括：`income`（log median income）、`ethnic`、`educ`、`age9`、`age60`、`hsizeavg`、`density`、`hvalmean`、`poverty` 等约 40 个变量。可作为 store-level 异质性控制。

### 7.2 `ccount.dta` —— 门店-周客流
每行一个 (store, date)，含：`CUSTCOUN`（客流量）、各品类 sales（`GROCERY`、`CEREAL` 等按部门）、`MANCOUP`（厂家券兑换数）等。可作为需求冲击控制或 traffic 调整。

---

## 8. 已知数据底线

| 规则 | 说明 |
|---|---|
| `OK = 1` | 必须过滤；0 = manual 明确标记 "trash" |
| `PROFIT` 异常 | 负利润、超 100% 利润视为缺失 |
| `MOVE = 0` | 零销量周，主需求回归（log Q）时过滤；raw 诊断中所有 `MOVE=0` 都同时为 `PRICE=0` |
| `PRICE = 0` 或极小 | 过滤；raw 诊断中绝大多数与 `MOVE=0` 重合，另有 677 行 `MOVE>0` 但 `PRICE=0` 的异常记录 |
| `QTY` | 绝大多数 = 1；> 1 代表 bundle 促销，是数据特性不是错误 |
| 库存字段 | DFF **不提供**，作为 scenario input |

---

## 9. Cereals 品类特有信息

- 本品类 UPC 映射表有 **490** 行；清洗后交易面板保留 **486** 个有有效交易记录的 UPC。
- Step 2 清洗后样本覆盖 **93** 家门店、**366** 个周次、**36,199** 个 UPC-store pairs；每个 UPC-store pair 的观测周数中位数为 **78**，足以支持 SKU-store pair fixed effects。
- 主要品牌（需从 `DESCRIP` 前缀解析）：Kellogg's、General Mills、Post、Quaker、Ralston、Nabisco、Private Label、其他小品牌。
- 包装规格多数为盒装，`SIZE` 以 OZ 为主，但只有 **72.2%** 可被严格 OZ 正则直接解析；后续 `price_per_oz` 需要鲁棒解析和失败样本处理。
- `COM_CODE` 为单值 **311**，所有 Cereals UPC 同属一个品类代码，不存在需要额外剔除的子品类混杂。

---

## 10. 下一步

1. 解压后的数据文件（`wcer.csv`、`upccer.csv`、`demo.dta`、`ccount.dta`）是主工作数据；zip 保留作备份。
2. 清洗和聚合逻辑在 `notebooks/01_data_cleaning.ipynb` 中逐步构建，稳定后迁移到 `src/data.py` 和 `src/features.py`。
3. 主项目计划见仓库根目录 `pricing_promotion_decision_engine_plan.tex`。

---

*本说明文件最后更新：2026-04-20*
