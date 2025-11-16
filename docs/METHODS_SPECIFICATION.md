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
d_j &\sim \mathcal{N}(0, 100^2), \quad j = 2, \ldots, J \\
\tau &\sim \text{Half-Normal}(0, 1)
\end{align}
$$

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

**Direct evidence:**
$$d_{AB}^{\text{direct}} \sim \mathcal{N}(0, 100^2)$$

**Network (indirect) evidence:**
$$d_{AB}^{\text{indirect}} = d_B - d_A$$

**Inconsistency parameter:**
$$\omega_{AB} = d_{AB}^{\text{direct}} - d_{AB}^{\text{indirect}}$$

$$\omega_{AB} \sim \mathcal{N}(0, 10^2)$$

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

When inconsistency is detected, down-weight inconsistent loops:

$$w_i^* = w_i \cdot \exp(-\alpha |\omega_i|)$$

where $\omega_i$ is the inconsistency in the loop containing comparison $i$, and $\alpha$ is a tuning parameter.

Alternatively, bias adjustment model:

$$\delta_{ik} \sim \mathcal{N}(d_{t_{ik}} - d_{t_{i1}} + b_i, \tau^2)$$

where $b_i \sim \mathcal{N}(0, \sigma_b^2)$ is a study-specific bias term with:
$$\sigma_b \sim \text{Half-Normal}(0, \tau_{\text{bias}})$$

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

## 12. References

1. Dias, S., Welton, N. J., Caldwell, D. M., & Ades, A. E. (2010). Checking consistency in mixed treatment comparison meta-analysis. *Statistics in Medicine*, 29(7-8), 932-944.

2. Jansen, J. P., Fleurence, R., Devine, B., et al. (2011). Interpreting indirect treatment comparisons and network meta-analysis for health-care decision making. *PharmacoEconomics*, 29(5), 369-382.

3. Salanti, G., Ades, A. E., & Ioannidis, J. P. (2011). Graphical methods and numerical summaries for presenting results from multiple-treatment meta-analysis. *Journal of Clinical Epidemiology*, 64(2), 163-171.

4. Meinshausen, N., & Bühlmann, P. (2010). Stability selection. *Journal of the Royal Statistical Society: Series B*, 72(4), 417-473.

5. Rubin, D. B. (1987). *Multiple Imputation for Nonresponse in Surveys*. John Wiley & Sons.

6. Gelman, A., Carlin, J. B., Stern, H. S., et al. (2013). *Bayesian Data Analysis* (3rd ed.). CRC Press.
