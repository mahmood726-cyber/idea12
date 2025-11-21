# Mathematical Specification for Network Meta-Regression with Inconsistency Modeling

## 1. Introduction

This document provides the complete mathematical specification for the network meta-regression framework implemented in `netmetareg`. The methodology combines network meta-analysis (NMA), meta-regression with effect modifiers, and inconsistency detection in a unified Bayesian and frequentist framework.

## 2. Notation

### 2.1 Data Structure

- $i = 1, \ldots, N$: Study index
- $k = 1, \ldots, K_i$: Treatment arm index within study $i$
- $j = 1, \ldots, J$: Treatment index in network
- $t_{ik}$: Treatment assigned to arm $k$ in study $i$
- $y_{ik}$: Observed effect size in arm $k$ of study $i$
- $\text{se}_{ik}$: Standard error of $y_{ik}$
- $\mathbf{X}_i = (X_{i1}, \ldots, X_{iP})^T$: Vector of $P$ study-level covariates

### 2.2 Parameters

- $d_j$: Effect of treatment $j$ relative to reference treatment ($d_1 = 0$)
- $\delta_{ik}$: Study-specific effect for arm $k$ in study $i$ (random effect)
- $\tau^2$: Between-study heterogeneity variance
- $\boldsymbol{\beta}$: Vector of meta-regression coefficients
- $\boldsymbol{\gamma}_{j}$: Treatment-specific covariate effects (interactions)
- $\omega_{jj'}$: Inconsistency parameter for comparison $j$ vs $j'$

## 3. Core Network Meta-Analysis Models

### 3.1 Contrast-Based Model (Random Effects)

The fundamental model for observed contrasts:

$$y_{ik} \sim \mathcal{N}(\delta_{ik}, \text{se}_{ik}^2), \quad k = 2, \ldots, K_i$$

where $\delta_{i1} = 0$ (baseline arm) and for $k > 1$:

$$\delta_{ik} \sim \mathcal{N}(d_{t_{ik}} - d_{t_{i1}}, \tau^2)$$

**Priors (Bayesian framework):**
$$
\begin{align}
d_j &\sim \mathcal{N}(0, 1.5^2), \quad j = 2, \ldots, J \quad \text{(weakly informative)} \\
\tau &\sim \text{Half-Normal}(0, 0.5) \quad \text{(implies median tau} \approx 0.35\text{)}
\end{align}
$$

**Prior justification:**
- $\sigma_d = 1.5$: Places 95% prior mass on effects between -3 and 3 (log scale), appropriate for most health outcomes
- $\sigma_\tau = 0.5$: Based on empirical distributions from Turner et al. (2012) for typical RCT heterogeneity

**Likelihood (Frequentist framework):**

Using generalized least squares with variance-covariance matrix:
$$\mathbf{V} = \mathbf{S} + \tau^2 \mathbf{I}$$

where $\mathbf{S}$ is the within-study covariance matrix. For multi-arm trials, within-study correlation is 0.5 for contrasts sharing a baseline.

### 3.2 Multi-Arm Trial Adjustment

For studies with $K_i > 2$ arms, the within-study variance-covariance matrix is:

$$
\mathbf{S}_i =
\begin{pmatrix}
\text{se}_{i2}^2 & \frac{1}{2}\text{se}_{i2}\text{se}_{i3} & \cdots \\
\frac{1}{2}\text{se}_{i2}\text{se}_{i3} & \text{se}_{i3}^2 & \cdots \\
\vdots & \vdots & \ddots
\end{pmatrix}
$$

This accounts for the correlation between contrasts that share the same baseline arm.

**Note on correlation structure:** The correlation of 0.5 is exact when effects are measured as differences in means with equal variances, or when log odds ratios are computed from large samples. For finite samples with binary outcomes, the exact correlation is:

$$\text{Corr}(\hat{y}_{i2}, \hat{y}_{i3}) = \sqrt{\frac{n_{i1}/(n_{i1} + n_{i2})}{n_{i1}/(n_{i1} + n_{i3})}}$$

For most practical purposes with moderate to large sample sizes, the 0.5 approximation is adequate (White et al., 2012).

## 4. Network Meta-Regression

### 4.1 Main Effects Model

Incorporating study-level covariates:

$$\delta_{ik} \sim \mathcal{N}(d_{t_{ik}} - d_{t_{i1}} + \mathbf{X}_i^T \boldsymbol{\beta}, \tau^2)$$

The meta-regression coefficient $\beta_p$ represents the change in relative treatment effect associated with a one-unit increase in covariate $X_p$, averaged across all treatments.

### 4.2 Treatment-by-Covariate Interaction Model

Allowing treatment-specific covariate effects:

$$\delta_{ik} \sim \mathcal{N}(d_{t_{ik}} - d_{t_{i1}} + \mathbf{X}_i^T (\boldsymbol{\beta} + \boldsymbol{\gamma}_{t_{ik}} - \boldsymbol{\gamma}_{t_{i1}}), \tau^2)$$

where $\boldsymbol{\gamma}_j = (\gamma_{j1}, \ldots, \gamma_{jP})^T$ are treatment-specific interaction terms.

**Priors:**
$$\beta_p \sim \mathcal{N}(0, 1^2), \quad \gamma_{jp} \sim \mathcal{N}(0, 1^2)$$

### 4.3 Hierarchical Centering

To improve interpretation and avoid extrapolation, covariates are centered at the network mean:

$$\tilde{X}_{ip} = X_{ip} - \bar{X}_p$$

where $\bar{X}_p = \frac{1}{N}\sum_{i=1}^N X_{ip}$.

This ensures that $d_j$ represents the treatment effect at the average covariate values in the network.

## 5. Inconsistency Models

### 5.1 Node-Splitting Model

For a comparison $A$ vs $B$ with both direct and indirect evidence, we estimate:

**Model specification:**

We estimate separate parameters for direct and network evidence:
$$d_{AB}^{\text{direct}} \sim \mathcal{N}(0, 1.5^2)$$

The network evidence is derived from the basic effects:
$$d_{AB}^{\text{network}} = d_B - d_A$$

where $d_A, d_B$ are estimated from all data except the direct A vs B comparisons.

**Inconsistency parameter:**
$$\omega_{AB} = d_{AB}^{\text{direct}} - d_{AB}^{\text{network}}$$

Prior on inconsistency:
$$\omega_{AB} \sim \mathcal{N}(0, 1^2)$$

**Likelihood for direct comparisons:**
For studies directly comparing A vs B:
$$y_i \sim \mathcal{N}(d_{AB}^{\text{direct}}, \text{se}_i^2 + \tau^2)$$

**Likelihood for indirect comparisons:**
For all other studies in the network:
$$y_i \sim \mathcal{N}(d_{t_{i,\text{active}}} - d_{t_{i,\text{baseline}}}, \text{se}_i^2 + \tau^2)$$

where the basic effects $d_j$ inform only the indirect estimate.

The posterior distribution of $\omega_{AB}$ quantifies inconsistency. Evidence of inconsistency is indicated by:
- $P(|\omega_{AB}| > 0) > 0.95$ (Bayesian p-value < 0.05)
- 95% credible interval excluding zero

### 5.2 Design-by-Treatment Interaction Model

Extending the basic model to include design-specific effects:

$$\delta_{ik} \sim \mathcal{N}(d_{t_{ik}} - d_{t_{i1}} + \gamma_{D_i, t_{ik}} - \gamma_{D_i, t_{i1}}, \tau^2)$$

where $D_i$ is the design type of study $i$ (defined by the set of treatments compared), and $\gamma_{d,j}$ is the design-by-treatment interaction.

**Prior:**
$$\gamma_{d,j} \sim \mathcal{N}(0, 10^2)$$

**Inconsistency test:**
Evidence of inconsistency if $\max_{d,j} |\gamma_{d,j}| > \epsilon$ (threshold $\epsilon \approx 1$).

## 6. Novel Methodological Extensions

### 6.1 LASSO Covariate Selection

To prevent overfitting with many candidate covariates, apply L1 penalization:

$$\hat{\boldsymbol{\beta}} = \arg\min_{\boldsymbol{\beta}} \left\{ \sum_{i=1}^N w_i (y_i - \mathbf{x}_i^T \boldsymbol{\beta})^2 + \lambda \|\boldsymbol{\beta}\|_1 \right\}$$

where $w_i = 1/\text{se}_i^2$ and $\lambda$ is chosen by cross-validation.

**Elastic Net** (combining L1 and L2):
$$\text{Penalty} = \lambda \left[ \alpha \|\boldsymbol{\beta}\|_1 + \frac{1-\alpha}{2}\|\boldsymbol{\beta}\|_2^2 \right]$$

### 6.2 Stability Selection

Bootstrap-based variable selection:

1. For $b = 1, \ldots, B$ bootstrap samples:
   - Draw subsample of size $\lfloor 0.8N \rfloor$
   - Fit LASSO
   - Record selected variables: $S_b$

2. Selection frequency: $\pi_p = \frac{1}{B}\sum_{b=1}^B \mathbb{1}(p \in S_b)$

3. Select covariates with $\pi_p > 0.6$ (threshold)

### 6.3 Multiple Imputation for Missing Covariates

Using multiple imputation by chained equations (MICE):

1. Create $M$ imputed datasets: $\tilde{\mathbf{X}}^{(1)}, \ldots, \tilde{\mathbf{X}}^{(M)}$

2. Fit NMA model on each: $\hat{d}_j^{(m)}, \text{Var}(\hat{d}_j^{(m)})$

3. **Rubin's Rules for pooling:**

$$\bar{d}_j = \frac{1}{M}\sum_{m=1}^M \hat{d}_j^{(m)}$$

**Within-imputation variance:**
$$W = \frac{1}{M}\sum_{m=1}^M \text{Var}(\hat{d}_j^{(m)})$$

**Between-imputation variance:**
$$B = \frac{1}{M-1}\sum_{m=1}^M (\hat{d}_j^{(m)} - \bar{d}_j)^2$$

**Total variance:**
$$T = W + \left(1 + \frac{1}{M}\right)B$$

**Diagnostics:**
- Relative increase in variance: $r = (1 + 1/M)B/W$
- Fraction of missing information: $\lambda = (1 + 1/M)B/T$

### 6.4 Inconsistency Adjustment

**Note:** These methods are experimental extensions and should be used with caution.

**Option 1: Down-weighting approach (exploratory)**

When inconsistency is detected, one option is to down-weight studies in inconsistent comparisons:

$$w_i^* = w_i \cdot \exp(-\alpha |\hat{\omega}_i|)$$

where $\hat{\omega}_i$ is the estimated inconsistency involving study $i$, and $\alpha$ is chosen via sensitivity analysis (typical values: 0.5-2.0).

**Limitations:** This approach lacks formal theoretical justification and should only be used in sensitivity analyses.

**Option 2: Bias adjustment model**

Incorporate study-specific bias terms:

$$\delta_{ik} \sim \mathcal{N}(d_{t_{ik}} - d_{t_{i1}} + b_i, \tau^2)$$

where $b_i \sim \mathcal{N}(0, \sigma_b^2)$ allows for study-specific biases.

**Prior on bias variance:**
$$\sigma_b \sim \text{Half-Normal}(0, 0.5)$$

This approach is related to bias-adjustment models in meta-epidemiology (Welton et al., 2009).

**Recommendation:** When inconsistency is detected, priority should be given to:
1. Investigating sources through meta-regression
2. Subgroup analyses by design characteristics
3. Expert assessment of clinical/methodological differences
Rather than automatic down-weighting procedures.

## 7. Prediction for New Populations

Given covariate values $\mathbf{X}_{\text{new}}$ for a target population:

$$\hat{d}_{jj'}^{\text{new}} = \hat{d}_j - \hat{d}_{j'} + \mathbf{X}_{\text{new}}^T (\hat{\boldsymbol{\beta}} + \hat{\boldsymbol{\gamma}}_j - \hat{\boldsymbol{\gamma}}_{j'})$$

**Bayesian prediction interval:**

Sample from posterior:
$$d_{jj'}^{\text{new}} \sim p(d_{jj'}^{\text{new}} | \mathbf{Y}, \mathbf{X}_{\text{new}})$$

**Credible interval:** 2.5th and 97.5th percentiles of posterior samples.

**Extrapolation check:**

For each covariate $p$:
$$z_p = \frac{X_{\text{new},p} - \bar{X}_p}{\text{SD}(X_p)}$$

Flag extrapolation if $|z_p| > 2$ or $X_{\text{new},p} \notin [\min(X_p), \max(X_p)]$.

## 8. Treatment Ranking

### 8.1 SUCRA (Bayesian)

Surface Under the Cumulative Ranking curve:

$$\text{SUCRA}_j = \frac{1}{J-1}\sum_{r=1}^{J-1} P(\text{rank}_j \leq r | \mathbf{Y})$$

where $P(\text{rank}_j \leq r | \mathbf{Y})$ is computed from posterior samples.

### 8.2 P-Score (Frequentist)

$$P_j = \frac{1}{J-1}\sum_{j' \neq j} \Phi\left(\frac{d_j - d_{j'}}{\text{SE}(d_j - d_{j'})}\right)$$

where $\Phi$ is the standard normal CDF.

## 9. Model Comparison

### 9.1 Bayesian (WAIC)

Widely Applicable Information Criterion:

$$\text{WAIC} = -2(\text{lppd} - p_{\text{WAIC}})$$

where:
- $\text{lppd} = \sum_i \log\left(\frac{1}{S}\sum_s p(y_i | \theta^{(s)})\right)$
- $p_{\text{WAIC}} = \sum_i \text{Var}_s(\log p(y_i | \theta^{(s)}))$

### 9.2 Frequentist (AIC/BIC)

$$\text{AIC} = -2\log L(\hat{\theta}) + 2k$$
$$\text{BIC} = -2\log L(\hat{\theta}) + k\log N$$

where $k$ is the number of parameters.

## 10. Heterogeneity Assessment

### 10.1 Between-Study Variance

$$\tau^2 \sim \text{Half-Normal}(0, 1)^2 \quad \text{(Bayesian)}$$

$$\hat{\tau}^2 = \max\left(0, \frac{Q - df}{C}\right) \quad \text{(Frequentist DerSimonian-Laird)}$$

where:
- $Q = \mathbf{r}^T \mathbf{S}^{-1} \mathbf{r}$ (Cochran's Q)
- $df = N - J + 1$
- $C = \text{tr}(\mathbf{S}^{-1}) - \text{tr}(\mathbf{X}^T\mathbf{S}^{-1}\mathbf{X}(\mathbf{X}^T\mathbf{S}^{-1}\mathbf{X})^{-1})$

### 10.2 I² Statistic

$$I^2 = \max\left(0, 100\% \times \frac{Q - df}{Q}\right)$$

Interpretation:
- $I^2 < 25\%$: Low heterogeneity
- $25\% \leq I^2 < 50\%$: Moderate
- $I^2 \geq 50\%$: Substantial

## 11. Software Implementation

All models are implemented in Python with:

- **Bayesian estimation:** PyMC (NUTS sampler)
- **Frequentist estimation:** NumPy/SciPy (GLS, REML)
- **Regularization:** scikit-learn (LASSO, elastic net)
- **Network analysis:** NetworkX
- **Visualization:** Matplotlib, Seaborn, ArviZ

## 12. Advanced Methodological Extensions

### 12.1 Horseshoe Prior for Sparse Covariate Selection

The horseshoe prior provides continuous shrinkage with superior properties to LASSO:

$$\beta_p \sim \mathcal{N}(0, \lambda_p \tau), \quad \lambda_p \sim \text{Half-Cauchy}(0, 1), \quad \tau \sim \text{Half-Cauchy}(0, \tau_0)$$

where $\tau_0 = \frac{p_0}{p - p_0} \frac{1}{\sqrt{N}}$ is determined by expected sparsity.

**Regularized Horseshoe (Piironen & Vehtari 2017):**

$$\tilde{\lambda}_p = \frac{\lambda_p \sqrt{c^2}}{{\sqrt{c^2 + \tau^2 \lambda_p^2}}}, \quad c^2 \sim \text{InverseGamma}(\nu_{\text{slab}}/2, \nu_{\text{slab}} s_{\text{slab}}^2/2)$$

This adds a "slab" component that prevents overfitting while maintaining strong shrinkage for noise covariates.

**Advantages over LASSO:**
- Stronger shrinkage toward zero for noise covariates
- Minimal shrinkage for true signals
- No need for cross-validation to select penalty parameter
- Full posterior distribution for inference

### 12.2 Robust Models with Student-t Likelihood

To handle outliers and heavy-tailed distributions:

$$y_{ik} \sim \text{StudentT}(\nu, \delta_{ik}, \text{se}_{ik})$$

where $\nu$ controls tail thickness:
- $\nu = 3\text{-}5$: Heavy tails, robust to outliers
- $\nu > 30$: Approximately normal
- Estimate $\nu$ from data: $\nu \sim \text{Gamma}(2, 0.1)$

**Benefits:**
- Automatically down-weights outliers
- More realistic for heterogeneous evidence
- Better predictive performance in presence of outliers

### 12.3 Treatment-Specific Heterogeneity

Instead of common $\tau^2$, allow treatment-specific heterogeneity:

$$\delta_{ik} \sim \mathcal{N}(d_{t_{ik}} - d_{t_{i1}}, \tau_{t_{ik}}^2)$$

with hierarchical prior:
$$\tau_j \sim \text{Half-Normal}(0, \sigma_{\tau}), \quad \sigma_{\tau} \sim \text{Half-Cauchy}(0, 0.5)$$

### 12.4 Advanced Model Comparison

**Leave-One-Out Cross-Validation (LOO-CV):**

$$\text{ELPD}_{\text{LOO}} = \sum_{i=1}^N \log p(y_i | y_{-i})$$

Estimated using Pareto Smoothed Importance Sampling (PSIS). Diagnostics:
- Pareto $k < 0.5$: Good
- $0.5 \leq k < 0.7$: OK
- $k \geq 0.7$: Unreliable (use K-fold CV)

**Model Averaging via Stacking:**

Find optimal weights $w_m$ to minimize:
$$\sum_{i=1}^N \left(\log \sum_{m=1}^M w_m p_m(y_i | y_{-i})\right)$$

subject to $\sum w_m = 1, w_m \geq 0$.

### 12.5 Posterior Predictive Checks

For test statistic $T(\cdot)$, compute Bayesian p-value:

$$p_B = P(T(y^{\text{rep}}) \geq T(y^{\text{obs}}) | y^{\text{obs}})$$

Test statistics include:
- Mean, variance, min, max
- Quantiles
- Model-specific features

**LOO-PIT (Probability Integral Transform):**

$$\text{PIT}_i = P(y_i^{\text{rep}} \leq y_i^{\text{obs}} | y_{-i})$$

Should be uniform under correct model.

### 12.6 Publication Bias Methods

**Selection Models:**

Model publication probability as function of p-value:
$$P(\text{published} | \text{effect}, \text{se}) = \frac{1}{1 + \exp(-\alpha - \beta |z|)}$$

**Comparison-Adjusted Funnel Plot:**

For network MA, adjust for comparison type:
$$y_i^{\text{adj}} = y_i - \hat{d}_{AB}^{\text{network}}$$

Test asymmetry using adjusted effects.

**P-curve Analysis:**

Tests if distribution of significant p-values is:
- Right-skewed (evidential value)
- Flat or left-skewed (p-hacking/bias)

### 12.7 Network Coherence and Contribution Analysis

**Contribution Matrix:**

For design matrix $\mathbf{X}$, the hat matrix:
$$\mathbf{H} = \mathbf{X}(\mathbf{X}^T\mathbf{X})^{-1}\mathbf{X}^T$$

gives contribution of direct evidence to network estimates.

**Network Connectivity:**
- Bridges: Edges whose removal disconnects network
- Articulation points: Critical nodes
- Evidence diversity: Number of independent paths

### 12.8 Prediction Intervals

**Frequentist Prediction Interval:**

$$\text{PI} = \hat{d}_j \pm t_{\alpha/2, df} \sqrt{\text{SE}(\hat{d}_j)^2 + \hat{\tau}^2}$$

Accounts for both estimation uncertainty and between-study heterogeneity.

**Bayesian Prediction:**

For future study effect $\theta^{\text{new}}$:
$$\theta^{\text{new}} | \mathbf{y} \sim \int \mathcal{N}(\theta^{\text{new}} | d_j, \tau^2) p(d_j, \tau | \mathbf{y}) \, dd_j \, d\tau$$

Sample from posterior to get full predictive distribution.

**Prediction for New Population:**

With covariate vector $\mathbf{X}_{\text{new}}$:
$$\hat{d}_{jj'}^{\text{new}} = \hat{d}_j - \hat{d}_{j'} + \mathbf{X}_{\text{new}}^T (\hat{\boldsymbol{\beta}} + \hat{\boldsymbol{\gamma}}_j - \hat{\boldsymbol{\gamma}}_{j'})$$

with prediction interval accounting for $\tau^2$ and parameter uncertainty.

### 12.9 Small-Study Effects Detection

**Egger's Test:** Regress effect on precision
**Harbord's Test:** Modified for binary outcomes
**Peters' Test:** Uses sample size instead of precision
**DOI Plot:** Alternative visualization to funnel plot
**Trim-and-Fill:** Estimates missing studies and adjusts

## 13. Software Implementation

All models implemented in Python with:

- **Bayesian estimation:** PyMC (NUTS sampler, automatic differentiation)
- **Diagnostics:** ArviZ (LOO-CV, PSIS, convergence diagnostics)
- **Frequentist estimation:** NumPy/SciPy (GLS, REML, optimization)
- **Regularization:** scikit-learn (LASSO, elastic net, cross-validation)
- **Network analysis:** NetworkX (graph algorithms, connectivity)
- **Visualization:** Matplotlib, Seaborn, ArviZ plots

## 14. References

### Core NMA Methodology

1. Dias, S., Welton, N. J., Caldwell, D. M., & Ades, A. E. (2010). Checking consistency in mixed treatment comparison meta-analysis. *Statistics in Medicine*, 29(7-8), 932-944.

2. Jansen, J. P., Fleurence, R., Devine, B., et al. (2011). Interpreting indirect treatment comparisons and network meta-analysis for health-care decision making. *PharmacoEconomics*, 29(5), 369-382.

3. Salanti, G., Ades, A. E., & Ioannidis, J. P. (2011). Graphical methods and numerical summaries for presenting results from multiple-treatment meta-analysis. *Journal of Clinical Epidemiology*, 64(2), 163-171.

4. Rubin, D. B. (1987). *Multiple Imputation for Nonresponse in Surveys*. John Wiley & Sons.

5. Gelman, A., Carlin, J. B., Stern, H. S., et al. (2013). *Bayesian Data Analysis* (3rd ed.). CRC Press.

### Advanced Bayesian Methods

6. Carvalho, C. M., Polson, N. G., & Scott, J. G. (2010). The horseshoe estimator for sparse signals. *Biometrika*, 97(2), 465-480.

7. Piironen, J., & Vehtari, A. (2017). Sparsity information and regularization in the horseshoe and other shrinkage priors. *Electronic Journal of Statistics*, 11(2), 5018-5051.

8. Gelman, A. (2006). Prior distributions for variance parameters in hierarchical models. *Bayesian Analysis*, 1(3), 515-534.

### Model Comparison and Diagnostics

9. Vehtari, A., Gelman, A., & Gabry, J. (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing*, 27(5), 1413-1432.

10. Yao, Y., Vehtari, A., Simpson, D., & Gelman, A. (2018). Using stacking to average Bayesian predictive distributions. *Bayesian Analysis*, 13(3), 917-1007.

11. Gabry, J., Simpson, D., Vehtari, A., Betancourt, M., & Gelman, A. (2019). Visualization in Bayesian workflow. *Journal of the Royal Statistical Society: Series A*, 182(2), 389-402.

### Publication Bias

12. Chaimani, A., Higgins, J. P., Mavridis, D., Spyridonos, P., & Salanti, G. (2013). Graphical tools for network meta-analysis in STATA. *PLoS ONE*, 8(10), e76654.

13. Egger, M., Smith, G. D., Schneider, M., & Minder, C. (1997). Bias in meta-analysis detected by a simple, graphical test. *BMJ*, 315(7109), 629-634.

14. Simonsohn, U., Nelson, L. D., & Simmons, J. P. (2014). P-curve: A key to the file-drawer. *Journal of Experimental Psychology: General*, 143(2), 534-547.

15. Copas, J., & Shi, J. Q. (2000). Meta-analysis, funnel plots and sensitivity analysis. *Biostatistics*, 1(3), 247-262.

### Robust Methods

16. Geweke, J. (1993). Bayesian treatment of the independent Student-t linear model. *Journal of Applied Econometrics*, 8(S1), S19-S40.

### Prediction

17. Riley, R. D., Higgins, J. P., & Deeks, J. J. (2011). Interpretation of random effects meta-analyses. *BMJ*, 342, d549.

18. Higgins, J. P., Thompson, S. G., & Spiegelhalter, D. J. (2009). A re-evaluation of random-effects meta-analysis. *Journal of the Royal Statistical Society: Series A*, 172(1), 137-159.

### Variable Selection

19. Meinshausen, N., & Bühlmann, P. (2010). Stability selection. *Journal of the Royal Statistical Society: Series B*, 72(4), 417-473.

### Network Analysis

20. Papakonstantinou, T., Nikolakopoulou, A., Higgins, J. P., Egger, M., & Salanti, G. (2020). CINeMA: Software for semiautomated assessment of the confidence in the results of network meta-analysis. *Campbell Systematic Reviews*, 16(1), e1080.

21. König, J., Krahn, U., & Binder, H. (2013). Visualizing the flow of evidence in network meta-analysis and characterizing mixed treatment comparisons. *Statistics in Medicine*, 32(30), 5414-5429.
