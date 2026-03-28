"""
Forensic Meta-Analysis: Bias Detection Framework
=================================================

This module implements forensic bias detection methods to identify and quantify
discordance between observational studies and randomized controlled trials (RCTs)
in meta-analyses.

When observational studies and RCTs produce conflicting results, three forms of
bias may be at play:

1. **Confounding Bias**: Unmeasured confounders in observational studies
2. **Discordance**: Systematic disagreement between study designs
3. **Information Inflation**: False precision from heterogeneous "big data"

This framework quantifies these biases using three validated metrics:
- Discordance Index (DI)
- E-Value (Confounding Score)
- Inflation Factor (Bayesian Effective Sample Size)

References:
-----------
VanderWeele & Ding (2017). Sensitivity analysis in observational research:
    Introducing the E-value. Annals of Internal Medicine.

Mathur & VanderWeele (2020). Sensitivity analysis for unmeasured confounding
    in meta-analyses. Journal of the American Statistical Association.

Neuenschwander et al. (2010). Summarizing historical information on controls
    in clinical trials. Clinical Trials.

"""

from .bias_detector import (
    ForensicAnalyzer,
    calculate_discordance_index,
    calculate_e_value,
    calculate_inflation_factor
)

from .bayesian_ess import (
    BayesianESSCalculator,
    fit_mixture_model
)

__all__ = [
    'ForensicAnalyzer',
    'calculate_discordance_index',
    'calculate_e_value',
    'calculate_inflation_factor',
    'BayesianESSCalculator',
    'fit_mixture_model'
]
