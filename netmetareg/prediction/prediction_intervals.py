"""
Prediction intervals for network meta-analysis.

Implements prediction intervals that account for:
- Between-study heterogeneity
- Parameter uncertainty
- Future study variability

References:
    Riley et al. (2011). Interpretation of random effects meta-analyses.
    BMJ, 342, d549.

    Higgins et al. (2009). A re-evaluation of random-effects meta-analysis.
    Journal of the Royal Statistical Society: Series A.
"""

import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional, Dict, Tuple
import arviz as az


class PredictionIntervals:
    """Compute prediction intervals for network meta-analysis.

    Prediction intervals estimate the range of treatment effects expected
    in a future study, accounting for:
    1. Uncertainty in the pooled estimate
    2. Between-study heterogeneity

    PI = pooled_estimate ± t_critical * sqrt(SE² + τ²)
    """

    def __init__(self,
                 treatment_effects: np.ndarray,
                 se: np.ndarray,
                 tau: float,
                 df: Optional[int] = None):
        """Initialize prediction interval computation.

        Args:
            treatment_effects: Point estimates for treatments
            se: Standard errors of estimates
            tau: Between-study heterogeneity (SD)
            df: Degrees of freedom for t-distribution (if None, uses normal)
        """
        self.effects = treatment_effects
        self.se = se
        self.tau = tau
        self.df = df

    def compute_interval(self,
                        level: float = 0.95,
                        method: str = 'standard') -> pd.DataFrame:
        """Compute prediction intervals.

        Args:
            level: Coverage level (default: 0.95)
            method: Method ('standard', 'hartung-knapp')

        Returns:
            DataFrame with prediction intervals
        """
        if method == 'standard':
            return self._standard_prediction_interval(level)
        elif method == 'hartung-knapp':
            return self._hartung_knapp_interval(level)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _standard_prediction_interval(self, level: float) -> pd.DataFrame:
        """Standard prediction interval.

        PI = estimate ± t * sqrt(SE² + τ²)
        """
        # Prediction variance combines estimation uncertainty and heterogeneity
        pred_var = self.se**2 + self.tau**2
        pred_se = np.sqrt(pred_var)

        # Critical value
        alpha = 1 - level
        if self.df is not None:
            t_crit = stats.t.ppf(1 - alpha/2, self.df)
        else:
            t_crit = stats.norm.ppf(1 - alpha/2)

        # Intervals
        lower = self.effects - t_crit * pred_se
        upper = self.effects + t_crit * pred_se

        # Also compute confidence intervals for comparison
        ci_lower = self.effects - t_crit * self.se
        ci_upper = self.effects + t_crit * self.se

        return pd.DataFrame({
            'estimate': self.effects,
            'se': self.se,
            'tau': self.tau,
            'pred_se': pred_se,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'pi_lower': lower,
            'pi_upper': upper,
            'pi_width': upper - lower,
            'ci_width': ci_upper - ci_lower
        })

    def _hartung_knapp_interval(self, level: float) -> pd.DataFrame:
        """Hartung-Knapp adjustment for prediction intervals.

        More conservative when heterogeneity is present.
        """
        # This requires study-level data, simplified version here
        # In practice, would refit with robust variance
        return self._standard_prediction_interval(level)

    def plot_intervals(self,
                      treatment_names: Optional[list] = None,
                      figsize: tuple = (10, 8)):
        """Plot confidence and prediction intervals together.

        Args:
            treatment_names: Names for treatments
            figsize: Figure size
        """
        import matplotlib.pyplot as plt

        results = self.compute_interval()

        if treatment_names is None:
            treatment_names = [f"T{i}" for i in range(len(self.effects))]

        fig, ax = plt.subplots(figsize=figsize)

        y_pos = np.arange(len(treatment_names))

        # Plot prediction intervals (wider)
        ax.barh(y_pos, results['pi_width'], left=results['pi_lower'],
               height=0.5, alpha=0.3, color='lightblue',
               label='95% Prediction Interval')

        # Plot confidence intervals (narrower)
        ax.barh(y_pos, results['ci_width'], left=results['ci_lower'],
               height=0.3, alpha=0.6, color='blue',
               label='95% Confidence Interval')

        # Plot point estimates
        ax.scatter(results['estimate'], y_pos, color='black', s=100, zorder=5)

        # Reference line
        ax.axvline(x=0, color='red', linestyle='--', alpha=0.5)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(treatment_names)
        ax.set_xlabel('Effect Size')
        ax.set_title('Confidence and Prediction Intervals')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()
        return fig


class BayesianPredictionIntervals:
    """Compute Bayesian prediction intervals from posterior samples.

    Uses full posterior distribution to generate predictions for future studies.
    """

    def __init__(self, trace: az.InferenceData, tau_var: str = 'tau'):
        """Initialize Bayesian prediction intervals.

        Args:
            trace: ArviZ InferenceData with posterior samples
            tau_var: Name of heterogeneity parameter in trace
        """
        self.trace = trace
        self.tau_var = tau_var

    def predict_future_study(self,
                            treatment_idx: int,
                            n_samples: int = 4000) -> np.ndarray:
        """Generate predictive distribution for a future study.

        Args:
            treatment_idx: Index of treatment
            n_samples: Number of samples to draw

        Returns:
            Samples from predictive distribution
        """
        # Extract posterior samples
        d_samples = self.trace.posterior['d_fixed'].values
        tau_samples = self.trace.posterior[self.tau_var].values

        # Flatten chains and draws
        d_flat = d_samples.reshape(-1, d_samples.shape[-1])
        tau_flat = tau_samples.flatten()

        # Sample from predictive distribution
        # theta_new ~ N(d[j], tau^2)
        n_posterior = len(d_flat)
        sample_idx = np.random.choice(n_posterior, size=n_samples)

        predictions = np.random.normal(
            loc=d_flat[sample_idx, treatment_idx],
            scale=tau_flat[sample_idx]
        )

        return predictions

    def compute_prediction_intervals(self,
                                    level: float = 0.95) -> pd.DataFrame:
        """Compute prediction intervals for all treatments.

        Args:
            level: Coverage level

        Returns:
            DataFrame with prediction intervals
        """
        # Get treatment effects
        d_summary = az.summary(self.trace, var_names=['d_fixed'])

        n_treatments = len(d_summary)
        results = []

        for i in range(n_treatments):
            # Generate predictions
            pred_samples = self.predict_future_study(i)

            # Compute quantiles
            lower_q = (1 - level) / 2
            upper_q = 1 - lower_q

            pi_lower = np.percentile(pred_samples, lower_q * 100)
            pi_upper = np.percentile(pred_samples, upper_q * 100)

            results.append({
                'treatment': i,
                'mean': d_summary.iloc[i]['mean'],
                'sd': d_summary.iloc[i]['sd'],
                'ci_lower': d_summary.iloc[i]['hdi_3%'],
                'ci_upper': d_summary.iloc[i]['hdi_97%'],
                'pi_lower': pi_lower,
                'pi_upper': pi_upper,
                'pi_width': pi_upper - pi_lower
            })

        return pd.DataFrame(results)

    def plot_predictive_distribution(self,
                                    treatment_idx: int,
                                    treatment_name: Optional[str] = None,
                                    figsize: tuple = (10, 6)):
        """Plot predictive distribution for a specific treatment.

        Args:
            treatment_idx: Treatment index
            treatment_name: Treatment name for title
            figsize: Figure size
        """
        import matplotlib.pyplot as plt

        # Generate predictions
        predictions = self.predict_future_study(treatment_idx)

        # Get posterior for comparison
        d_samples = self.trace.posterior['d_fixed'].values
        d_flat = d_samples.reshape(-1, d_samples.shape[-1])

        fig, ax = plt.subplots(figsize=figsize)

        # Plot predictive distribution
        ax.hist(predictions, bins=50, density=True, alpha=0.5,
               label='Predictive (future study)', color='lightblue', edgecolor='black')

        # Plot posterior
        ax.hist(d_flat[:, treatment_idx], bins=50, density=True, alpha=0.5,
               label='Posterior (pooled estimate)', color='orange', edgecolor='black')

        # Add credible and prediction intervals
        ci_lower, ci_upper = np.percentile(d_flat[:, treatment_idx], [2.5, 97.5])
        pi_lower, pi_upper = np.percentile(predictions, [2.5, 97.5])

        ax.axvline(ci_lower, color='orange', linestyle='--', alpha=0.7, linewidth=2)
        ax.axvline(ci_upper, color='orange', linestyle='--', alpha=0.7, linewidth=2)
        ax.axvline(pi_lower, color='blue', linestyle='--', alpha=0.7, linewidth=2)
        ax.axvline(pi_upper, color='blue', linestyle='--', alpha=0.7, linewidth=2)

        if treatment_name:
            title = f'Predictive Distribution for {treatment_name}'
        else:
            title = f'Predictive Distribution for Treatment {treatment_idx}'

        ax.set_xlabel('Effect Size')
        ax.set_ylabel('Density')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig


def compute_prediction_interval(pooled_estimate: float,
                                se: float,
                                tau: float,
                                df: Optional[int] = None,
                                level: float = 0.95) -> Tuple[float, float]:
    """Convenience function to compute prediction interval.

    Args:
        pooled_estimate: Pooled treatment effect
        se: Standard error of pooled estimate
        tau: Between-study heterogeneity
        df: Degrees of freedom (None for normal approximation)
        level: Coverage level

    Returns:
        Tuple of (lower, upper) bounds
    """
    pred_se = np.sqrt(se**2 + tau**2)

    alpha = 1 - level
    if df is not None:
        t_crit = stats.t.ppf(1 - alpha/2, df)
    else:
        t_crit = stats.norm.ppf(1 - alpha/2)

    lower = pooled_estimate - t_crit * pred_se
    upper = pooled_estimate + t_crit * pred_se

    return lower, upper


def predict_new_study(posterior_samples: np.ndarray,
                     tau_samples: np.ndarray,
                     n_predictions: int = 4000) -> np.ndarray:
    """Generate predictions for a new study from posterior samples.

    Args:
        posterior_samples: Posterior samples for effect of interest
        tau_samples: Posterior samples for heterogeneity
        n_predictions: Number of predictions to generate

    Returns:
        Array of predicted effects for new study
    """
    # Sample from posterior
    n_posterior = len(posterior_samples)
    idx = np.random.choice(n_posterior, size=n_predictions)

    # Generate predictions
    predictions = np.random.normal(
        loc=posterior_samples[idx],
        scale=tau_samples[idx]
    )

    return predictions


class PredictionForNewPopulation:
    """Generate predictions for a new target population with specific covariates.

    Accounts for:
    - Covariate values in new population
    - Uncertainty in regression coefficients
    - Between-study heterogeneity
    """

    def __init__(self,
                 trace: az.InferenceData,
                 covariate_names: list):
        """Initialize prediction for new population.

        Args:
            trace: Posterior samples from meta-regression
            covariate_names: Names of covariates
        """
        self.trace = trace
        self.covariate_names = covariate_names

    def predict(self,
               new_covariates: Dict[str, float],
               treatment_comparison: Tuple[int, int],
               include_heterogeneity: bool = True) -> Dict[str, any]:
        """Generate prediction for new population.

        Args:
            new_covariates: Dictionary of covariate values
            treatment_comparison: Tuple of (treatment1_idx, treatment2_idx)
            include_heterogeneity: Include between-study heterogeneity in prediction

        Returns:
            Dictionary with prediction statistics
        """
        # Extract posterior samples
        d_samples = self.trace.posterior['d_fixed'].values
        beta_samples = self.trace.posterior['beta'].values

        # Flatten
        d_flat = d_samples.reshape(-1, d_samples.shape[-1])
        beta_flat = beta_samples.reshape(-1, beta_samples.shape[-1])

        # Treatment effect
        t1, t2 = treatment_comparison
        treatment_effect = d_flat[:, t2] - d_flat[:, t1]

        # Covariate adjustment
        X_new = np.array([new_covariates.get(cov, 0) for cov in self.covariate_names])
        covariate_effect = beta_flat @ X_new

        # Combined prediction (for mean effect in new population)
        predicted_mean = treatment_effect + covariate_effect

        # Prediction for new study (includes heterogeneity)
        if include_heterogeneity:
            tau_samples = self.trace.posterior['tau'].values.flatten()
            predicted_new_study = np.random.normal(
                loc=predicted_mean,
                scale=tau_samples[:len(predicted_mean)]
            )
        else:
            predicted_new_study = predicted_mean

        return {
            'mean': np.mean(predicted_new_study),
            'median': np.median(predicted_new_study),
            'sd': np.std(predicted_new_study),
            'ci_lower': np.percentile(predicted_new_study, 2.5),
            'ci_upper': np.percentile(predicted_new_study, 97.5),
            'samples': predicted_new_study
        }
