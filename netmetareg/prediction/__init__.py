"""
Advanced prediction methods for network meta-analysis.
"""

from .prediction_intervals import *

__all__ = [
    'PredictionIntervals',
    'compute_prediction_interval',
    'predict_new_study',
]
