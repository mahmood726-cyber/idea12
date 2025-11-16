"""
Multiple imputation for missing covariate data.

Handles missing study-level covariates using multiple imputation
with Rubin's rules for combining estimates.
"""

import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..core.data_structure import NMAData


@dataclass
class ImputationResults:
    """Results from multiple imputation.

    Attributes:
        imputed_datasets: List of imputed NMAData objects
        pooled_estimates: Pooled estimates using Rubin's rules
        within_variance: Within-imputation variance
        between_variance: Between-imputation variance
        total_variance: Total variance
        relative_increase: Relative increase in variance due to missing data
        fraction_missing_info: Fraction of missing information
    """
    imputed_datasets: List[NMAData]
    pooled_estimates: Optional[Dict] = None
    within_variance: Optional[float] = None
    between_variance: Optional[float] = None
    total_variance: Optional[float] = None
    relative_increase: Optional[float] = None
    fraction_missing_info: Optional[float] = None


class MultipleImputation:
    """Multiple imputation for missing covariate data.

    This class implements multiple imputation using chained equations (MICE)
    to handle missing study-level covariates in network meta-analysis.

    Steps:
    1. Create m imputed datasets
    2. Fit NMA model on each imputed dataset
    3. Pool estimates using Rubin's rules

    Rubin's rules for pooling:
        - Pooled estimate: θ_pooled = mean(θ_1, ..., θ_m)
        - Within variance: W = mean(Var(θ_1), ..., Var(θ_m))
        - Between variance: B = Var(θ_1, ..., θ_m)
        - Total variance: T = W + (1 + 1/m) * B
    """

    def __init__(self,
                 data: NMAData,
                 n_imputations: int = 20,
                 max_iter: int = 50,
                 random_state: int = 42):
        """Initialize multiple imputation.

        Args:
            data: NMAData object with missing covariates
            n_imputations: Number of imputed datasets to create
            max_iter: Maximum iterations for imputation algorithm
            random_state: Random seed for reproducibility
        """
        self.data = data
        self.n_imputations = n_imputations
        self.max_iter = max_iter
        self.random_state = random_state

    def impute(self) -> ImputationResults:
        """Perform multiple imputation.

        Returns:
            ImputationResults object with imputed datasets
        """
        # Get covariate matrix with missing values
        X, params = self.data.get_covariate_matrix(center=False, scale=False)

        # Check if there are any missing values
        if not np.any(np.isnan(X)):
            print("No missing data detected. Returning original dataset.")
            return ImputationResults(imputed_datasets=[self.data])

        # Create imputer
        imputer = IterativeImputer(
            estimator=BayesianRidge(),
            max_iter=self.max_iter,
            random_state=self.random_state,
            sample_posterior=True  # Important for MI
        )

        # Fit imputer on original data
        imputer.fit(X)

        # Generate multiple imputations
        imputed_datasets = []
        for m in range(self.n_imputations):
            # Impute
            X_imputed = imputer.transform(X)

            # Create new NMAData with imputed covariates
            imputed_data = self._create_imputed_data(X_imputed)
            imputed_datasets.append(imputed_data)

        results = ImputationResults(imputed_datasets=imputed_datasets)

        return results

    def _create_imputed_data(self, X_imputed: np.ndarray) -> NMAData:
        """Create NMAData object with imputed covariate values.

        Args:
            X_imputed: Imputed covariate matrix

        Returns:
            New NMAData object with imputed values
        """
        # Create deep copy of studies
        imputed_studies = []

        for i, study in enumerate(self.data.studies):
            # Copy study
            from copy import deepcopy
            new_study = deepcopy(study)

            # Update covariates with imputed values
            for j, cov_name in enumerate(self.data.covariate_names):
                new_study.covariates[cov_name] = float(X_imputed[i, j])

            imputed_studies.append(new_study)

        # Create new NMAData
        imputed_data = NMAData(
            studies=imputed_studies,
            reference_treatment=self.data.reference_treatment
        )

        return imputed_data

    @staticmethod
    def pool_estimates(estimates: List[np.ndarray],
                      variances: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Pool estimates from multiple imputed datasets using Rubin's rules.

        Args:
            estimates: List of parameter estimates from each imputation
            variances: List of variance estimates from each imputation

        Returns:
            Tuple of (pooled_estimates, pooled_variances, diagnostics)
        """
        m = len(estimates)

        if m == 0:
            raise ValueError("No estimates provided")

        # Convert to arrays
        estimates_array = np.array(estimates)  # Shape: (m, n_params)
        variances_array = np.array(variances)  # Shape: (m, n_params)

        # Pooled estimate (mean across imputations)
        theta_pooled = np.mean(estimates_array, axis=0)

        # Within-imputation variance (mean of variances)
        W = np.mean(variances_array, axis=0)

        # Between-imputation variance
        B = np.var(estimates_array, axis=0, ddof=1)

        # Total variance
        T = W + (1 + 1/m) * B

        # Relative increase in variance due to missingness
        r = (1 + 1/m) * B / W

        # Fraction of missing information
        lambda_mi = (1 + 1/m) * B / T

        diagnostics = {
            'within_variance': W,
            'between_variance': B,
            'total_variance': T,
            'relative_increase': r,
            'fraction_missing_info': lambda_mi,
            'n_imputations': m
        }

        return theta_pooled, T, diagnostics

    def analyze_missing_pattern(self) -> pd.DataFrame:
        """Analyze the pattern of missing data.

        Returns:
            DataFrame with missing data statistics
        """
        X, _ = self.data.get_covariate_matrix(center=False, scale=False)

        stats = []
        for j, cov_name in enumerate(self.data.covariate_names):
            cov_values = X[:, j]
            n_missing = np.sum(np.isnan(cov_values))
            pct_missing = 100 * n_missing / len(cov_values)

            if n_missing < len(cov_values):
                observed = cov_values[~np.isnan(cov_values)]
                mean_observed = np.mean(observed)
                sd_observed = np.std(observed)
            else:
                mean_observed = np.nan
                sd_observed = np.nan

            stats.append({
                'covariate': cov_name,
                'n_studies': len(cov_values),
                'n_missing': n_missing,
                'pct_missing': pct_missing,
                'mean_observed': mean_observed,
                'sd_observed': sd_observed
            })

        return pd.DataFrame(stats)

    def convergence_diagnostics(self, results: ImputationResults) -> pd.DataFrame:
        """Assess convergence of imputation algorithm.

        Args:
            results: ImputationResults object

        Returns:
            DataFrame with convergence diagnostics
        """
        if len(results.imputed_datasets) < 2:
            return pd.DataFrame()

        # For each covariate, check variance across imputations
        diagnostics = []

        for cov_name in self.data.covariate_names:
            # Get imputed values for this covariate across all imputations
            imputed_values = []
            for imputed_data in results.imputed_datasets:
                cov_idx = imputed_data.covariate_names.index(cov_name)
                X, _ = imputed_data.get_covariate_matrix(center=False, scale=False)
                imputed_values.append(X[:, cov_idx])

            imputed_values = np.array(imputed_values)  # Shape: (m, n_studies)

            # Calculate variance across imputations for each study
            within_study_var = np.var(imputed_values, axis=0)
            mean_within_study_var = np.mean(within_study_var)

            # Potential scale reduction factor (simplified)
            # Measures convergence of imputation
            psr = np.max(within_study_var) / (mean_within_study_var + 1e-10)

            diagnostics.append({
                'covariate': cov_name,
                'mean_within_study_var': mean_within_study_var,
                'max_within_study_var': np.max(within_study_var),
                'psr': psr,
                'converged': psr < 1.2
            })

        return pd.DataFrame(diagnostics)
