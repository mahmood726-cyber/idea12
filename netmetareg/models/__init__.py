"""Statistical models for network meta-analysis."""

from .bayesian_nma import BayesianNMA
from .frequentist_nma import FrequentistNMA

__all__ = ['BayesianNMA', 'FrequentistNMA']
