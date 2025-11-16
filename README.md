# Network Meta-Regression with Inconsistency Modeling

A comprehensive Python framework for advanced network meta-analysis with meta-regression, inconsistency detection, and novel methodological extensions.

## Overview

This package implements state-of-the-art methods for network meta-analysis that simultaneously:

- **Meta-regression**: Includes continuous/categorical effect modifiers with treatment-by-covariate interactions
- **Inconsistency modeling**: Detects and quantifies violations of transitivity using node-splitting and design-by-treatment interaction
- **Class effects**: Groups treatments into therapeutic classes with shared parameters
- **Prediction**: Generates predictions for new populations given covariate values

## Key Features

### Established Methods
- Contrast-based and arm-based network meta-analysis
- Meta-regression across treatment networks
- Node-splitting for inconsistency detection
- Design-by-treatment interaction models
- Class effects modeling
- Heterogeneity vs. inconsistency decomposition

### Novel Methodological Extensions
1. **Automated Covariate Selection**: LASSO/elastic net regularization with cross-validation
2. **Hierarchical Centering**: Network-average centering to improve interpretation and avoid extrapolation
3. **Multiple Imputation**: Handle missing study-level covariates with Rubin's rules
4. **Inconsistency Adjustment**: Down-weight inconsistent loops and bias adjustment models

## Theoretical Foundation

Based on established frameworks:
- Dias et al. (2013) - NICE Decision Support Unit technical support documents
- Jansen et al. (2012) - Network meta-regression methodology
- Cooper et al. (2009) - Mixed treatment comparisons
- Cochrane Handbook Chapter 11 - Network meta-analysis guidance

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from netmetareg import NetworkMetaRegression
from netmetareg.data import load_example_data

# Load example data
data = load_example_data('antidepressants')

# Fit network meta-regression
model = NetworkMetaRegression(
    data=data,
    covariates=['mean_age', 'prop_female', 'year'],
    inconsistency_method='node_splitting'
)

# Fit model
results = model.fit(method='bayesian')

# Check inconsistency
inconsistency = model.check_inconsistency()

# Predict for new population
new_pop = {'mean_age': 45, 'prop_female': 0.6, 'year': 2020}
predictions = model.predict(new_pop)
```

## Citation

If you use this package, please cite:

```
[Citation will be added upon publication]
```

## License

MIT License

## References

1. Dias, S., Welton, N. J., Sutton, A. J., & Ades, A. E. (2013). NICE DSU Technical Support Document 4: Inconsistency in Networks of Evidence Based on Randomised Controlled Trials.

2. Jansen, J. P., Schmid, C. H., & Salanti, G. (2012). Directed acyclic graphs can help understand bias in indirect and mixed treatment comparisons. Journal of Clinical Epidemiology, 65(7), 798-807.

3. Cooper, N. J., Sutton, A. J., Lu, G., & Khunti, K. (2009). Mixed comparison of stroke prevention treatments in individuals with nonrheumatic atrial fibrillation. Archives of Internal Medicine, 169(20), 1854-1860.
