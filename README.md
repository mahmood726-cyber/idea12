# Network Meta-Regression with Inconsistency Modeling

A Python framework for network meta-analysis with meta-regression, inconsistency detection, and methodological extensions.

## Overview

This package implements methods for network meta-analysis that support:

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

### Methodological Extensions
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
import numpy as np
from netmetareg import NMAData, NetworkMetaRegression, NodeSplitting
from netmetareg.core.data_structure import Study

# Build the network from study-level contrasts
studies = [
    Study(study_id="S1", treatments=["Placebo", "SSRI-A"],
          effects=np.array([-0.42]), se=np.array([0.15]), n=np.array([100, 98]),
          covariates={"mean_age": 45, "prop_female": 0.65, "year": 2015}),
    Study(study_id="S2", treatments=["Placebo", "SSRI-B"],
          effects=np.array([-0.38]), se=np.array([0.14]), n=np.array([105, 103]),
          covariates={"mean_age": 42, "prop_female": 0.58, "year": 2016}),
    Study(study_id="S3", treatments=["SSRI-A", "SSRI-B"],
          effects=np.array([0.05]), se=np.array([0.16]), n=np.array([90, 92]),
          covariates={"mean_age": 47, "prop_female": 0.60, "year": 2017}),
]
data = NMAData(studies=studies, reference_treatment="Placebo")

# Fit network meta-regression
model = NetworkMetaRegression(
    data=data,
    covariates=["mean_age", "prop_female", "year"],
)
results = model.fit(method="bayesian")

# Check inconsistency for a specific comparison via node-splitting
node_split = NodeSplitting(data)
inconsistency = node_split.split_node("Placebo", "SSRI-A")

# Predict for a new population
predictions = model.predict({"mean_age": 45, "prop_female": 0.6, "year": 2020})
```

See `examples/example_antidepressants.py` for a complete worked example.

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
