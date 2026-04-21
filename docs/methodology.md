# Methodology: Demand Estimation, Counterfactual Pricing, and Validation

## Abstract

This document lays out the empirical and decision-theoretic methodology for the Pricing & Promotion Decision Engine. The project studies weekly retail scanner data from Dominick's Finer Foods in the ready-to-eat cereal category and estimates a transparent demand model that relates quantity sold to own price, competitor price, and promotion status. The estimated demand response is then embedded in counterfactual revenue and profit calculations, subject to price, margin, inventory, and experimental-validation constraints. The goal is not to introduce a new econometric estimator or to replicate a full structural demand model such as Berry, Levinsohn, and Pakes (1995) or Nevo (2001). Rather, the project builds an applied decision-support system that translates standard scanner-data demand estimation into auditable pricing recommendations.

The current empirical implementation estimates an own-price elasticity of approximately -1.7 to -1.9, a positive cross-price elasticity, and a positive conditional sale-code coefficient. A promotion coefficient of 0.43 is measured in log points; it corresponds to an implied multiplicative demand difference of approximately \(\exp(0.43)-1 \approx 54\%\), conditional on price and fixed effects. These signs are economically sensible, but the recommendations are explicitly framed as "raise-and-test" candidates rather than direct deployment decisions. A Hausman-style leave-one-out other-store IV and a stricter store-week fixed-effect specification shift the own-price estimate by roughly three to four percent and preserve its sign, bounding the plausible range of bias from observational pricing but not replacing the need for experimental validation; a same-chain caveat applies because Dominick's is a single chain in a single metropolitan area.

## 1. Research Setting and Decision Problem

Retail pricing teams face a recurrent decision problem: for a given product, store, and time period, should the firm keep the current effective price and promotion status, raise price, lower price, or run a promotion? A useful pricing model must therefore do more than forecast sales. It must map feasible actions into expected demand, revenue, and profit under business constraints.

The decision variables in this project are the effective unit price, a binary promotion status, an optional promotion fixed cost, and scenario-level operational constraints such as available inventory and minimum margin. The output of the system is not an automatic price change. It is a set of candidate pricing and promotion actions, accompanied by assumptions, model uncertainty, and an A/B validation design.

## 2. Data and Unit of Observation

The empirical setting is the Dominick's Finer Foods database distributed by the Kilts Center for Marketing at the University of Chicago Booth School of Business. The official data description states that Dominick's and Chicago Booth partnered on store-level shelf-management and pricing research, producing store-level scanner data with category-specific UPC and weekly movement files. The cereal movement file contains weekly store-UPC observations with price, units sold, profit margin, and deal-code variables.

The source-of-truth panel is

```text
UPC x store x week.
```

The baseline demand model uses an aggregated panel at

```text
brand x size_oz x store x week.
```

This baseline grain is a transparency-oriented MVP choice. It reduces sparse UPC noise and keeps brand-size differentiation, but it may introduce compositional bias when multiple UPCs within the same brand-size cell have different prices, bundle structures, promotion status, or sales intensity. The UPC-level panel is therefore retained for robustness. In the current implementation, the brand-size panel has approximately 2.69 million observations and the UPC-level processed panel has approximately 4.65 million valid positive-price observations.

When UPC-level observations are aggregated to the brand-size-store-week level, let \(g\) denote a brand-size cell and \(u \in g\) denote UPCs assigned to that cell. Quantities are summed:

\[
Q_{gst}=\sum_{u\in g} MOVE_{ust}.
\]

Dollar sales are computed from DFF bundle prices and bundle quantities before aggregation:

\[
Sales_{gst}=\sum_{u\in g}\frac{PRICE_{ust}\times MOVE_{ust}}{QTY_{ust}}.
\]

The aggregated effective price is the revenue-per-unit price, equivalently a unit-sales-weighted effective price:

\[
P^{eff}_{gst}=\frac{Sales_{gst}}{Q_{gst}}.
\]

The aggregated unit-cost proxy is quantity-weighted:

\[
c_{gst}=
\frac{\sum_{u\in g} c_{ust} MOVE_{ust}}
{\sum_{u\in g} MOVE_{ust}}.
\]

The baseline promotion indicator is

\[
Promo^{any}_{gst}=\mathbf{1}\left\{\sum_{u\in g} Promo_{ust}>0\right\},
\]

with the quantity-weighted promotion share retained as a diagnostic:

\[
Promo^{share}_{gst}
=
\frac{\sum_{u\in g} Promo_{ust}MOVE_{ust}}
{\sum_{u\in g} MOVE_{ust}}.
\]

Let \(i\) index the product unit, where \(i\) is either a brand-size unit in the baseline panel or a UPC in the robustness panel; let \(s\) index stores and \(t\) index weeks. The main outcome is units sold, \(Q_{ist}\). Effective unit price is \(P^{eff}_{ist}\), computed from the DFF bundle price divided by bundle quantity. Promotion status is \(Promo_{ist}\), based on the cleaned sale-code field. Unit cost \(c_{ist}\) is proxied from DFF's gross margin as

```text
unit_cost = unit_price * (1 - PROFIT / 100).
```

This cost proxy is useful for decision simulation but should not be interpreted as a perfect marginal cost measure, because DFF's wholesale-cost accounting is based on average acquisition cost rather than a contemporaneous replacement cost.

The baseline log-demand specification requires positive observed sales. Observations with invalid quality flags and invalid non-positive prices are excluded, and the main model is estimated on positive-sales product-store-week observations. Missing movement weeks and zero-sale cells are therefore not interpreted as unconditional zero demand in the baseline specification. A robustness version can complete the panel at the UPC-store-week level and handle zero-sale weeks using \(\log(Q+1)\) or an explicit availability indicator. This distinction means that the MVP estimates conditional demand for observed available selling cells, not unconditional category demand across every possible UPC-store-week.

## 3. Demand Specification

The baseline econometric model is a log-log demand equation with product-store and week fixed effects:

```text
log(Q_ist) =
    alpha_is
  + gamma_t
  + beta_own   * log(P_eff_ist)
  + beta_cross * log(P_comp_ist)
  + theta      * Promo_ist
  + X_ist' delta
  + epsilon_ist.
```

The product-store fixed effect \(\alpha_{is}\) absorbs persistent differences in baseline demand across product-store pairs, including stable local demographics, store assortment, shelf placement, and product popularity. Week fixed effects \(\gamma_t\) absorb aggregate seasonality and common demand shocks. The optional control vector \(X_{ist}\) is left empty in the MVP specification, but the design allows later inclusion of holiday indicators, brand-specific seasonality, or store-specific trends.

The coefficient \(\beta_{own}\) is interpreted as an own-price elasticity. A value of \(-1.75\), for example, means that a one percent increase in effective price is associated with an approximately 1.75 percent decrease in quantity, conditional on the fixed effects and controls. The coefficient \(\beta_{cross}\) is an aggregate cross-price elasticity: for substitute cereal brands, it is expected to be positive. The coefficient \(\theta\) measures a conditional sale-code association in log points after controlling for price and fixed effects. Its implied percent demand difference is \(\exp(\theta)-1\), not \(\theta\) itself.

This specification is deliberately simpler than a full differentiated-products demand system. Structural random-coefficients demand models estimate richer substitution patterns and supply-side primitives, but they are outside the MVP scope. The present model is intended to produce an interpretable demand curve that can support counterfactual simulation and experimental prioritization.

### 3.1 Formula Provenance and Interpretation

The formulas in this methodology combine three types of objects: data-accounting transformations, standard econometric or pricing formulas, and project-specific implementation choices. Distinguishing these objects is important because the project is not claiming to introduce a new econometric estimator. It is an auditable decision-support implementation that combines scanner-data demand estimation, retransformation correction, and constrained pricing optimization.

First, the effective unit price and unit-cost proxy are data-accounting transformations based on the Dominick's Finer Foods documentation. Because DFF sometimes records bundle prices, the effective unit price is computed as

\[
P^{eff}_{ist}=\frac{PRICE_{ist}}{QTY_{ist}}.
\]

Dollar sales are correspondingly computed as

\[
Sales_{ist}=\frac{PRICE_{ist}\times MOVE_{ist}}{QTY_{ist}}.
\]

The unit-cost proxy is derived from the DFF gross-margin variable:

\[
c_{ist}=P^{eff}_{ist}\left(1-\frac{PROFIT_{ist}}{100}\right).
\]

This is not an observed marginal cost. It is an accounting proxy based on DFF's gross-margin definition. Since the DFF documentation states that the wholesale-cost measure corresponds to average acquisition cost rather than replacement cost, this proxy is used only for scenario-based decision simulation.

Second, the demand equation is a reduced-form constant-elasticity panel demand approximation. It is not a full structural differentiated-products model. Product-store and week fixed effects provide a transparent adjustment for persistent product-store heterogeneity and aggregate weekly shocks, but the coefficients remain observational unless supported by randomized or quasi-experimental variation. The promotion coefficient is measured in log points; the implied percentage effect of promotion is \(\exp(\theta)-1\), not \(\theta\).

Third, the competitor-price index is a project-specific competitive-environment measure. It summarizes same-store, same-week competitor prices using baseline or lagged weights. It should not be interpreted as a structural substitution matrix or a full set of brand-pair cross-price effects.

Fourth, the smearing correction and the corresponding level prediction follow Duan's retransformation correction for log-outcome models. This correction is applied when converting fitted log-demand predictions into level quantities. It is not applied to the anchored counterfactual demand function because that function starts from an observed level baseline.

Finally, the anchored counterfactual demand function is a project-specific implementation derived algebraically from the estimated log-log demand equation:

\[
\widehat Q(p',m',p^{comp\prime})
=
\bar Q_{cell}
\exp\left[
\hat\beta_{own}\Delta \log p
+
\hat\beta_{cross}\Delta \log p^{comp}
+
\hat\theta \Delta m
\right].
\]

In the MVP optimizer, competitor prices are held fixed unless the user explicitly runs a competitor-price scenario, so \(\Delta \log p^{comp}=0\) by default. To avoid confusion with the Duan smearing factor \(\widehat S\), realized sold quantity is denoted \(\widehat Q^{sold}\):

\[
\widehat Q^{sold}(p',m',p^{comp\prime})
=
\min\{
\widehat Q(p',m',p^{comp\prime}),Inventory
\}.
\]

Revenue and profit are then computed as

\[
Revenue(p',m',p^{comp\prime})
=
p'\widehat Q^{sold}(p',m',p^{comp\prime}),
\]

and

\[
Profit(p',m',p^{comp\prime})
=
(p'-c)\widehat Q^{sold}(p',m',p^{comp\prime})
-
Fm'.
\]

These are accounting and decision-objective formulas, not new econometric estimators. The constrained optimizer applies standard pricing-optimization logic to this estimated demand system, while price bounds, margin constraints, inventory constraints, and promotion fixed costs are project-specific operational guardrails.

## 4. Competitor Price Index

For each focal product \(i\), the competitor price index is constructed from other brands in the same store-week:

```text
P_comp_ist = sum_{b != B(i)} w_base_bs * P_oz_bst,
```

where \(B(i)\) is the focal brand, \(P^{oz}_{bst}\) is the price per ounce for competitor brand \(b\) in store \(s\) and week \(t\), and \(w^{base}_{bs}\) is a baseline or lagged sales-share weight. Current-week sales shares are not used as weights because they would mechanically reflect current demand shocks. If baseline weights are not available, the MVP can use equal weights across observed competitor brands.

The cross-price term is an average competitive environment measure, not a full brand-pair substitution matrix. If the estimated \(\beta_{cross}\) is non-positive or unstable, the optimizer should either disable cross-price response or use a sensitivity range rather than directly using the point estimate.

## 5. Promotion Treatment

The MVP treats promotion as a binary state rather than a continuous discount-depth variable. This choice avoids double-counting discounts. Since the model already includes effective transaction price through \(\log(P^{eff}_{ist})\), adding a continuous discount variable without a separately estimated coefficient would conflate the price effect with a promotion effect.

In the cleaned DFF cereal data, known sale codes \(B\), \(S\), and \(C\) are mapped to promotion types, while the undocumented but empirically promotion-like code \(G\) is retained as `unknown_promo` and included in `promo=True`. The one-row code \(L\) is treated as missing. In the brand-size panel, the primary promotion variable is `promo_any`. The auxiliary `promo_share` is retained for diagnostics, but partial-promotion cells are rare after aggregation, so it is not the main MVP treatment variable.

## 6. Estimation Results Used by the MVP

The current demand estimation notebook produces three main specifications. The baseline brand-size model estimates \(\hat{\beta}_{own} \approx -1.75\) and a conditional sale-code coefficient of approximately \(0.43\) log points, with within \(R^2\) around 0.75. The reported within \(R^2\) refers to the fixed-effects panel regression fit, not to out-of-sample predictive accuracy. A coefficient of \(0.43\) implies a multiplicative difference of \(\exp(0.43)-1 \approx 54\%\), conditional on price and fixed effects. Adding the competitor price term gives \(\hat{\beta}_{own} \approx -1.73\), \(\hat{\beta}_{cross} \approx 0.65\), and a sale-code coefficient around \(0.43\). The UPC-level robustness model gives \(\hat{\beta}_{own} \approx -1.90\), \(\hat{\beta}_{cross} \approx 0.50\), and a sale-code coefficient around \(0.51\).

The sign pattern is economically coherent: own-price elasticity is negative, competitor-price elasticity is positive, and the conditional sale-code association is positive. However, these estimates are not interpreted as final causal effects. They are observational estimates used to parameterize counterfactual decision support.

## 7. Retransformation and Prediction

When the model predicts log quantity directly, retransformation to levels requires care. Applying \(\exp(\cdot)\) to a fitted log outcome can produce biased level predictions because of Jensen's inequality. Following Duan (1983), the project computes a smearing factor

```text
S_hat = (1 / N) * sum_n exp(epsilon_hat_n),
```

and uses

```text
Q_hat = S_hat * exp(eta_hat)
```

when converting model-level log predictions into level quantities. The estimated smearing factor is approximately 1.14 in the baseline brand-size model and approximately 1.17 in the UPC robustness model.

For the counterfactual optimizer, however, the implemented demand function is cell anchored. It begins from the cell's observed baseline mean quantity and applies only the relative demand response implied by the elasticity estimates:

```text
Q_hat(p', m', p_comp') =
    mean_q_cell
  * exp(beta_own * Delta log price
        + beta_cross * Delta log competitor price
        + theta * Delta promo).
```

In the MVP optimizer, competitor prices are held fixed unless the user explicitly runs a competitor-price scenario; equivalently, \(\Delta \log P^{comp}=0\) in the default case. Because the anchor is already a level quantity, the optimizer does not multiply by the smearing factor again. Doing so would double-count the level correction and inflate counterfactual quantities. The calibration ratio of the current counterfactual implementation is approximately 1.06, which is acceptable for the MVP.

## 8. Revenue, Profit, and Feasible Actions

For a candidate effective price \(p'\), promotion status \(m'\), and competitor price \(p^{comp}\), the model first computes counterfactual demand and then applies the inventory cap to realized sold units:

```text
Q_sold(p', m', p_comp) =
    min(Q_hat(p', m', p_comp), Inventory).
```

Revenue and profit use the same capped quantity:

```text
Revenue(p', m', p_comp)
  = p' * Q_sold(p', m', p_comp)

Profit(p', m', p_comp)
  = (p' - c) * Q_sold(p', m', p_comp) - F * m',
```

where \(c\) is unit cost, \(Inventory\) is a scenario input, and \(F\) is an optional fixed cost of running a promotion. The use of \(Inventory\) as a scenario input reflects the fact that the DFF movement data do not observe inventory directly.

When the app reports absolute candidate profit, the promotion fixed cost enters as

\[
Profit(p',m')=(p'-c)Q^{sold}(p',m')-Fm'.
\]

When the app reports profit lift relative to the observed baseline \((p_0,m_0)\), the fixed cost is differenced:

\[
\Delta Profit =
\left[(p'-c)Q^{sold}(p',m')-Fm'\right]
-
\left[(p_0-c)Q^{sold}(p_0,m_0)-Fm_0\right].
\]

Thus, the fixed cost affects the incremental recommendation only when the candidate and baseline promotion states differ.

The feasible action set is restricted by price bounds, a minimum margin condition, optional inventory constraints, and a binary promotion status. These constraints are essential because an unconstrained profit problem can recommend implausible prices when the model is extrapolated outside the historically observed range.

### 8.1 Scenario Overlay (App)

The Streamlit app exposes a unified *scenario overlay* on top of the frozen demand model. The overlay is **business shocks applied to model outputs**, not a re-fit of the model. Five inert defaults (`demand_shock = cost_shock = competitor_price_shock = promo_fixed_cost = 0`, `inventory_cap = None`) reproduce the offline counterfactual exactly. The overlay equations are

```text
Q_model            = predict_q(p, m; coefs, log_p_comp_delta)
log_p_comp_delta   = log(1 + competitor_price_shock)
Q_scenario         = Q_model * (1 + demand_shock)
Q_sold             = min(Q_scenario, inventory_cap)        if cap given else Q_scenario
c_eff              = c * (1 + cost_shock)
Revenue            = p * Q_sold
Profit             = (p - c_eff) * Q_sold - F * m,         F = promo_fixed_cost
```

The multiplicative shocks must satisfy

\[
\delta_q>-1,\qquad \delta_c>-1,\qquad \delta_{comp}>-1,
\]

so that demand, cost, and competitor prices remain non-negative and the logarithm in \(\Delta\log p^{comp}\) is well-defined.

The margin floor uses `c_eff` (so cost shocks tighten the lower price guardrail), and the same `Scenario` instance is passed into both the cell-level simulator and the panel-wide optimizer, so candidate rankings update consistently when the user perturbs any input.

This overlay is intentionally simple: it is meant to support what-if stress tests of cost / demand / competitor / capacity, not to replace IV identification, dynamic stockpiling, or explicit competitor best-response — those are itemized as roadmap notebooks in §11. Risk flags fire when any shock leaves a sane range:

\[
|\delta_q|>0.20,\quad |\delta_c|>0.25,\quad
|\delta_{comp}|>0.15,\quad \text{or}\quad
\bar Q < \bar Q^{base}_{cell}.
\]

These flags warn the user that the inputs lie outside the observational support of the model.

## 9. Optimization Problem

The MVP optimizer evaluates candidate prices and promotion states using a grid search. Since \(m \in \{0,1\}\), the problem can be decomposed into two one-dimensional searches:

```text
1. Fix m = 0 and scan feasible candidate prices.
2. Fix m = 1 and scan feasible candidate prices.
3. Select the feasible action with the highest objective value.
```

The supported objectives are revenue maximization, profit maximization, and profit maximization subject to a minimum quantity constraint. The current counterfactual notebook uses cost, baseline demand, price bounds, and elasticity estimates to produce top candidate actions.

The most important optimizer finding is a diagnostic warning rather than evidence of a successful automatic recommendation rule: 98.5 percent of eligible cells recommend a price at the upper guardrail. For an interior single-product optimum with constant marginal cost and \(\varepsilon<-1\), constant-elasticity demand \(Q=A p^{\varepsilon}\) implies the Lerner condition

\[
\frac{p-c}{p}=-\frac{1}{\varepsilon}.
\]

With an elasticity around \(-1.73\), this implies an unconstrained margin of roughly \(58\%\), which explains why the optimizer frequently pushes prices above the historical support and into the upper bound. These cases should be interpreted as candidate "raise-and-test" opportunities, not direct deployment recommendations.

This guardrail binding result highlights several missing forces: competitor reaction, within-brand cannibalization across package sizes, loss-leader roles, nonlinear elasticities near extreme prices, and strategic category management. These are not defects in the MVP, but they are central limitations that must be disclosed before using the recommendations operationally.

## 10. Identification and Causal Interpretation

The estimation strategy controls for product-store and week fixed effects, but price and promotion are still observational choices. Managers may lower price when expected demand is weak, raise price during high-demand periods, or promote products because of inventory pressure, vendor funding, or category-level campaign schedules. Competitor prices may also respond to common local demand shocks. As a result, \(\hat{\beta}_{own}\), \(\hat{\beta}_{cross}\), and \(\hat{\theta}\) should be interpreted as conditional associations suitable for decision support, not as definitive causal effects.

### 10.1 IV Sensitivity Check (Notebook 08)

The MVP tests whether the baseline OLS own-price elasticity is robust to Hausman-style other-store price instruments and stricter store-week fixed effects. Because Dominick's Finer Foods is a single chain in a single metropolitan area, the IV estimates are interpreted as **sensitivity bounds rather than definitive causal estimates**.

Four specifications are estimated on a common sample (\(N \approx 2.59\) million rows where the Hausman instrument is defined):

| Spec | FE | Estimator | \(\hat\beta_{own}\) | SE |
|---|---|---|---:|---:|
| M0  | brand\(\times\)size\(\times\)store + week | OLS | \(-1.728\) | \(0.020\) |
| M0b | brand\(\times\)size\(\times\)store + store\(\times\)week | OLS | \(-1.805\) | \(0.020\) |
| M1  | brand\(\times\)size\(\times\)store + week | IV (\(Z_H\)) | \(-1.781\) | \(0.021\) |
| M2  | brand\(\times\)size\(\times\)store + week | IV (\(Z_H, Z_C\)) over-ID | \(-1.780\) | \(0.021\) |

The Hausman instrument is the leave-one-out other-store log price, \(Z^H_{bkst} = |\mathcal{S}_{bkt} \setminus \{s\}|^{-1} \sum_{s' \neq s} \log P_{bks't}\). The cost instrument is the analogous leave-one-out other-store log unit cost. We explicitly do **not** use the own-cell \(\log c_{ist}\) as an instrument because DFF derives \(c_{ist} = P_{ist}(1 - PROFIT_{ist}/100)\), so the own-cell cost is mechanically linked to the own-cell price and would violate the IV exclusion restriction. The leave-one-out variant breaks the within-cell mechanical link.

A four-condition decision rule is used:

1. \(|\hat\beta_{IV} - \hat\beta_{OLS}| / |\hat\beta_{OLS}| < 15\%\).
2. First-stage \(F > 10\) (Stock-Yogo weak-instrument rule of thumb).
3. \(\hat\beta_{IV}\) and \(\hat\beta_{OLS}\) share sign.
4. IV 95\% CI width divided by OLS 95\% CI width \(< 3\).

The observed values are \(|\Delta\hat\beta|/|\hat\beta_{OLS}| = 3.0\%\), first-stage \(F \gg 10\), same sign, and CI width ratio \(1.08\). All four conditions clear, so the MVP retains the OLS estimate as the working number and documents the limits of this sample's identification rather than switching to an IV headline.

**Same-chain caveat.** The other-store instrument does not break chain-wide promotional calendars, manufacturer funding windows, or Chicago-local demand shocks. The Sargan over-identification test rejects at \(p < 0.001\), but at this sample size even an economically negligible coefficient difference between \(Z_H\) and \(Z_C\) is statistically detectable; we read the rejection as a same-chain diagnostic rather than an IV invalidation. Multi-chain, multi-metro data or external wholesale-cost shifters would be the path to definitive causal identification and are outside the MVP scope.

### 10.2 Experimental Validation

The fixed-effects design and the IV sensitivity check together establish bounds on the own-price elasticity, but neither replaces experimental evidence. Any recommended price or promotion action should be tested through randomized or quasi-experimental rollout before production deployment. In the DFF context, a natural design is store-level or store-cluster-level randomization over weeks. In an online environment, user-, session-, or geo-level randomization may be feasible depending on the operational setting.

## 11. Robustness and Extensions

The MVP already compares the brand-size model against a UPC-level robustness model and checks that the own-price, cross-price, and promotion coefficients have stable signs. Additional robustness checks should include models with and without competitor price, sensitivity of recommendations to elasticity bounds, holdout prediction diagnostics, and smearing-factor diagnostics.

As an additional robustness check, the project estimates specifications with store-week fixed effects:

\[
\log(Q_{ist}) =
\alpha_{is}
+
\lambda_{st}
+
\beta_{own}\log(P^{eff}_{ist})
+
\theta Promo_{ist}
+
\epsilon_{ist}.
\]

The store-week fixed effect \(\lambda_{st}\) absorbs local demand shocks, store-level campaigns, and week-specific inventory or traffic conditions. This is important because DFF prices and promotions are manager choices, and the sale-code variable is not a clean randomized treatment. The DFF documentation also notes that sale coding is imperfect: if the sale code is not set, there still may have been a promotion that week. The store-week-FE specification sacrifices some cross-price variation but provides a stricter check on whether the own-price elasticity is driven by local store-week confounding. The competitor-price index is excluded from the store-week-FE robustness specification because it is mechanically absorbed by \(\lambda_{st}\): the competitor index is constant within a (store, week). This specification is reported as M0b in §10.1; \(\hat\beta_{own}\) moves from \(-1.728\) (week FE) to \(-1.805\) (store\(\times\)week FE), a 4.4\% change that bounds the contribution of unobserved local demand shocks.

A same-brand cross-size price index captures within-brand cannibalization, which is especially relevant when the optimizer recommends price increases for one package size that may shift demand to another size of the same brand. Notebook 07 adds a baseline-quantity-weighted same-brand other-size log-price index to the demand specification and estimates a positive and significant coefficient of \(\hat\beta_{same} = +0.231\) (SE 0.008). Plugging this coefficient into an ex-post spillover adjustment on the top-10 portfolio candidates gives a median \(|adjustment|\) of \(2.5\%\) (maximum \(4.0\%\)) — within-brand substitution is detectable but well below the \(10-15\%\) band that would justify rebuilding the optimizer around a joint multi-size objective. The per-cell optimizer is retained; the cannibalization diagnostic is surfaced in the Limitations page of the app so the size of the correction is visible without replacing the optimizer.

A full brand-pair substitution matrix would require a richer differentiated-products demand system. Temporary promotions may induce household stockpiling, so a static weekly demand model may misstate longer-run price response; Hendel and Nevo (2006) provide the canonical warning for this dynamic issue. Both extensions are noted in the app's Limitations roadmap as post-MVP work.

## 12. Relationship to Prior Literature

This project is closest in spirit to empirical scanner-data demand estimation and pricing optimization. The DFF price, quantity, movement, sale-code, and profit-margin variables come from the DFF documentation; the effective-price, dollar-sales, and unit-cost formulas are accounting transformations of those fields, not arbitrary definitions. The unit-cost measure is a gross-margin-derived average-acquisition-cost proxy, not an observed marginal cost.

BLP (1995) provides the structural differentiated-products framework that motivates thinking about substitution and market power. Nevo (2001) applies related ideas to ready-to-eat cereal and documents the role of product differentiation and multi-product pricing in explaining margins. These papers motivate the cereal-market context and the importance of substitution, but they are not the source of the reduced-form fixed-effects equation used in this MVP. The present project does not estimate a structural random-coefficients model.

The retransformation correction follows Duan (1983). The competitor-price index and anchored counterfactual demand function are project-specific implementations: the former summarizes the competitive environment, and the latter is an algebraic relative-response implementation of the estimated log-log demand model. They should not be described as a structural cross-price system or as published formulas. The revenue and profit equations are accounting and decision-objective formulas, not econometric estimators.

The revenue and pricing optimization layer is motivated by revenue-management and pricing-optimization treatments such as Talluri and van Ryzin (2004) and Phillips (2005). The grid search is an implementation of constrained pricing optimization, not a new optimization method. The identification caveats are consistent with the applied econometrics perspective in Angrist and Pischke (2009) and with the broader causal-inference distinction between observational adjustment and experimental validation. The online experimentation component follows the practical controlled-experiment logic summarized by Kohavi, Tang, and Xu (2020); it is a validation design, not causal proof from the observational model itself.

## References

Angrist, Joshua D., and Jörn-Steffen Pischke. 2009. *Mostly Harmless Econometrics: An Empiricist's Companion*. Princeton University Press. DOI: [10.1515/9781400829828](https://doi.org/10.1515/9781400829828).

Berry, Steven, James Levinsohn, and Ariel Pakes. 1995. "Automobile Prices in Market Equilibrium." *Econometrica* 63(4): 841-890. DOI: [10.2307/2171802](https://doi.org/10.2307/2171802).

Duan, Naihua. 1983. "Smearing Estimate: A Nonparametric Retransformation Method." *Journal of the American Statistical Association* 78(383): 605-610. DOI: [10.1080/01621459.1983.10478017](https://doi.org/10.1080/01621459.1983.10478017).

Hendel, Igal, and Aviv Nevo. 2006. "Sales and Consumer Inventory." *RAND Journal of Economics* 37(3): 543-561. DOI: [10.1111/j.1756-2171.2006.tb00030.x](https://doi.org/10.1111/j.1756-2171.2006.tb00030.x).

Imbens, Guido W., and Donald B. Rubin. 2015. *Causal Inference for Statistics, Social, and Biomedical Sciences*. Cambridge University Press. DOI: [10.1017/CBO9781139025751](https://doi.org/10.1017/CBO9781139025751).

Kohavi, Ron, Diane Tang, and Ya Xu. 2020. *Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing*. Cambridge University Press. DOI: [10.1017/9781108653985](https://doi.org/10.1017/9781108653985).

Nevo, Aviv. 2001. "Measuring Market Power in the Ready-to-Eat Cereal Industry." *Econometrica* 69(2): 307-342. DOI: [10.1111/1468-0262.00194](https://doi.org/10.1111/1468-0262.00194).

Phillips, Robert L. 2005. *Pricing and Revenue Optimization*. Stanford Business Books. DOI: [10.1515/9780804781640](https://doi.org/10.1515/9780804781640).

Talluri, Kalyan T., and Garrett J. van Ryzin. 2004. *The Theory and Practice of Revenue Management*. Springer. DOI: [10.1007/b139000](https://doi.org/10.1007/b139000).

UChicago Booth Kilts Center for Marketing. n.d. "Dominick's Finer Foods Database." Accessed April 2026. [https://www.chicagobooth.edu/research/kilts/research-data/dominicks](https://www.chicagobooth.edu/research/kilts/research-data/dominicks).
