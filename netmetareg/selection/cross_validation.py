"""Cross-validation for NMA covariate selection.

Stub — implements the interface expected by the package.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CrossValidationNMA:
    """K-fold cross-validation for network meta-regression covariate selection."""
    n_folds: int = 5
    metric: str = "deviance"
    random_state: int | None = None

    def fit(self, effects, se, covariates, treatment_pairs):
        """Run cross-validation and return selected covariates."""
        # Placeholder — returns all covariates as selected
        if hasattr(covariates, 'columns'):
            return list(covariates.columns)
        return list(range(len(covariates[0]))) if covariates else []

    def score(self, effects, se, covariates, treatment_pairs):
        """Return cross-validation score for given covariates."""
        return {"metric": self.metric, "score": 0.0, "n_folds": self.n_folds}
