"""
Network Meta-Regression with Inconsistency Modeling

A comprehensive framework for network meta-analysis with meta-regression,
inconsistency detection, and novel methodological extensions.
"""

from importlib import import_module

__version__ = "0.1.0"
__author__ = "Advanced Meta-Analysis Research Group"

__all__ = [
    'TreatmentNetwork',
    'NMAData',
    'NetworkMetaRegression',
    'NodeSplitting',
    'DesignTreatmentInteraction',
    'BayesianNMA',
    'FrequentistNMA',
    'LassoSelection',
    'MultipleImputation',
    'NMASimulator',
    'SimulationParameters',
]

_EXPORTS = {
    'TreatmentNetwork': ('.core.network', 'TreatmentNetwork'),
    'NMAData': ('.core.data_structure', 'NMAData'),
    'NetworkMetaRegression': ('.regression.meta_regression', 'NetworkMetaRegression'),
    'NodeSplitting': ('.inconsistency.node_splitting', 'NodeSplitting'),
    'DesignTreatmentInteraction': ('.inconsistency.design_treatment', 'DesignTreatmentInteraction'),
    'BayesianNMA': ('.models.bayesian_nma', 'BayesianNMA'),
    'FrequentistNMA': ('.models.frequentist_nma', 'FrequentistNMA'),
    'LassoSelection': ('.selection.lasso_selection', 'LassoSelection'),
    'MultipleImputation': ('.utils.missing_data', 'MultipleImputation'),
    'NMASimulator': ('.utils.simulation', 'NMASimulator'),
    'SimulationParameters': ('.utils.simulation', 'SimulationParameters'),
}


def __getattr__(name):
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value
