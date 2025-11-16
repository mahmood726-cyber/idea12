"""
Network Meta-Regression with Inconsistency Modeling

A comprehensive framework for network meta-analysis with meta-regression,
inconsistency detection, and novel methodological extensions.
"""

__version__ = "0.1.0"
__author__ = "Advanced Meta-Analysis Research Group"

from .core.network import TreatmentNetwork
from .core.data_structure import NMAData
from .regression.meta_regression import NetworkMetaRegression
from .inconsistency.node_splitting import NodeSplitting
from .inconsistency.design_treatment import DesignTreatmentInteraction
from .models.bayesian_nma import BayesianNMA
from .models.frequentist_nma import FrequentistNMA

__all__ = [
    'TreatmentNetwork',
    'NMAData',
    'NetworkMetaRegression',
    'NodeSplitting',
    'DesignTreatmentInteraction',
    'BayesianNMA',
    'FrequentistNMA',
]
