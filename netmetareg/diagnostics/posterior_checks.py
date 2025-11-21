"""
Posterior predictive checks for network meta-analysis models.

Implements comprehensive model diagnostics including:
- Graphical posterior predictive checks
- Test statistics for model adequacy
- Residual diagnostics
- Calibration assessment

References:
    Gelman et al. (2013). Bayesian Data Analysis (3rd ed.). Chapter 6.
    Gabry et al. (2019). Visualization in Bayesian workflow. JRSS-A.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import arviz as az
from typing import Optional, List, Callable, Dict
from scipy import stats


class PosteriorPredictiveChecks:
    """Comprehensive posterior predictive checking for NMA models.

    Provides graphical and numerical checks for:
    - Distributional adequacy
    - Outliers and model fit
    - Heterogeneity assessment
    - Calibration
    """

    def __init__(self, trace: az.InferenceData, y_obs: np.ndarray):
        """Initialize posterior predictive checks.

        Args:
            trace: InferenceData object with posterior and posterior_predictive
            y_obs: Observed data
        """
        self.trace = trace
        self.y_obs = y_obs

        if not hasattr(trace, 'posterior_predictive'):
            raise ValueError("InferenceData must contain posterior_predictive group")

        self.y_rep = trace.posterior_predictive['y_like'].values

    def check_all(self, figsize: tuple = (15, 10)) -> Dict[str, float]:
        """Run all posterior predictive checks.

        Args:
            figsize: Figure size for plots

        Returns:
            Dictionary with p-values for all test statistics
        """
        fig = plt.figure(figsize=figsize)
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # 1. Density overlay
        ax1 = fig.add_subplot(gs[0, :2])
        self.plot_density_overlay(ax=ax1)

        # 2. Test statistics
        ax2 = fig.add_subplot(gs[0, 2])
        p_values = self.plot_test_statistics(ax=ax2)

        # 3. Quantile-quantile plot
        ax3 = fig.add_subplot(gs[1, 0])
        self.plot_qq(ax=ax3)

        # 4. Residuals
        ax4 = fig.add_subplot(gs[1, 1])
        self.plot_residuals(ax=ax4)

        # 5. LOO-PIT
        ax5 = fig.add_subplot(gs[1, 2])
        self.plot_loo_pit(ax=ax5)

        # 6. Scatter plot
        ax6 = fig.add_subplot(gs[2, 0])
        self.plot_observed_vs_predicted(ax=ax6)

        # 7. Histogram of residuals
        ax7 = fig.add_subplot(gs[2, 1])
        self.plot_residual_histogram(ax=ax7)

        # 8. Calibration plot
        ax8 = fig.add_subplot(gs[2, 2])
        self.plot_calibration(ax=ax8)

        plt.suptitle('Posterior Predictive Checks', fontsize=14, y=0.995)

        return p_values

    def plot_density_overlay(self, ax: Optional[plt.Axes] = None):
        """Plot density of observed data vs. posterior predictive replicates.

        Args:
            ax: Matplotlib axes (creates new if None)
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 5))

        # Flatten posterior predictive samples
        y_rep_flat = self.y_rep.reshape(-1, self.y_rep.shape[-1])

        # Plot densities for multiple replicates
        for i in range(min(100, y_rep_flat.shape[0])):
            kde = stats.gaussian_kde(y_rep_flat[i])
            x_range = np.linspace(self.y_obs.min() - 1, self.y_obs.max() + 1, 200)
            ax.plot(x_range, kde(x_range), color='lightblue', alpha=0.05)

        # Observed data density
        kde_obs = stats.gaussian_kde(self.y_obs)
        x_range = np.linspace(self.y_obs.min() - 1, self.y_obs.max() + 1, 200)
        ax.plot(x_range, kde_obs(x_range), color='black', linewidth=2,
                label='Observed')

        ax.set_xlabel('Effect Size')
        ax.set_ylabel('Density')
        ax.set_title('Density Overlay')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def plot_test_statistics(self, ax: Optional[plt.Axes] = None) -> Dict[str, float]:
        """Plot posterior predictive p-values for multiple test statistics.

        Args:
            ax: Matplotlib axes

        Returns:
            Dictionary of p-values
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 6))

        # Test statistics
        test_stats = {
            'Mean': lambda y: np.mean(y),
            'SD': lambda y: np.std(y),
            'Min': lambda y: np.min(y),
            'Max': lambda y: np.max(y),
            'Median': lambda y: np.median(y),
            'IQR': lambda y: np.percentile(y, 75) - np.percentile(y, 25)
        }

        p_values = {}
        names = []
        pvals = []

        for name, stat_func in test_stats.items():
            T_obs = stat_func(self.y_obs)
            T_rep = np.array([stat_func(self.y_rep[:, :, i].flatten())
                             for i in range(self.y_rep.shape[-1])])
            T_rep_mean = T_rep.mean()

            # Bayesian p-value
            p_value = np.mean(T_rep >= T_obs)
            p_values[name] = p_value
            names.append(name)
            pvals.append(p_value)

        # Plot p-values
        colors = ['red' if (p < 0.025 or p > 0.975) else 'green' for p in pvals]
        ax.barh(names, pvals, color=colors, alpha=0.6)
        ax.axvline(x=0.5, color='black', linestyle='--', alpha=0.5)
        ax.axvline(x=0.025, color='red', linestyle=':', alpha=0.5)
        ax.axvline(x=0.975, color='red', linestyle=':', alpha=0.5)
        ax.set_xlabel('Posterior Predictive P-Value')
        ax.set_title('Test Statistics')
        ax.set_xlim(0, 1)
        ax.grid(True, alpha=0.3, axis='x')

        return p_values

    def plot_qq(self, ax: Optional[plt.Axes] = None):
        """Q-Q plot of observed vs. predicted quantiles.

        Args:
            ax: Matplotlib axes
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 6))

        # Compute quantiles
        y_pred_mean = self.y_rep.mean(axis=(0, 1))

        # Q-Q plot
        stats.probplot(self.y_obs, dist=stats.norm,
                      fit=True, plot=ax)

        ax.set_title('Q-Q Plot')
        ax.grid(True, alpha=0.3)

    def plot_residuals(self, ax: Optional[plt.Axes] = None):
        """Plot residuals vs. fitted values.

        Args:
            ax: Matplotlib axes
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 5))

        # Posterior mean predictions
        y_pred = self.y_rep.mean(axis=(0, 1))

        # Residuals
        residuals = self.y_obs - y_pred

        ax.scatter(y_pred, residuals, alpha=0.6)
        ax.axhline(y=0, color='red', linestyle='--')
        ax.set_xlabel('Fitted Values')
        ax.set_ylabel('Residuals')
        ax.set_title('Residuals vs. Fitted')
        ax.grid(True, alpha=0.3)

        # Add loess smooth
        try:
            from scipy.interpolate import make_interp_spline
            sorted_idx = np.argsort(y_pred)
            spl = make_interp_spline(y_pred[sorted_idx], residuals[sorted_idx], k=3)
            x_smooth = np.linspace(y_pred.min(), y_pred.max(), 100)
            y_smooth = spl(x_smooth)
            ax.plot(x_smooth, y_smooth, color='blue', linewidth=2)
        except:
            pass

    def plot_loo_pit(self, ax: Optional[plt.Axes] = None):
        """Plot LOO-PIT (Probability Integral Transform) histogram.

        Uniform distribution indicates good calibration.

        Args:
            ax: Matplotlib axes
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 5))

        # Compute LOO-PIT values
        try:
            loo_pit = az.loo_pit(idata=self.trace, y='y_like')
            pit_values = loo_pit['y_like'].values

            ax.hist(pit_values, bins=20, density=True, alpha=0.6,
                   edgecolor='black')
            ax.axhline(y=1, color='red', linestyle='--', label='Uniform')
            ax.set_xlabel('PIT Value')
            ax.set_ylabel('Density')
            ax.set_title('LOO-PIT Histogram')
            ax.legend()
            ax.grid(True, alpha=0.3)
        except Exception as e:
            ax.text(0.5, 0.5, f'LOO-PIT computation failed:\n{str(e)}',
                   ha='center', va='center', transform=ax.transAxes)

    def plot_observed_vs_predicted(self, ax: Optional[plt.Axes] = None):
        """Scatter plot of observed vs. predicted values.

        Args:
            ax: Matplotlib axes
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 6))

        y_pred = self.y_rep.mean(axis=(0, 1))

        ax.scatter(self.y_obs, y_pred, alpha=0.6)

        # Add 45-degree line
        min_val = min(self.y_obs.min(), y_pred.min())
        max_val = max(self.y_obs.max(), y_pred.max())
        ax.plot([min_val, max_val], [min_val, max_val],
               'r--', label='Perfect prediction')

        ax.set_xlabel('Observed')
        ax.set_ylabel('Predicted (mean)')
        ax.set_title('Observed vs. Predicted')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Add R²
        r_squared = np.corrcoef(self.y_obs, y_pred)[0, 1]**2
        ax.text(0.05, 0.95, f'R² = {r_squared:.3f}',
               transform=ax.transAxes, va='top')

    def plot_residual_histogram(self, ax: Optional[plt.Axes] = None):
        """Histogram of residuals with normal overlay.

        Args:
            ax: Matplotlib axes
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 5))

        y_pred = self.y_rep.mean(axis=(0, 1))
        residuals = self.y_obs - y_pred

        ax.hist(residuals, bins=20, density=True, alpha=0.6,
               edgecolor='black', label='Residuals')

        # Normal overlay
        mu, sigma = residuals.mean(), residuals.std()
        x = np.linspace(residuals.min(), residuals.max(), 100)
        ax.plot(x, stats.norm.pdf(x, mu, sigma), 'r-',
               label=f'N({mu:.2f}, {sigma:.2f}²)')

        ax.set_xlabel('Residual')
        ax.set_ylabel('Density')
        ax.set_title('Residual Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def plot_calibration(self, ax: Optional[plt.Axes] = None):
        """Calibration plot for prediction intervals.

        Args:
            ax: Matplotlib axes
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 6))

        # Compute coverage at different levels
        levels = np.arange(0.1, 1.0, 0.05)
        empirical_coverage = []

        for level in levels:
            lower_q = (1 - level) / 2
            upper_q = 1 - lower_q

            y_lower = np.percentile(self.y_rep, lower_q * 100, axis=(0, 1))
            y_upper = np.percentile(self.y_rep, upper_q * 100, axis=(0, 1))

            coverage = np.mean((self.y_obs >= y_lower) & (self.y_obs <= y_upper))
            empirical_coverage.append(coverage)

        ax.plot(levels, empirical_coverage, 'o-', label='Empirical')
        ax.plot([0, 1], [0, 1], 'r--', label='Perfect calibration')

        ax.set_xlabel('Nominal Coverage')
        ax.set_ylabel('Empirical Coverage')
        ax.set_title('Calibration Plot')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def compute_standardized_residuals(self,
                                      se_obs: Optional[np.ndarray] = None) -> np.ndarray:
        """Compute standardized residuals.

        Args:
            se_obs: Standard errors of observations (optional)

        Returns:
            Standardized residuals
        """
        y_pred = self.y_rep.mean(axis=(0, 1))
        residuals = self.y_obs - y_pred

        if se_obs is not None:
            # Account for observation uncertainty
            residuals_std = residuals / se_obs
        else:
            # Use posterior predictive SD
            y_pred_sd = self.y_rep.std(axis=(0, 1))
            residuals_std = residuals / y_pred_sd

        return residuals_std

    def identify_outliers(self,
                         threshold: float = 3.0,
                         se_obs: Optional[np.ndarray] = None) -> pd.DataFrame:
        """Identify potential outliers using standardized residuals.

        Args:
            threshold: Threshold in SD units (default: 3)
            se_obs: Standard errors of observations

        Returns:
            DataFrame with potential outliers
        """
        residuals_std = self.compute_standardized_residuals(se_obs)
        y_pred = self.y_rep.mean(axis=(0, 1))

        outliers = []
        for i, (obs, pred, resid_std) in enumerate(zip(self.y_obs, y_pred, residuals_std)):
            if np.abs(resid_std) > threshold:
                outliers.append({
                    'index': i,
                    'observed': obs,
                    'predicted': pred,
                    'std_residual': resid_std,
                    'abs_residual': np.abs(obs - pred)
                })

        df = pd.DataFrame(outliers)
        if len(df) > 0:
            df = df.sort_values('abs_residual', ascending=False)

        return df


def posterior_predictive_pvalue(trace: az.InferenceData,
                                y_obs: np.ndarray,
                                test_statistic: Callable) -> float:
    """Compute posterior predictive p-value for a test statistic.

    Args:
        trace: InferenceData with posterior_predictive
        y_obs: Observed data
        test_statistic: Function computing test statistic from data

    Returns:
        Bayesian p-value
    """
    T_obs = test_statistic(y_obs)

    y_rep = trace.posterior_predictive['y_like'].values
    T_rep = np.array([test_statistic(y_rep[:, :, i].flatten())
                     for i in range(y_rep.shape[-1])])

    p_value = np.mean(T_rep >= T_obs)

    return p_value
