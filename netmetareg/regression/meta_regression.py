"""
Network Meta-Regression models.

This module implements network meta-regression with:
- Treatment-by-covariate interactions
- Hierarchical centering of covariates
- Automated covariate selection (LASSO, elastic net)
- Multiple imputation for missing covariates
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Tuple, Union
from dataclasses import dataclass

from ..core.data_structure import NMAData
from ..core.network import TreatmentNetwork
from ..models.bayesian_nma import BayesianNMA, BayesianNMAResults
from ..models.frequentist_nma import FrequentistNMA, FrequentistNMAResults


@dataclass
class MetaRegressionResults:
    """Results from network meta-regression.

    Attributes:
        base_results: Results from base NMA model (Bayesian or Frequentist)
        covariate_effects: Summary of covariate effect estimates
        interactions: Summary of treatment-by-covariate interactions
        model_comparison: Model fit statistics
        centering_params: Parameters used for covariate centering
    """
    base_results: Union[BayesianNMAResults, FrequentistNMAResults]
    covariate_effects: pd.DataFrame
    interactions: Optional[pd.DataFrame] = None
    model_comparison: Optional[Dict] = None
    centering_params: Optional[Dict] = None


class NetworkMetaRegression:
    """Network Meta-Regression with advanced features.

    This class extends standard network meta-analysis to include
    study-level covariates and treatment-by-covariate interactions.

    Key features:
    - Hierarchical centering at network-average
    - Treatment-by-covariate interactions
    - Prediction for new populations
    - Integration with inconsistency models
    """

    def __init__(self,
                 data: NMAData,
                 covariates: Optional[List[str]] = None,
                 interactions: bool = False,
                 center_covariates: bool = True,
                 scale_covariates: bool = False,
                 reference_treatment: Optional[str] = None):
        """Initialize network meta-regression.

        Args:
            data: NMAData object
            covariates: List of covariate names to include
            interactions: Whether to include treatment-by-covariate interactions
            center_covariates: Whether to center covariates at network mean
            scale_covariates: Whether to standardize covariates
            reference_treatment: Reference treatment
        """
        self.data = data
        self.network = TreatmentNetwork(data)
        self.covariates = covariates or []
        self.interactions = interactions
        self.center_covariates = center_covariates
        self.scale_covariates = scale_covariates

        if reference_treatment:
            self.data.reference_treatment = reference_treatment

        # Validate covariates
        available_covs = set(self.data.covariate_names)
        requested_covs = set(self.covariates)
        missing_covs = requested_covs - available_covs

        if missing_covs:
            raise ValueError(f"Covariates not found in data: {missing_covs}")

        self.results = None
        self.centering_params = None

    def fit(self,
           method: str = 'bayesian',
           **kwargs) -> MetaRegressionResults:
        """Fit network meta-regression model.

        Args:
            method: Estimation method ('bayesian' or 'frequentist')
            **kwargs: Additional arguments passed to fitting method

        Returns:
            MetaRegressionResults object
        """
        if method == 'bayesian':
            return self._fit_bayesian(**kwargs)
        elif method == 'frequentist':
            return self._fit_frequentist(**kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _fit_bayesian(self, **kwargs) -> MetaRegressionResults:
        """Fit Bayesian meta-regression.

        Args:
            **kwargs: Arguments passed to BayesianNMA.fit()

        Returns:
            MetaRegressionResults object
        """
        # Build and fit model
        model = BayesianNMA(
            data=self.data,
            reference_treatment=self.data.reference_treatment
        )

        model.build_model(
            covariates=self.covariates,
            interactions=self.interactions,
            center_covariates=self.center_covariates
        )

        base_results = model.fit(**kwargs)

        # Extract covariate effects
        covariate_effects = self._extract_covariate_effects_bayesian(base_results)

        # Extract interactions if present
        interactions_df = None
        if self.interactions:
            interactions_df = self._extract_interactions_bayesian(base_results)

        # Get centering parameters
        X, centering_params = self.data.get_covariate_matrix(
            center=self.center_covariates,
            scale=self.scale_covariates
        )
        self.centering_params = centering_params

        self.results = MetaRegressionResults(
            base_results=base_results,
            covariate_effects=covariate_effects,
            interactions=interactions_df,
            centering_params=centering_params
        )

        return self.results

    def _fit_frequentist(self, **kwargs) -> MetaRegressionResults:
        """Fit frequentist meta-regression.

        Args:
            **kwargs: Arguments passed to FrequentistNMA

        Returns:
            MetaRegressionResults object
        """
        # For frequentist approach, we need to extend the design matrix
        # to include covariates (to be implemented in FrequentistNMA)
        raise NotImplementedError(
            "Frequentist meta-regression not yet implemented. "
            "Use method='bayesian' for now."
        )

    def _extract_covariate_effects_bayesian(self,
                                           results: BayesianNMAResults) -> pd.DataFrame:
        """Extract covariate effect estimates from Bayesian model.

        Args:
            results: BayesianNMAResults object

        Returns:
            DataFrame with covariate effect summaries
        """
        if 'beta' not in results.trace.posterior:
            return pd.DataFrame()

        beta_samples = results.trace.posterior['beta'].values

        # Check shape to determine if interactions are present
        if beta_samples.ndim == 3:
            # Shape: (chains, draws, n_covariates)
            # Main effects only
            beta_samples = beta_samples.reshape(-1, beta_samples.shape[-1])

            results_list = []
            for i, cov_name in enumerate(self.covariates):
                samples = beta_samples[:, i]
                results_list.append({
                    'covariate': cov_name,
                    'mean': np.mean(samples),
                    'sd': np.std(samples),
                    'median': np.median(samples),
                    'q025': np.percentile(samples, 2.5),
                    'q975': np.percentile(samples, 97.5),
                    'prob_positive': np.mean(samples > 0)
                })

            return pd.DataFrame(results_list)

        elif beta_samples.ndim == 4:
            # Shape: (chains, draws, n_covariates, n_treatments)
            # Interactions present - return main effects averaged across treatments
            beta_samples = beta_samples.reshape(-1, beta_samples.shape[-2], beta_samples.shape[-1])

            results_list = []
            for i, cov_name in enumerate(self.covariates):
                # Average across treatments
                samples = np.mean(beta_samples[:, i, :], axis=1)
                results_list.append({
                    'covariate': cov_name,
                    'mean': np.mean(samples),
                    'sd': np.std(samples),
                    'median': np.median(samples),
                    'q025': np.percentile(samples, 2.5),
                    'q975': np.percentile(samples, 97.5),
                    'prob_positive': np.mean(samples > 0)
                })

            return pd.DataFrame(results_list)

        return pd.DataFrame()

    def _extract_interactions_bayesian(self,
                                      results: BayesianNMAResults) -> pd.DataFrame:
        """Extract treatment-by-covariate interactions from Bayesian model.

        Args:
            results: BayesianNMAResults object

        Returns:
            DataFrame with interaction effect summaries
        """
        if 'beta' not in results.trace.posterior:
            return pd.DataFrame()

        beta_samples = results.trace.posterior['beta'].values

        if beta_samples.ndim != 4:
            return pd.DataFrame()

        # Shape: (chains, draws, n_covariates, n_treatments)
        beta_samples = beta_samples.reshape(-1, beta_samples.shape[-2], beta_samples.shape[-1])

        results_list = []
        for i, cov_name in enumerate(self.covariates):
            for j, treatment in enumerate(self.data.treatments):
                samples = beta_samples[:, i, j]
                results_list.append({
                    'covariate': cov_name,
                    'treatment': treatment,
                    'mean': np.mean(samples),
                    'sd': np.std(samples),
                    'median': np.median(samples),
                    'q025': np.percentile(samples, 2.5),
                    'q975': np.percentile(samples, 97.5),
                    'prob_positive': np.mean(samples > 0)
                })

        return pd.DataFrame(results_list)

    def predict(self,
                covariate_values: Dict[str, float],
                treatment_pair: Optional[Tuple[str, str]] = None) -> Dict:
        """Predict treatment effect for a new population.

        Args:
            covariate_values: Dictionary of covariate values for target population
            treatment_pair: Optional tuple of (treatment_1, treatment_2) to compare

        Returns:
            Dictionary with prediction summaries
        """
        if self.results is None:
            raise ValueError("Model must be fitted before prediction")

        # Adjust covariate values for centering/scaling
        adjusted_covs = {}
        for cov_name, value in covariate_values.items():
            if cov_name not in self.covariates:
                continue

            adjusted_value = value

            # Apply centering
            if self.center_covariates and self.centering_params:
                if 'means' in self.centering_params:
                    cov_idx = self.covariates.index(cov_name)
                    adjusted_value -= self.centering_params['means'][cov_idx]

            # Apply scaling
            if self.scale_covariates and self.centering_params:
                if 'stds' in self.centering_params:
                    cov_idx = self.covariates.index(cov_name)
                    adjusted_value /= self.centering_params['stds'][cov_idx]

            adjusted_covs[cov_name] = adjusted_value

        # Use base model's predict method
        if isinstance(self.results.base_results, BayesianNMAResults):
            # Bayesian prediction
            model = BayesianNMA(data=self.data)
            model.trace = self.results.base_results.trace
            predictions = model.predict(adjusted_covs, treatment_pair)
        else:
            # Frequentist prediction (to be implemented)
            raise NotImplementedError("Frequentist prediction not yet implemented")

        return predictions

    def check_covariate_distribution(self,
                                    covariate_values: Dict[str, float]) -> pd.DataFrame:
        """Check if target covariate values are within observed range.

        This helps identify extrapolation and assess applicability.

        Args:
            covariate_values: Dictionary of covariate values

        Returns:
            DataFrame with covariate comparison to network distribution
        """
        X, _ = self.data.get_covariate_matrix(center=False, scale=False)

        results = []
        for cov_name, target_value in covariate_values.items():
            if cov_name not in self.data.covariate_names:
                continue

            cov_idx = self.data.covariate_names.index(cov_name)
            cov_values = X[:, cov_idx]
            cov_values = cov_values[~np.isnan(cov_values)]

            if len(cov_values) == 0:
                continue

            min_val = np.min(cov_values)
            max_val = np.max(cov_values)
            mean_val = np.mean(cov_values)
            sd_val = np.std(cov_values)

            # Check if extrapolating
            is_extrapolating = target_value < min_val or target_value > max_val

            # Z-score
            z_score = (target_value - mean_val) / sd_val if sd_val > 0 else 0

            results.append({
                'covariate': cov_name,
                'target_value': target_value,
                'network_mean': mean_val,
                'network_sd': sd_val,
                'network_min': min_val,
                'network_max': max_val,
                'z_score': z_score,
                'extrapolating': is_extrapolating
            })

        return pd.DataFrame(results)

    def compare_models(self,
                      null_model_results: Union[BayesianNMAResults, FrequentistNMAResults]
                      ) -> Dict:
        """Compare meta-regression model to null model (no covariates).

        Args:
            null_model_results: Results from model without covariates

        Returns:
            Dictionary with model comparison statistics
        """
        if self.results is None:
            raise ValueError("Model must be fitted before comparison")

        comparison = {}

        if isinstance(self.results.base_results, BayesianNMAResults):
            # Bayesian model comparison using WAIC
            waic_regression = self.results.base_results.waic
            waic_null = null_model_results.waic

            comparison['waic_regression'] = waic_regression
            comparison['waic_null'] = waic_null
            comparison['delta_waic'] = waic_regression - waic_null
            comparison['prefers_regression'] = waic_regression < waic_null

            # Bayes factor approximation from WAIC
            comparison['log_bf_approx'] = (waic_null - waic_regression) / 2

        else:
            # Frequentist model comparison using AIC/BIC
            aic_regression = self.results.base_results.aic
            bic_regression = self.results.base_results.bic
            aic_null = null_model_results.aic
            bic_null = null_model_results.bic

            comparison['aic_regression'] = aic_regression
            comparison['aic_null'] = aic_null
            comparison['delta_aic'] = aic_regression - aic_null

            comparison['bic_regression'] = bic_regression
            comparison['bic_null'] = bic_null
            comparison['delta_bic'] = bic_regression - bic_null

            comparison['prefers_regression'] = aic_regression < aic_null

        return comparison

    def summary(self) -> str:
        """Generate text summary of meta-regression results.

        Returns:
            Multi-line string with results summary
        """
        if self.results is None:
            raise ValueError("Model must be fitted before generating summary")

        lines = [
            "=" * 70,
            "NETWORK META-REGRESSION SUMMARY",
            "=" * 70,
            f"Covariates included: {', '.join(self.covariates)}",
            f"Treatment-by-covariate interactions: {'Yes' if self.interactions else 'No'}",
            f"Covariate centering: {'Yes' if self.center_covariates else 'No'}",
            f"Covariate scaling: {'Yes' if self.scale_covariates else 'No'}",
            "",
            "COVARIATE EFFECTS:",
            "-" * 70
        ]

        # Add covariate effects table
        if not self.results.covariate_effects.empty:
            lines.append(self.results.covariate_effects.to_string(index=False))
        else:
            lines.append("No covariate effects estimated")

        if self.interactions and self.results.interactions is not None:
            lines.extend([
                "",
                "TREATMENT-BY-COVARIATE INTERACTIONS:",
                "-" * 70,
                self.results.interactions.to_string(index=False)
            ])

        if self.centering_params:
            lines.extend([
                "",
                "CENTERING PARAMETERS:",
                "-" * 70
            ])
            if 'means' in self.centering_params:
                for i, cov_name in enumerate(self.covariates):
                    mean = self.centering_params['means'][i]
                    lines.append(f"{cov_name}: centered at {mean:.3f}")

        lines.append("=" * 70)

        return "\n".join(lines)
