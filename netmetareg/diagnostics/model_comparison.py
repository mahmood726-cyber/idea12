"""
Model comparison and selection tools for NMA.

Implements modern Bayesian model comparison using:
- Leave-One-Out Cross-Validation (LOO-CV)
- Pareto Smoothed Importance Sampling (PSIS)
- WAIC (Widely Applicable Information Criterion)
- Stacking weights for model averaging

References:
    Vehtari et al. (2017). Practical Bayesian model evaluation using LOO-CV and WAIC.
    Statistics and Computing, 27(5), 1413-1432.

    Yao et al. (2018). Using stacking to average Bayesian predictive distributions.
    Bayesian Analysis, 13(3), 917-1007.
"""

import numpy as np
import pandas as pd
import arviz as az
from typing import List, Dict, Optional, Union
import matplotlib.pyplot as plt
import seaborn as sns


class ModelComparison:
    """Comprehensive model comparison for Bayesian NMA models.

    Provides tools for:
    - LOO-CV comparison
    - PSIS diagnostics
    - Model averaging via stacking
    - Predictive performance assessment
    """

    def __init__(self, models: Dict[str, az.InferenceData]):
        """Initialize model comparison.

        Args:
            models: Dictionary mapping model names to InferenceData objects
        """
        self.models = models
        self.model_names = list(models.keys())
        self.comparison_results = None

    def compare_loo(self, ic: str = 'loo', scale: str = 'deviance') -> pd.DataFrame:
        """Compare models using LOO-CV or WAIC.

        Args:
            ic: Information criterion ('loo' or 'waic')
            scale: 'deviance' (default) or 'log'

        Returns:
            DataFrame with comparison results including:
            - Expected log predictive density (ELPD)
            - Standard error of ELPD
            - PSIS diagnostic (Pareto k values)
            - Effective sample size
        """
        # Compute LOO/WAIC for each model
        loo_results = {}
        for name, model_data in self.models.items():
            if ic == 'loo':
                loo_results[name] = az.loo(model_data, pointwise=True, scale=scale)
            elif ic == 'waic':
                loo_results[name] = az.waic(model_data, pointwise=True, scale=scale)
            else:
                raise ValueError(f"Unknown IC: {ic}. Use 'loo' or 'waic'")

        # Compare models
        comp = az.compare(loo_results, ic=ic, scale=scale)

        # Add interpretations
        comp['weight'] = np.exp(comp['elpd_diff'])
        comp['weight'] = comp['weight'] / comp['weight'].sum()

        self.comparison_results = comp
        return comp

    def check_psis_diagnostics(self, threshold: float = 0.7) -> Dict[str, Dict]:
        """Check PSIS diagnostics for all models.

        Pareto k diagnostic values:
        - k < 0.5: Good
        - 0.5 <= k < 0.7: OK
        - k >= 0.7: Bad (LOO-CV unreliable)

        Args:
            threshold: Threshold for flagging problematic observations

        Returns:
            Dictionary with diagnostics for each model
        """
        diagnostics = {}

        for name, model_data in self.models.items():
            loo = az.loo(model_data, pointwise=True)

            # Extract Pareto k values
            pareto_k = loo.pareto_k.values

            # Categorize
            n_good = np.sum(pareto_k < 0.5)
            n_ok = np.sum((pareto_k >= 0.5) & (pareto_k < 0.7))
            n_bad = np.sum(pareto_k >= 0.7)

            # Identify problematic observations
            bad_indices = np.where(pareto_k >= threshold)[0]

            diagnostics[name] = {
                'n_good': n_good,
                'n_ok': n_ok,
                'n_bad': n_bad,
                'max_k': np.max(pareto_k),
                'mean_k': np.mean(pareto_k),
                'bad_observations': bad_indices.tolist(),
                'reliable': n_bad == 0,
                'warnings': n_bad > 0
            }

            if n_bad > 0:
                print(f"\nWarning for model '{name}':")
                print(f"  {n_bad} observations with Pareto k >= {threshold}")
                print(f"  LOO-CV may be unreliable. Consider:")
                print(f"  1. Using K-fold cross-validation")
                print(f"  2. Checking for outliers")
                print(f"  3. Using a more flexible model")

        return diagnostics

    def compute_stacking_weights(self) -> pd.DataFrame:
        """Compute stacking weights for Bayesian model averaging.

        Stacking finds optimal linear combination of models for prediction.

        Returns:
            DataFrame with stacking weights for each model
        """
        # Get LOO pointwise log-likelihoods
        lpd_points = {}
        for name, model_data in self.models.items():
            loo = az.loo(model_data, pointwise=True)
            lpd_points[name] = loo.loo_i.values

        # Convert to matrix (models x observations)
        n_obs = len(next(iter(lpd_points.values())))
        lpd_matrix = np.array([lpd_points[name] for name in self.model_names])

        # Compute stacking weights via optimization
        # This is simplified; az.compare already does this
        comp = az.compare(self.models, ic='loo')

        weights_df = pd.DataFrame({
            'model': self.model_names,
            'stacking_weight': comp['weight'].values
        })

        return weights_df.sort_values('stacking_weight', ascending=False)

    def predictive_performance(self) -> pd.DataFrame:
        """Assess predictive performance of all models.

        Returns:
            DataFrame with:
            - ELPD (expected log pointwise predictive density)
            - RMSE (root mean squared error)
            - Coverage of 95% prediction intervals
        """
        performance = []

        for name, model_data in self.models.items():
            # LOO
            loo = az.loo(model_data, pointwise=True)
            elpd = loo.elpd_loo
            elpd_se = loo.se

            # Compute RMSE from posterior predictive
            if hasattr(model_data, 'posterior_predictive'):
                y_rep = model_data.posterior_predictive['y_like'].values
                y_obs = model_data.observed_data['y_like'].values

                # Mean prediction
                y_pred = y_rep.mean(axis=(0, 1))
                rmse = np.sqrt(np.mean((y_obs - y_pred)**2))

                # Coverage
                y_lower = np.percentile(y_rep, 2.5, axis=(0, 1))
                y_upper = np.percentile(y_rep, 97.5, axis=(0, 1))
                coverage = np.mean((y_obs >= y_lower) & (y_obs <= y_upper))
            else:
                rmse = np.nan
                coverage = np.nan

            performance.append({
                'model': name,
                'elpd_loo': elpd,
                'elpd_se': elpd_se,
                'rmse': rmse,
                'coverage_95': coverage
            })

        return pd.DataFrame(performance).sort_values('elpd_loo', ascending=False)

    def plot_comparison(self, figsize: tuple = (10, 6)):
        """Plot model comparison results.

        Args:
            figsize: Figure size (width, height)
        """
        if self.comparison_results is None:
            self.compare_loo()

        # Create comparison plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

        # Plot 1: ELPD comparison
        comp = self.comparison_results.reset_index()
        ax1.errorbar(
            x=comp['elpd_loo'],
            y=range(len(comp)),
            xerr=comp['se'],
            fmt='o',
            capsize=5
        )
        ax1.set_yticks(range(len(comp)))
        ax1.set_yticklabels(comp['index'])
        ax1.set_xlabel('ELPD (LOO-CV)')
        ax1.set_title('Model Comparison (higher is better)')
        ax1.grid(True, alpha=0.3)

        # Plot 2: Stacking weights
        weights = self.compute_stacking_weights()
        ax2.barh(range(len(weights)), weights['stacking_weight'])
        ax2.set_yticks(range(len(weights)))
        ax2.set_yticklabels(weights['model'])
        ax2.set_xlabel('Stacking Weight')
        ax2.set_title('Model Averaging Weights')
        ax2.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()
        return fig

    def plot_pareto_k(self, figsize: tuple = (12, 4)):
        """Plot Pareto k diagnostic values for all models.

        Args:
            figsize: Figure size
        """
        n_models = len(self.models)
        fig, axes = plt.subplots(1, n_models, figsize=figsize, squeeze=False)
        axes = axes.flatten()

        for idx, (name, model_data) in enumerate(self.models.items()):
            loo = az.loo(model_data, pointwise=True)
            pareto_k = loo.pareto_k.values

            ax = axes[idx]
            ax.scatter(range(len(pareto_k)), pareto_k, alpha=0.6)
            ax.axhline(y=0.5, color='orange', linestyle='--', label='k=0.5 (OK)')
            ax.axhline(y=0.7, color='red', linestyle='--', label='k=0.7 (Bad)')
            ax.set_xlabel('Observation')
            ax.set_ylabel('Pareto k')
            ax.set_title(f'{name}')
            ax.legend()
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig


def compare_models_loo(models: Dict[str, az.InferenceData],
                       ic: str = 'loo',
                       plot: bool = True) -> pd.DataFrame:
    """Convenience function to compare models using LOO-CV.

    Args:
        models: Dictionary of model name -> InferenceData
        ic: Information criterion ('loo' or 'waic')
        plot: Whether to create comparison plots

    Returns:
        Comparison DataFrame
    """
    comp = ModelComparison(models)
    results = comp.compare_loo(ic=ic)

    # Check PSIS diagnostics
    diagnostics = comp.check_psis_diagnostics()

    if plot:
        comp.plot_comparison()
        comp.plot_pareto_k()
        plt.show()

    return results


def model_averaging_predictions(models: Dict[str, az.InferenceData],
                                weights: Optional[Dict[str, float]] = None,
                                use_stacking: bool = True) -> np.ndarray:
    """Generate predictions using Bayesian model averaging.

    Args:
        models: Dictionary of models
        weights: Optional custom weights (if None, uses stacking)
        use_stacking: Use stacking weights if weights not provided

    Returns:
        Averaged predictions
    """
    if weights is None and use_stacking:
        comp = ModelComparison(models)
        weight_df = comp.compute_stacking_weights()
        weights = dict(zip(weight_df['model'], weight_df['stacking_weight']))
    elif weights is None:
        # Equal weights
        weights = {name: 1/len(models) for name in models.keys()}

    # Get predictions from each model
    predictions = {}
    for name, model_data in models.items():
        if hasattr(model_data, 'posterior_predictive'):
            y_rep = model_data.posterior_predictive['y_like'].values
            predictions[name] = y_rep.mean(axis=(0, 1))

    # Weighted average
    weighted_pred = np.zeros_like(next(iter(predictions.values())))
    for name, pred in predictions.items():
        weighted_pred += weights[name] * pred

    return weighted_pred


class CrossValidation:
    """K-fold cross-validation for network meta-analysis models.

    Useful when LOO-CV is unreliable (high Pareto k values).
    """

    def __init__(self, data, model_builder, k_folds: int = 5):
        """Initialize cross-validation.

        Args:
            data: NMAData object
            model_builder: Function that builds and fits model
            k_folds: Number of folds
        """
        self.data = data
        self.model_builder = model_builder
        self.k_folds = k_folds

    def run(self) -> Dict[str, float]:
        """Run K-fold cross-validation.

        Returns:
            Dictionary with CV metrics
        """
        n_studies = len(self.data.studies)
        fold_size = n_studies // self.k_folds

        cv_lpd = []
        cv_rmse = []

        for fold in range(self.k_folds):
            # Split data
            test_start = fold * fold_size
            test_end = test_start + fold_size if fold < self.k_folds - 1 else n_studies

            train_studies = (
                self.data.studies[:test_start] +
                self.data.studies[test_end:]
            )
            test_studies = self.data.studies[test_start:test_end]

            # Build model on training data
            train_data = type(self.data)(
                studies=train_studies,
                treatments=self.data.treatments,
                reference_treatment=self.data.reference_treatment
            )

            # Fit model
            model_result = self.model_builder(train_data)

            # Evaluate on test data
            # (Implementation depends on specific model interface)
            # For now, placeholder
            pass

        return {
            'cv_lpd': np.mean(cv_lpd),
            'cv_rmse': np.mean(cv_rmse),
            'cv_lpd_se': np.std(cv_lpd) / np.sqrt(self.k_folds)
        }
