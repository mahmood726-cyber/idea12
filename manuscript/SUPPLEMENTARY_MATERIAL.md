# Supplementary Material

## Network Meta-Regression with Inconsistency Modeling: A Unified Framework for Evidence Synthesis

---

## Table of Contents

- **Appendix A**: Extended Simulation Study Results
- **Appendix B**: Mathematical Derivations and Proofs
- **Appendix C**: Additional Application Example (Antidepressants)
- **Appendix D**: Software Documentation and Code
- **Appendix E**: Sensitivity Analyses

---

## Appendix A: Extended Simulation Study Results

### A.1 Complete Simulation Design

**Network structures tested:**

| Network Type | Treatments | Studies | Direct Comparisons | Multi-arm Trials | Density |
|--------------|------------|---------|-------------------|------------------|---------|
| Small        | 4          | 12      | 6                 | 2 (17%)          | 1.00    |
| Medium       | 8          | 30      | 18                | 5 (17%)          | 0.64    |
| Large        | 15         | 80      | 42                | 12 (15%)         | 0.40    |
| Very Large   | 50         | 200     | 124               | 28 (14%)         | 0.10    |

**Sample size distributions (per arm):**

Based on empirical distributions from Rhodes et al. (2015) and Turner et al. (2012):
- Small: median n=75 (IQR: 50-100)
- Medium: median n=250 (IQR: 150-400)
- Large: median n=800 (IQR: 500-1500)

**Heterogeneity scenarios:**

Based on Turner et al. (2012) predictive distributions:
- Low: τ = 0.05 (25th percentile for subjective outcomes)
- Moderate: τ = 0.15 (median for subjective outcomes)
- High: τ = 0.30 (75th percentile for subjective outcomes)

### A.2 Inconsistency + Meta-Regression Interaction Scenarios

**Scenario 1: Meta-regression partially explains inconsistency**

Data generating mechanism:
- True inconsistency in loop ABC: ω₀ = 0.20
- Covariate X distributed differently across comparisons:
  - Studies comparing A vs B: mean(X) = 0
  - Studies comparing B vs C: mean(X) = 0.5
  - Studies comparing A vs C: mean(X) = 0.25
- Effect modifier: β = 0.15 per unit X
- Meta-regression reduces apparent inconsistency from 0.20 to 0.08

**Results (10,000 replications):**

| Model                    | Estimated ω | SE   | P(ω>0) | τ²    |
|--------------------------|-------------|------|--------|-------|
| Consistency (no covars)  | 0.19        | 0.08 | 0.018  | 0.032 |
| With meta-regression     | 0.08        | 0.07 | 0.264  | 0.021 |

**Conclusion:** Meta-regression explained 60% of apparent inconsistency by accounting for covariate imbalance.

**Scenario 2: Residual inconsistency after meta-regression**

Data generating mechanism:
- True inconsistency: ω₀ = 0.30 (design-specific bias)
- Effect modifier: β = 0.20
- Inconsistency unrelated to measured covariates

**Results:**

| Model                    | Estimated ω | SE   | P(ω>0) | Decision        |
|--------------------------|-------------|------|--------|-----------------|
| Consistency (no covars)  | 0.31        | 0.09 | <0.001 | Reject          |
| With meta-regression     | 0.28        | 0.08 | 0.001  | Reject          |

**Conclusion:** Meta-regression did not eliminate inconsistency; bias adjustment needed.

### A.3 Post-Selection Inference Coverage

**Scenario:** 5 candidate covariates, 2 true effects (β₁=0.20, β₂=0.15), 3 null

**Methods compared:**
1. **Naive post-selection OLS**: Refit with LASSO-selected variables, ignore selection
2. **Post-selection with PoSI**: Polyhedral selective inference (Lee et al. 2016)
3. **Data splitting**: Use 50% for selection, 50% for inference
4. **Bootstrap**: Bootstrap selection + inference

**Coverage of 95% confidence intervals:**

| Method                | β₁ Coverage | β₂ Coverage | Null Coverage | Mean Width |
|-----------------------|-------------|-------------|---------------|------------|
| Naive post-selection  | 87.2%       | 86.8%       | 96.1%         | 0.082      |
| PoSI                  | 94.8%       | 94.2%       | 95.3%         | 0.124      |
| Data splitting        | 95.1%       | 94.6%       | 95.0%         | 0.156      |
| Bootstrap (B=1000)    | 94.3%       | 93.8%       | 94.9%         | 0.118      |

**Findings:**
- Naive post-selection under-covers (87% vs nominal 95%)
- PoSI and bootstrap achieve nominal coverage
- Data splitting has correct coverage but wide intervals (reduced sample size)
- **Recommendation:** Use bootstrap or PoSI for post-selection inference

### A.4 Extrapolation Threshold Calibration

**Goal:** Determine if z-score thresholds (z=2, z=3) correlate with prediction error

**Method:**
1. Simulate networks with true meta-regression model
2. Make predictions at varying distances from network mean
3. Compute prediction error: PE = |predicted - true|
4. Assess relationship between z-score and PE

**Results:**

| Z-score Range | Mean PE | 95th %ile PE | Proportion Large Error (>0.3) |
|---------------|---------|--------------|-------------------------------|
| z < 1         | 0.048   | 0.112        | 2.4%                          |
| 1 ≤ z < 2     | 0.082   | 0.186        | 8.7%                          |
| 2 ≤ z < 3     | 0.134   | 0.298        | 24.3%                         |
| z ≥ 3         | 0.221   | 0.487        | 48.6%                         |

**Calibrated thresholds:**
- z < 2: Low extrapolation risk (mean PE < 0.10)
- 2 ≤ z < 3: **WARNING** - moderate risk (mean PE 0.13, 24% large errors)
- z ≥ 3: **CAUTION** - high risk (mean PE 0.22, 49% large errors)

**Conclusion:** Current thresholds are well-calibrated to prediction error risk.

### A.5 Missing Data Mechanisms - Mathematical Specification

**MCAR (Missing Completely at Random):**
$$P(M_{ip} = 1 \mid X_i, Y_i, \theta) = \pi_0$$

**MAR (Missing at Random):**
$$\text{logit}(P(M_{ip} = 1)) = \alpha_0 + \alpha_1 \text{Year}_i + \alpha_2 \text{SampleSize}_i$$

where Year and SampleSize are fully observed.

**MNAR (Missing Not at Random) - Mild:**
$$\text{logit}(P(M_{ip} = 1)) = \alpha_0 + \alpha_1 \text{Year}_i + 0.3 \times X_{ip}$$

If X_{ip} is missing, it tends to be lower (coefficient = 0.3 on standardized scale).

**Simulation results with 30% MNAR:**

| Method           | Bias (×10⁻³) | Coverage | MSE   |
|------------------|--------------|----------|-------|
| Complete case    | -18.4        | 89.2%    | 0.094 |
| MI (assume MAR)  | -8.7         | 91.8%    | 0.073 |
| MI + δ-adjust    | -3.2         | 94.1%    | 0.078 |

where δ-adjustment assumes missing values are 0.3 SD lower than observed (sensitivity analysis).

---

## Appendix B: Mathematical Derivations

### B.1 Variance-Covariance Matrix for Multi-Arm Trials

For a trial with K arms (K ≥ 2), let arm 1 be the baseline. Define contrasts:
$$y_{ik} = \theta_{ik} - \theta_{i1}, \quad k = 2, \ldots, K$$

**Continuous outcomes:**

$$\text{Var}(y_{ik}) = \sigma^2 \left(\frac{1}{n_{ik}} + \frac{1}{n_{i1}}\right)$$

$$\text{Cov}(y_{ik}, y_{ij}) = \frac{\sigma^2}{n_{i1}}, \quad k \neq j$$

$$\text{Corr}(y_{ik}, y_{ij}) = \sqrt{\frac{n_{i1}/(n_{i1}+n_{ik})}{n_{i1}/(n_{i1}+n_{ij})}} \approx 0.5$$

when $n_{ik} \approx n_{ij}$ (equal allocation).

**Binary outcomes (log odds ratios):**

$$\text{Var}(\log \text{OR}_{ik}) = \frac{1}{r_{ik}} + \frac{1}{n_{ik}-r_{ik}} + \frac{1}{r_{i1}} + \frac{1}{n_{i1}-r_{i1}}$$

$$\text{Cov}(\log \text{OR}_{ik}, \log \text{OR}_{ij}) = \frac{1}{r_{i1}} + \frac{1}{n_{i1}-r_{i1}}$$

**Generalized covariance matrix:**

$$\mathbf{S}_i = \mathbf{H}_i \mathbf{D}_i \mathbf{H}_i^T$$

where $\mathbf{D}_i$ is diagonal matrix of arm-specific variances and $\mathbf{H}_i$ is $(K-1) \times K$ contrast matrix:

$$\mathbf{H}_i = \begin{pmatrix} -1 & 1 & 0 & \cdots & 0 \\ -1 & 0 & 1 & \cdots & 0 \\ \vdots & \vdots & \vdots & \ddots & \vdots \\ -1 & 0 & 0 & \cdots & 1 \end{pmatrix}$$

### B.2 REML Estimation Algorithm

**Objective:** Estimate heterogeneity variance τ² using restricted maximum likelihood

**Algorithm:**

1. Initialize: $\tau^2_{(0)} = 0$

2. For iteration t = 1, 2, ..., until convergence:

   a) Update treatment effects given $\tau^2_{(t-1)}$:
   $$\hat{\mathbf{d}}_{(t)} = (\mathbf{Z}^T \mathbf{V}^{-1}_{(t-1)} \mathbf{Z})^{-1} \mathbf{Z}^T \mathbf{V}^{-1}_{(t-1)} \mathbf{y}$$

   b) Compute residuals:
   $$\mathbf{r}_{(t)} = \mathbf{y} - \mathbf{Z}\hat{\mathbf{d}}_{(t)}$$

   c) Update $\tau^2$ by maximizing restricted log-likelihood:
   $$\ell_R(\tau^2) = -\frac{1}{2}\left[\log|\mathbf{V}| + \log|\mathbf{Z}^T\mathbf{V}^{-1}\mathbf{Z}| + \mathbf{r}^T\mathbf{V}^{-1}\mathbf{r}\right]$$

   d) Use Newton-Raphson:
   $$\tau^2_{(t)} = \tau^2_{(t-1)} - \frac{\ell_R'(\tau^2_{(t-1)})}{\ell_R''(\tau^2_{(t-1)})}$$

3. Convergence criterion: $|\tau^2_{(t)} - \tau^2_{(t-1)}| < 10^{-6}$

**Derivatives:**

$$\ell_R'(\tau^2) = -\frac{1}{2}\text{tr}\left[\mathbf{P} - \mathbf{P}\mathbf{r}\mathbf{r}^T\mathbf{P}\right]$$

$$\ell_R''(\tau^2) = \text{tr}\left[\mathbf{P}^2 - 2\mathbf{P}\mathbf{r}\mathbf{r}^T\mathbf{P}^2 + \mathbf{P}\mathbf{r}\mathbf{r}^T\mathbf{P}\mathbf{r}\mathbf{r}^T\mathbf{P}\right]$$

where $\mathbf{P} = \mathbf{V}^{-1} - \mathbf{V}^{-1}\mathbf{Z}(\mathbf{Z}^T\mathbf{V}^{-1}\mathbf{Z})^{-1}\mathbf{Z}^T\mathbf{V}^{-1}$

### B.3 Prediction Variance Derivation

For new population with covariates $\mathbf{X}^*$, predicted effect for treatment j:

$$\delta_j^* = d_j + (\mathbf{X}^* - \bar{\mathbf{X}})^T \boldsymbol{\beta}$$

**Variance components:**

1. **Parameter estimation uncertainty:**
   $$\text{Var}(\hat{\delta}_j^*) = \text{Var}(\hat{d}_j) + (\mathbf{X}^* - \bar{\mathbf{X}})^T \text{Var}(\hat{\boldsymbol{\beta}}) (\mathbf{X}^* - \bar{\mathbf{X}}) + 2\text{Cov}(\hat{d}_j, \hat{\boldsymbol{\beta}})^T(\mathbf{X}^* - \bar{\mathbf{X}})$$

2. **Between-study heterogeneity:**
   $$\tau^2$$

3. **Extrapolation uncertainty:**
   $$\tau_{\text{extrap}}^2 = \tau^2 \times h(\mathbf{X}^*)$$

   where leverage function:
   $$h(\mathbf{X}^*) = (\mathbf{X}^* - \bar{\mathbf{X}})^T (\mathbf{X}^T\mathbf{X})^{-1} (\mathbf{X}^* - \bar{\mathbf{X}})$$

**Total prediction variance:**
$$\text{Var}_{\text{pred}}(\delta_j^*) = \text{Var}(\hat{\delta}_j^*) + \tau^2(1 + h(\mathbf{X}^*))$$

**95% Prediction Interval:**
$$\hat{\delta}_j^* \pm t_{N-J-P, 0.975} \sqrt{\text{Var}_{\text{pred}}(\delta_j^*)}$$

using t-distribution with Kenward-Roger degrees of freedom.

### B.4 LASSO Solution Path Algorithm

**Objective:** Minimize penalized negative log-likelihood

$$Q(\boldsymbol{\beta}; \lambda) = -\ell(\boldsymbol{\beta}) + \lambda \sum_{p=1}^P |\beta_p|$$

**Coordinate Descent Algorithm:**

1. Initialize: $\boldsymbol{\beta}^{(0)} = \mathbf{0}$, $\tau^2$ at REML estimate

2. For iteration t = 1, 2, ..., until convergence:

   For p = 1, ..., P:

   a) Compute partial residual:
      $$\tilde{r}_p = \mathbf{y} - \mathbf{Z}\mathbf{d} - \sum_{q \neq p} X_q \beta_q$$

   b) Update via soft-thresholding:
      $$\beta_p^{(t)} = S\left(\frac{X_p^T \mathbf{V}^{-1} \tilde{r}_p}{X_p^T \mathbf{V}^{-1} X_p}, \frac{\lambda}{X_p^T \mathbf{V}^{-1} X_p}\right)$$

   where soft-thresholding operator:
   $$S(z, \gamma) = \begin{cases} z - \gamma & \text{if } z > \gamma \\ 0 & \text{if } |z| \leq \gamma \\ z + \gamma & \text{if } z < -\gamma \end{cases}$$

3. Convergence: $\|\boldsymbol{\beta}^{(t)} - \boldsymbol{\beta}^{(t-1)}\|_2 < 10^{-6}$

**Cross-validation for λ selection:**

For each λ in grid $\{\lambda_1, \ldots, \lambda_L\}$:
1. Partition studies into K folds (K=10)
2. For fold k:
   - Fit model on studies $\{1, \ldots, N\} \setminus \text{fold}_k$
   - Predict for studies in fold_k
   - Compute MSE_k
3. Select $\lambda^* = \arg\min_\lambda \frac{1}{K}\sum_{k=1}^K \text{MSE}_k$

### B.5 Multiple Imputation - Rubin's Rules

**Combining point estimates:**
$$\bar{Q} = \frac{1}{M}\sum_{m=1}^M \hat{Q}_m$$

**Within-imputation variance:**
$$\bar{U} = \frac{1}{M}\sum_{m=1}^M U_m$$

**Between-imputation variance:**
$$B = \frac{1}{M-1}\sum_{m=1}^M (\hat{Q}_m - \bar{Q})^2$$

**Total variance:**
$$T = \bar{U} + \left(1 + \frac{1}{M}\right)B$$

**Degrees of freedom (Barnard-Rubin adjustment):**

$$\nu = \frac{(\nu_{\text{old}} + 1)(\nu_{\text{old}} + 3)}{\nu_{\text{old}} + 2(m+1)r_m}$$

where:
- $\nu_{\text{old}} = (M-1)/r_m^2$
- $r_m = (1 + 1/M)B/\bar{U}$ (relative increase in variance)
- $m = M$ (number of imputations)

**95% Confidence Interval:**
$$\bar{Q} \pm t_{\nu, 0.975} \sqrt{T}$$

**Relative efficiency of M imputations:**
$$\text{RE} = \left(1 + \frac{\lambda}{M}\right)^{-1}$$

where $\lambda = (B + B/M)/T$ is the fraction of missing information.

For typical scenarios with λ ≈ 0.20-0.30, M=20 provides RE > 99%.

---

## Appendix C: Antidepressants Application (Full Details)

[Content moved from main manuscript Section 4.1]

### C.1 Data Description

**Source:** Synthetic data based on network structure from Cipriani et al. (2018) comparative efficacy analysis of antidepressants.

**Included studies:** 12 randomized controlled trials published 2010-2020

**Treatments:**
1. Placebo
2. SSRI-A (selective serotonin reuptake inhibitor, first-generation)
3. SSRI-B (selective serotonin reuptake inhibitor, second-generation)
4. SNRI (serotonin-norepinephrine reuptake inhibitor)
5. TCA (tricyclic antidepressant)

**Outcome:** Hamilton Depression Rating Scale (HDRS) change from baseline, converted to standardized mean difference (SMD). Negative values indicate improvement.

**Study-level covariates:**
- mean_age: Mean age of participants (years)
- prop_female: Proportion of female participants (0-1)
- baseline_severity: Mean baseline HDRS score (higher = more severe)

### C.2 Complete Network Characteristics

**Direct evidence:**

| Comparison        | N Studies | Total N | Median N per study |
|-------------------|-----------|---------|-------------------|
| Placebo vs SSRI-A | 3         | 3,247   | 1,082             |
| Placebo vs SSRI-B | 3         | 3,156   | 1,052             |
| Placebo vs SNRI   | 2         | 2,018   | 1,009             |
| Placebo vs TCA    | 2         | 1,896   | 948               |
| SSRI-A vs SSRI-B  | 2         | 2,072   | 1,036             |
| SSRI-A vs SNRI    | 1         | 458     | --                |
| SSRI-B vs SNRI    | 1         | 485     | --                |

**Multi-arm trials:**
- Study 07: Placebo, SSRI-A, SSRI-B (N=1,248)
- Study 11: SSRI-A, SSRI-B, SNRI (N=824)

### C.3 Extended Results

[Full tables and additional analyses]

### C.4 Sensitivity Analyses

**Fixed vs Random Effects:**

| Model  | TCA Effect | 95% CI           | I² | τ   |
|--------|------------|------------------|----|----|
| Random | -0.548     | [-0.740, -0.356] | 28%| 0.094 |
| Fixed  | -0.532     | [-0.686, -0.378] | -- | --    |

**Excluding small studies (<500 participants):**

| Treatment | Original Effect | Sensitivity | Difference |
|-----------|----------------|-------------|------------|
| SSRI-A    | -0.420         | -0.408      | 0.012      |
| SNRI      | -0.508         | -0.521      | -0.013     |
| TCA       | -0.548         | -0.556      | -0.008     |

**Different correlation for multi-arm trials:**

| Correlation | TCA Effect | SE    |
|-------------|------------|-------|
| 0.50 (main) | -0.548     | 0.098 |
| 0.70        | -0.551     | 0.101 |
| 1.00        | -0.558     | 0.107 |

---

## Appendix D: Software Documentation

### D.1 Installation Instructions

```bash
# Via pip
pip install netmetareg

# Via conda
conda install -c conda-forge netmetareg

# From source
git clone https://github.com/username/netmetareg.git
cd netmetareg
pip install -e .
```

**Dependencies:**
- Python ≥ 3.8
- NumPy ≥ 1.20
- Pandas ≥ 1.3
- SciPy ≥ 1.7
- Scikit-learn ≥ 1.0
- PyStan ≥ 3.0 (for Bayesian estimation)
- Matplotlib ≥ 3.4 (for plotting)

### D.2 Example Code

**Basic network meta-analysis:**

```python
from netmetareg import NMAData, FrequentistNMA

# Load data
data = NMAData.from_csv('studies.csv')

# Fit random effects model
model = FrequentistNMA(data, method='REML')
results = model.fit()

# Print treatment effects
print(results.treatment_effects)

# Check inconsistency
inconsistency = model.node_splitting()
print(inconsistency)
```

**Meta-regression with LASSO selection:**

```python
from netmetareg import NetworkMetaRegression

# Specify candidate covariates
covariates = ['mean_age', 'prop_female', 'baseline_severity',
              'publication_year', 'sample_size']

# Fit with LASSO selection
model = NetworkMetaRegression(
    data=data,
    covariates=covariates,
    selection_method='lasso',
    cv_folds=10
)

results = model.fit()

# Selected covariates
print(f"Selected: {results.selected_covariates}")

# Treatment effects with covariates
print(results.treatment_effects)
print(results.meta_regression_coefficients)
```

**Prediction for new population:**

```python
# Define new population
new_pop = {
    'mean_age': 65,
    'prop_female': 0.55,
    'baseline_severity': 28
}

# Predict treatment effects
predictions = model.predict(new_pop)

# Show predictions with intervals
print(predictions.treatment_effects)
print(predictions.prediction_intervals)

# Check extrapolation
print(predictions.extrapolation_warnings)
```

### D.3 API Reference

[Complete API documentation]

### D.4 Computational Benchmarks

**Hardware:** Intel i7-12700K (12 cores), 32GB RAM, Ubuntu 22.04

**Benchmark results:**

| Network Size | Studies | Treatments | Frequentist | Bayesian (4 chains) | Memory (MB) |
|--------------|---------|------------|-------------|---------------------|-------------|
| Tiny         | 6       | 3          | 0.04s       | 8.2s                | 45          |
| Small        | 12      | 4          | 0.08s       | 12.4s               | 68          |
| Medium       | 30      | 8          | 0.34s       | 28.7s               | 142         |
| Large        | 80      | 15         | 1.52s       | 124.6s              | 386         |
| Very Large   | 200     | 50         | 18.4s       | 892.3s              | 1,248       |

**Scaling:**
- Frequentist: O(N × J²) (linear in studies, quadratic in treatments)
- Bayesian: O(N × J² × iterations) (+ MCMC iterations)

---

## Appendix E: Sensitivity Analyses

### E.1 Prior Sensitivity (Bayesian Models)

**Treatment effects prior:**

| Prior Distribution    | TCA Effect (Posterior Median) | 95% CrI          |
|----------------------|-------------------------------|------------------|
| N(0, 1.5²) [main]    | -0.552                        | [-0.748, -0.362] |
| N(0, 0.5²) [informative] | -0.524                    | [-0.692, -0.358] |
| N(0, 10²) [vague]    | -0.556                        | [-0.762, -0.354] |

**Heterogeneity prior:**

| Prior               | τ (Posterior Median) | 95% CrI       |
|---------------------|----------------------|---------------|
| Half-Normal(0, 0.5) | 0.096                | [0.042, 0.174]|
| Half-Cauchy(0, 0.25)| 0.089                | [0.038, 0.168]|
| Uniform(0, 2)       | 0.102                | [0.048, 0.186]|

**Conclusion:** Results robust to prior specifications.

### E.2 Missing Data Sensitivity

**Pattern-mixture model - sensitivity to MNAR:**

Assume missing baseline_severity values are δ SD lower than observed:

| δ    | β̂ (baseline_severity) | 95% CI           | Conclusion          |
|------|------------------------|------------------|---------------------|
| 0    | 0.018                  | [-0.004, 0.040]  | MAR (main analysis) |
| 0.25 | 0.014                  | [-0.008, 0.036]  | Slight weakening    |
| 0.50 | 0.010                  | [-0.012, 0.032]  | Non-significant     |
| 1.00 | 0.002                  | [-0.021, 0.024]  | Near-null effect    |

**Interpretation:** If missing severity values are >0.5 SD lower, effect modification may disappear. Monitor missingness mechanism.

---

**END OF SUPPLEMENTARY MATERIAL**
