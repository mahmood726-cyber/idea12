"""
Automated covariate selection using LASSO and elastic net.

This module implements penalized regression for NMA to prevent
overfitting when many candidate covariates are available.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV, ElasticNetCV
from sklearn.preprocessing import StandardScaler
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from ..core.data_structure import NMAData


@dataclass
class SelectionResults:
    """Results from covariate selection.

    Attributes:
        selected_covariates: List of selected covariate names
        coefficients: Coefficient estimates for selected covariates
        cv_scores: Cross-validation scores
        optimal_alpha: Optimal regularization parameter
        path: Full regularization path
    """
    selected_covariates: List[str]
    coefficients: Dict[str, float]
    cv_scores: np.ndarray
    optimal_alpha: float
    path: Optional[pd.DataFrame] = None


class LassoSelection:
    """Automated covariate selection using LASSO/elastic net.

    LASSO (Least Absolute Shrinkage and Selection Operator) applies
    L1 penalty to regression coefficients, shrinking irrelevant
    coefficients to exactly zero.

    Elastic net combines L1 (LASSO) and L2 (ridge) penalties:
        penalty = alpha * (l1_ratio * ||beta||_1 + (1-l1_ratio)/2 * ||beta||_2^2)

    This prevents overfitting and performs automatic variable selection
    in network meta-regression.
    """

    def __init__(self,
                 data: NMAData,
                 candidate_covariates: Optional[List[str]] = None,
                 method: str = 'lasso',
                 l1_ratio: float = 1.0):
        """Initialize covariate selection.

        Args:
            data: NMAData object
            candidate_covariates: List of candidate covariates (default: all)
            method: Selection method ('lasso' or 'elastic_net')
            l1_ratio: Mixing parameter for elastic net (1.0 = LASSO, 0.0 = ridge)
        """
        self.data = data
        self.candidate_covariates = candidate_covariates or data.covariate_names
        self.method = method
        self.l1_ratio = l1_ratio

        # Validate covariates
        available = set(data.covariate_names)
        requested = set(self.candidate_covariates)
        missing = requested - available
        if missing:
            raise ValueError(f"Covariates not found: {missing}")

    def select(self,
              n_alphas: int = 100,
              cv_folds: int = 5,
              max_iter: int = 10000,
              tol: float = 1e-4) -> SelectionResults:
        """Perform covariate selection.

        Args:
            n_alphas: Number of alpha values to try
            cv_folds: Number of cross-validation folds
            max_iter: Maximum iterations for optimization
            tol: Convergence tolerance

        Returns:
            SelectionResults object
        """
        # Prepare data
        X, y, se = self._prepare_data()

        # Standardize covariates
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Weight by inverse variance
        weights = 1 / (se ** 2)

        # Fit LASSO or elastic net with cross-validation
        if self.method == 'lasso':
            model = LassoCV(
                n_alphas=n_alphas,
                cv=cv_folds,
                max_iter=max_iter,
                tol=tol,
                random_state=42
            )
        else:
            model = ElasticNetCV(
                l1_ratio=self.l1_ratio,
                n_alphas=n_alphas,
                cv=cv_folds,
                max_iter=max_iter,
                tol=tol,
                random_state=42
            )

        # Fit with sample weights
        model.fit(X_scaled, y, sample_weight=weights)

        # Extract results
        coefficients_scaled = model.coef_

        # Transform back to original scale
        coefficients_original = coefficients_scaled / scaler.scale_

        # Identify selected covariates (non-zero coefficients)
        selected_idx = np.abs(coefficients_original) > 1e-10
        selected_covariates = [self.candidate_covariates[i]
                              for i in range(len(self.candidate_covariates))
                              if selected_idx[i]]

        coefficients_dict = {
            self.candidate_covariates[i]: coefficients_original[i]
            for i in range(len(self.candidate_covariates))
            if selected_idx[i]
        }

        # Cross-validation scores
        cv_scores = model.mse_path_.mean(axis=1)

        # Create regularization path DataFrame
        if hasattr(model, 'alphas_'):
            path_data = []
            for i, cov_name in enumerate(self.candidate_covariates):
                for j, alpha in enumerate(model.alphas_):
                    if hasattr(model, 'path_'):
                        path_data.append({
                            'covariate': cov_name,
                            'alpha': alpha,
                            'coefficient': model.path_[i, j] if i < model.path_.shape[0] else 0
                        })
            path_df = pd.DataFrame(path_data) if path_data else None
        else:
            path_df = None

        results = SelectionResults(
            selected_covariates=selected_covariates,
            coefficients=coefficients_dict,
            cv_scores=cv_scores,
            optimal_alpha=model.alpha_,
            path=path_df
        )

        return results

    def _prepare_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for LASSO regression.

        Returns:
            Tuple of (X, y, se) arrays
        """
        y_list = []
        se_list = []
        X_list = []

        for study in self.data.studies:
            if study.effects is None or study.se is None:
                continue

            # Get covariate values for this study
            cov_values = []
            has_all_covs = True
            for cov_name in self.candidate_covariates:
                if cov_name in study.covariates:
                    cov_values.append(study.covariates[cov_name])
                else:
                    has_all_covs = False
                    break

            if not has_all_covs:
                continue

            # Add observations (one per contrast)
            for k in range(len(study.effects)):
                y_list.append(study.effects[k])
                se_list.append(study.se[k])
                X_list.append(cov_values)

        X = np.array(X_list)
        y = np.array(y_list)
        se = np.array(se_list)

        return X, y, se

    def stability_selection(self,
                           n_bootstrap: int = 100,
                           threshold: float = 0.6,
                           subsample_fraction: float = 0.8) -> SelectionResults:
        """Perform stability selection using bootstrap resampling.

        Stability selection runs LASSO on bootstrap samples and selects
        covariates that are selected frequently across samples.

        Args:
            n_bootstrap: Number of bootstrap samples
            threshold: Inclusion threshold (proportion of samples)
            subsample_fraction: Fraction of data to sample

        Returns:
            SelectionResults with stable covariates
        """
        X, y, se = self._prepare_data()
        n_obs = len(y)
        n_covs = X.shape[1]

        # Track selection frequency
        selection_freq = np.zeros(n_covs)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        weights = 1 / (se ** 2)

        for b in range(n_bootstrap):
            # Bootstrap sample
            n_sample = int(subsample_fraction * n_obs)
            idx = np.random.choice(n_obs, n_sample, replace=True)

            X_boot = X_scaled[idx]
            y_boot = y[idx]
            w_boot = weights[idx]

            # Fit LASSO
            if self.method == 'lasso':
                model = LassoCV(cv=5, random_state=b)
            else:
                model = ElasticNetCV(l1_ratio=self.l1_ratio, cv=5, random_state=b)

            model.fit(X_boot, y_boot, sample_weight=w_boot)

            # Track selected variables
            selected = np.abs(model.coef_) > 1e-10
            selection_freq += selected.astype(float)

        # Normalize to proportions
        selection_freq /= n_bootstrap

        # Select stable covariates
        stable_idx = selection_freq >= threshold
        selected_covariates = [self.candidate_covariates[i]
                              for i in range(n_covs)
                              if stable_idx[i]]

        # Get average coefficients for selected covariates
        # Refit on full data with selected covariates
        if len(selected_covariates) > 0:
            X_selected = X[:, stable_idx]
            X_selected_scaled = scaler.fit_transform(X_selected)

            if self.method == 'lasso':
                model = LassoCV(cv=5)
            else:
                model = ElasticNetCV(l1_ratio=self.l1_ratio, cv=5)

            model.fit(X_selected_scaled, y, sample_weight=weights)

            coefficients_scaled = model.coef_
            coefficients_original = coefficients_scaled / scaler.scale_

            coefficients_dict = {
                selected_covariates[i]: coefficients_original[i]
                for i in range(len(selected_covariates))
            }

            optimal_alpha = model.alpha_
            cv_scores = model.mse_path_.mean(axis=1)
        else:
            coefficients_dict = {}
            optimal_alpha = 0.0
            cv_scores = np.array([])

        # Create stability path
        path_data = []
        for i, cov_name in enumerate(self.candidate_covariates):
            path_data.append({
                'covariate': cov_name,
                'selection_frequency': selection_freq[i],
                'stable': selection_freq[i] >= threshold
            })
        path_df = pd.DataFrame(path_data)

        results = SelectionResults(
            selected_covariates=selected_covariates,
            coefficients=coefficients_dict,
            cv_scores=cv_scores,
            optimal_alpha=optimal_alpha,
            path=path_df
        )

        return results

    def plot_regularization_path(self, results: SelectionResults):
        """Plot regularization path showing coefficient shrinkage.

        Args:
            results: SelectionResults object
        """
        import matplotlib.pyplot as plt

        if results.path is None or results.path.empty:
            print("No regularization path available")
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        # Plot coefficient paths
        for cov_name in self.candidate_covariates:
            cov_path = results.path[results.path['covariate'] == cov_name]
            if not cov_path.empty:
                ax.plot(np.log(cov_path['alpha']),
                       cov_path['coefficient'],
                       label=cov_name,
                       linewidth=2)

        # Mark optimal alpha
        ax.axvline(np.log(results.optimal_alpha),
                  color='red',
                  linestyle='--',
                  label='Optimal α',
                  linewidth=2)

        ax.set_xlabel('log(α)', fontsize=12)
        ax.set_ylabel('Coefficient', fontsize=12)
        ax.set_title('LASSO Regularization Path', fontsize=14, fontweight='bold')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def plot_stability(self, results: SelectionResults):
        """Plot stability selection frequencies.

        Args:
            results: SelectionResults from stability_selection
        """
        import matplotlib.pyplot as plt

        if results.path is None or 'selection_frequency' not in results.path.columns:
            print("No stability selection data available")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        path = results.path.sort_values('selection_frequency', ascending=True)

        colors = ['green' if stable else 'gray' for stable in path['stable']]

        ax.barh(range(len(path)), path['selection_frequency'], color=colors)
        ax.set_yticks(range(len(path)))
        ax.set_yticklabels(path['covariate'])
        ax.set_xlabel('Selection Frequency', fontsize=12)
        ax.set_title('Stability Selection', fontsize=14, fontweight='bold')
        ax.axvline(0.6, color='red', linestyle='--', label='Threshold')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()
        return fig
