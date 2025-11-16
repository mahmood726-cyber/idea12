# Network Meta-Regression Tutorial

## Introduction

This tutorial provides a comprehensive guide to using the `netmetareg` package for network meta-analysis with meta-regression and inconsistency modeling.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Data Preparation](#data-preparation)
4. [Basic Network Meta-Analysis](#basic-network-meta-analysis)
5. [Meta-Regression](#meta-regression)
6. [Inconsistency Detection](#inconsistency-detection)
7. [Advanced Features](#advanced-features)
8. [Interpretation and Reporting](#interpretation-and-reporting)

---

## Installation

```bash
# Clone repository
git clone https://github.com/your-repo/netmetareg.git
cd netmetareg

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .
```

### Required Dependencies

- Python ≥ 3.8
- NumPy, SciPy, Pandas
- PyMC ≥ 5.0 (for Bayesian models)
- scikit-learn (for covariate selection)
- NetworkX (for network analysis)
- Matplotlib, Seaborn (for visualization)

---

## Quick Start

```python
from netmetareg import NetworkMetaRegression
from netmetareg.core.data_structure import NMAData, Study
import numpy as np

# Create study data
studies = [
    Study(
        study_id="Study1",
        treatments=["Placebo", "Drug A"],
        effects=np.array([-0.50]),
        se=np.array([0.15]),
        covariates={"age": 45, "severity": 25}
    ),
    # ... more studies
]

data = NMAData(studies=studies)

# Fit network meta-regression
nmr = NetworkMetaRegression(
    data=data,
    covariates=['age', 'severity'],
    interactions=False
)

results = nmr.fit(method='bayesian', draws=2000)

# View results
print(results.summary())
```

---

## Data Preparation

### Study Object

Each study is represented by a `Study` object:

```python
from netmetareg.core.data_structure import Study
import numpy as np

study = Study(
    study_id="Smith2020",
    treatments=["Placebo", "Treatment A", "Treatment B"],  # Multi-arm trial
    effects=np.array([-0.42, -0.55]),  # Relative to first arm (Placebo)
    se=np.array([0.15, 0.16]),
    n=np.array([100, 98, 95]),  # Sample sizes
    covariates={
        "mean_age": 45,
        "prop_female": 0.65,
        "baseline_severity": 28,
        "year": 2020
    }
)
```

### Data Formats

The package supports two input formats:

#### 1. Contrast-Based Format

```python
# DataFrame with one row per comparison
df = pd.DataFrame({
    'study': ['S1', 'S2', 'S3'],
    'treatment_1': ['Placebo', 'Placebo', 'Drug A'],
    'treatment_2': ['Drug A', 'Drug B', 'Drug B'],
    'effect': [-0.42, -0.38, 0.05],
    'se': [0.15, 0.14, 0.12],
    'n_1': [100, 105, 110],
    'n_2': [98, 103, 108],
    'mean_age': [45, 42, 40],
    'prop_female': [0.65, 0.58, 0.60]
})

data = NMAData.from_dataframe(
    df,
    study_col='study',
    effect_col='effect',
    se_col='se',
    covariate_cols=['mean_age', 'prop_female'],
    format='contrast'
)
```

#### 2. Arm-Based Format

```python
# DataFrame with one row per treatment arm
df = pd.DataFrame({
    'study': ['S1', 'S1', 'S2', 'S2'],
    'treatment': ['Placebo', 'Drug A', 'Placebo', 'Drug B'],
    'effect': [0, -0.42, 0, -0.38],
    'se': [0, 0.15, 0, 0.14],
    'n': [100, 98, 105, 103],
    'mean_age': [45, 45, 42, 42]
})

data = NMAData.from_dataframe(
    df,
    study_col='study',
    treatment_col='treatment',
    effect_col='effect',
    se_col='se',
    covariate_cols=['mean_age'],
    format='arm'
)
```

### Data Validation

```python
# Validate data quality
warnings = data.validate()
for w in warnings:
    print(w)

# Summary statistics
summary = data.summary()
print(summary)
```

---

## Basic Network Meta-Analysis

### Network Structure Analysis

```python
from netmetareg.core.network import TreatmentNetwork

network = TreatmentNetwork(data)

# Summary
print(network.summary())

# Check connectivity
is_connected = network.is_connected()
print(f"Network is connected: {is_connected}")

# Find loops (potential inconsistency)
triangles = network.find_triangles()
print(f"Number of triangular loops: {len(triangles)}")

# Visualize network
network.visualize_network(output_file='network.png')
```

### Bayesian NMA

```python
from netmetareg.models.bayesian_nma import BayesianNMA

# Initialize model
model = BayesianNMA(
    data=data,
    reference_treatment="Placebo",
    random_effects=True
)

# Fit model
results = model.fit(
    draws=2000,
    tune=1000,
    chains=4,
    target_accept=0.95
)

# Treatment effects
print(results.treatment_effects)

# Heterogeneity
print(f"Tau: {results.heterogeneity['mean']:.3f}")
print(f"I²: {results.heterogeneity['I_squared']:.1f}%")

# Convergence diagnostics
print(results.convergence_diagnostics)

# Visualization
results.plot_forest()
results.plot_trace()
```

### Frequentist NMA

```python
from netmetareg.models.frequentist_nma import FrequentistNMA

model = FrequentistNMA(
    data=data,
    reference_treatment="Placebo",
    random_effects=True,
    method='REML'
)

results = model.fit()

# Results
print(results.treatment_effects)
print(f"Tau²: {results.heterogeneity['tau_squared']:.4f}")
print(f"I²: {results.heterogeneity['I_squared']:.1f}%")

# Pairwise comparison
comparison = model.predict("Drug A", "Drug B")
print(comparison)
```

### Treatment Ranking

```python
# Bayesian: SUCRA scores
sucra = model.calculate_sucra()
print(sucra)

# Frequentist: P-scores
rankings = model.rank_treatments(method='P-score')
print(rankings)
```

---

## Meta-Regression

### Main Effects Model

```python
from netmetareg.regression.meta_regression import NetworkMetaRegression

nmr = NetworkMetaRegression(
    data=data,
    covariates=['mean_age', 'baseline_severity'],
    interactions=False,
    center_covariates=True,  # Hierarchical centering
    scale_covariates=False
)

results = nmr.fit(method='bayesian', draws=2000)

# Covariate effects
print(results.covariate_effects)

# Model comparison
from netmetareg.models.bayesian_nma import BayesianNMA
null_model = BayesianNMA(data)
null_results = null_model.fit(draws=2000)

comparison = nmr.compare_models(null_results)
print(f"ΔWAIC: {comparison['delta_waic']:.2f}")
print(f"Prefers meta-regression: {comparison['prefers_regression']}")
```

### Treatment-by-Covariate Interactions

```python
nmr = NetworkMetaRegression(
    data=data,
    covariates=['mean_age'],
    interactions=True,  # Enable interactions
    center_covariates=True
)

results = nmr.fit(method='bayesian', draws=2000)

# Interaction estimates
print(results.interactions)
```

### Prediction for New Populations

```python
# Define target population
new_population = {
    'mean_age': 55,
    'baseline_severity': 32
}

# Check for extrapolation
extrap_check = nmr.check_covariate_distribution(new_population)
print(extrap_check)

# Make predictions
predictions = nmr.predict(
    covariate_values=new_population,
    treatment_pair=("Drug A", "Placebo")
)

print(f"Predicted effect: {predictions['mean']:.3f}")
print(f"95% CrI: [{predictions['q025']:.3f}, {predictions['q975']:.3f}]")
```

---

## Inconsistency Detection

### Node-Splitting

```python
from netmetareg.inconsistency.node_splitting import NodeSplitting

ns = NodeSplitting(data, method='bayesian')

# Identify splittable nodes
splittable = ns.identify_splittable_nodes()
print(f"Splittable comparisons: {splittable}")

# Split specific comparison
result = ns.split_node("Drug A", "Drug B", draws=2000)

print(f"Direct effect: {result.direct_effect['mean']:.3f}")
print(f"Indirect effect: {result.indirect_effect['mean']:.3f}")
print(f"Inconsistency: {result.inconsistency['mean']:.3f}")
print(f"p-value: {result.p_value:.4f}")

# Visualize
ns.plot_node_split(result)

# Split all nodes
all_results = ns.split_all_nodes(draws=2000)
print(all_results[all_results['significant']])
```

### Design-by-Treatment Interaction

```python
from netmetareg.inconsistency.design_treatment import DesignTreatmentInteraction

dt = DesignTreatmentInteraction(data)

# Identify designs
designs = dt.identify_designs()
print(f"Study designs: {designs}")

# Fit model
results = dt.fit(draws=2000)

print(results.design_effects)
print(f"Probability of inconsistency: {results.inconsistency_test['prob_any_interaction']:.3f}")

# Visualize
dt.plot_interactions(results)
```

---

## Advanced Features

### Automated Covariate Selection (LASSO)

```python
from netmetareg.selection.lasso_selection import LassoSelection

selector = LassoSelection(
    data,
    candidate_covariates=['age', 'severity', 'year', 'duration'],
    method='lasso'
)

# Standard LASSO
results = selector.select(n_alphas=100, cv_folds=5)
print(f"Selected: {results.selected_covariates}")
print(f"Coefficients: {results.coefficients}")

# Stability selection (more robust)
stable_results = selector.stability_selection(
    n_bootstrap=100,
    threshold=0.6
)

# Visualize
selector.plot_regularization_path(results)
selector.plot_stability(stable_results)
```

### Multiple Imputation for Missing Covariates

```python
from netmetareg.utils.missing_data import MultipleImputation

imputer = MultipleImputation(
    data,
    n_imputations=20,
    max_iter=50
)

# Analyze missing pattern
missing_analysis = imputer.analyze_missing_pattern()
print(missing_analysis)

# Perform imputation
imputation_results = imputer.impute()

# Fit NMA on each imputed dataset
estimates = []
variances = []

for imputed_data in imputation_results.imputed_datasets:
    model = BayesianNMA(imputed_data)
    result = model.fit(draws=1000)

    # Extract estimates (simplified)
    d = result.treatment_effects['mean'].values
    var = result.treatment_effects['sd'].values ** 2

    estimates.append(d)
    variances.append(var)

# Pool using Rubin's rules
pooled, pooled_var, diagnostics = MultipleImputation.pool_estimates(
    estimates, variances
)

print(f"Pooled estimates: {pooled}")
print(f"Fraction of missing info: {diagnostics['fraction_missing_info']}")
```

### Class Effects Modeling

```python
# Define treatment classes
treatment_classes = {
    'SSRI': ['Drug A', 'Drug B'],
    'SNRI': ['Drug C', 'Drug D'],
    'TCA': ['Drug E']
}

# This feature allows treatments within a class to share
# parameters, reducing the effective number of parameters
# and improving precision when classes are plausible

# Implementation would extend BayesianNMA with class hierarchy
```

---

## Interpretation and Reporting

### Effect Size Interpretation

For different outcome types:

**Continuous outcomes (SMD):**
- Small: |d| ≈ 0.2
- Medium: |d| ≈ 0.5
- Large: |d| ≈ 0.8

**Binary outcomes (log OR):**
- Convert to OR: `OR = exp(d)`
- Interpret: OR > 1 favors treatment

### Heterogeneity Interpretation

**I² statistic:**
- < 25%: Low heterogeneity
- 25-50%: Moderate
- 50-75%: Substantial
- > 75%: Considerable

**Tau interpretation:**
- Rule of thumb: τ < 0.3 suggests low heterogeneity

### Inconsistency Interpretation

**Node-splitting p-value:**
- p < 0.05: Evidence of inconsistency
- Action: Investigate potential effect modifiers or biases

**Design-by-treatment interactions:**
- Significant interactions suggest inconsistency
- May indicate different patient populations or risk of bias

### Reporting Checklist

1. **Network description:**
   - Number of studies, treatments, patients
   - Network geometry (connected? triangles?)
   - Direct comparisons available

2. **Model specification:**
   - Random vs. fixed effects
   - Covariates included
   - Interaction terms
   - Prior distributions (Bayesian)

3. **Results:**
   - Treatment effects with 95% CI/CrI
   - Heterogeneity (τ², I²)
   - Inconsistency assessment
   - Treatment rankings (SUCRA/P-scores)

4. **Model diagnostics:**
   - Convergence (R̂, ESS for Bayesian)
   - Model fit (WAIC, AIC, BIC)
   - Sensitivity analyses

5. **Prediction:**
   - Target population characteristics
   - Extrapolation warnings
   - Uncertainty quantification

### Example Results Table

```python
# Generate publication-ready table
results_df = results.treatment_effects.copy()
results_df['effect_ci'] = results_df.apply(
    lambda row: f"{row['mean']:.2f} ({row['q025']:.2f}, {row['q975']:.2f})",
    axis=1
)
results_df = results_df[['treatment', 'effect_ci']]
print(results_df.to_latex(index=False))
```

---

## Best Practices

1. **Always check network connectivity** before fitting models

2. **Center covariates** at network mean for interpretability

3. **Test for inconsistency** using node-splitting or design-by-treatment

4. **Use multiple imputation** for missing covariates (≥20 imputations)

5. **Apply covariate selection** when you have many candidate covariates

6. **Report heterogeneity** and discuss clinical implications

7. **Check convergence** (R̂ < 1.01, ESS > 1000 for Bayesian)

8. **Sensitivity analyses:**
   - Fixed vs. random effects
   - Different priors (Bayesian)
   - Excluding outlier studies

9. **Assess transitivity** assumption using covariate distributions

10. **Document all modeling decisions** for transparency

---

## Troubleshooting

### Common Issues

**Problem:** Network is disconnected
- **Solution:** Check treatment names for typos; consider limiting to connected component

**Problem:** MCMC convergence issues
- **Solution:** Increase tune period; use stronger priors; check for identifiability issues

**Problem:** Large heterogeneity (I² > 75%)
- **Solution:** Investigate with meta-regression; consider subgroup analyses

**Problem:** Inconsistency detected
- **Solution:** Look for effect modifiers; check for systematic differences in designs

**Problem:** Wide credible intervals
- **Solution:** Expected with limited data; consider informative priors; report uncertainty honestly

---

## Further Reading

1. Dias et al. (2013). NICE DSU Technical Support Documents
2. Salanti et al. (2011). Graphical methods for network meta-analysis
3. Cochrane Handbook Chapter 11: Network meta-analysis
4. Jansen et al. (2011). Interpreting indirect treatment comparisons

---

## Support

For questions or issues:
- GitHub Issues: https://github.com/your-repo/netmetareg/issues
- Documentation: https://netmetareg.readthedocs.io
- Email: support@netmetareg.org
