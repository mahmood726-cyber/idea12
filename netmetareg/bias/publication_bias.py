"""
Publication bias detection and adjustment for network meta-analysis.

Implements:
- Selection models for publication bias
- Comparison-adjusted funnel plots
- Network-specific bias detection
- Sensitivity analyses

References:
    Chaimani et al. (2013). Using network meta-analysis to evaluate the existence of
    small-study effects in a network of interventions. Research Synthesis Methods.

    Copas & Shi (2000). Meta-analysis, funnel plots and sensitivity analysis.
    Biostatistics, 1(3), 247-262.

    Egger et al. (1997). Bias in meta-analysis detected by a simple, graphical test.
    BMJ, 315(7109), 629-634.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.optimize import minimize
from typing import Optional, Dict, List, Tuple
import warnings


class SelectionModel:
    """Bayesian selection model for publication bias.

    Models the selection process where studies with significant results
    are more likely to be published:

    P(published | effect, se) = 1 / (1 + exp(-alpha - beta * |z|))

    where z = effect / se is the z-score.

    References:
        Hedges & Vevea (1996). Estimating effect size under publication bias.
        Psychological Bulletin.
    """

    def __init__(self, effects: np.ndarray, se: np.ndarray):
        """Initialize selection model.

        Args:
            effects: Array of effect sizes
            se: Array of standard errors
        """
        self.effects = np.array(effects)
        self.se = np.array(se)
        self.n = len(effects)

        # Compute z-scores
        self.z_scores = self.effects / self.se

    def fit_step_function(self,
                         cutpoints: List[float] = [0.025, 0.5, 1.0],
                         ) -> Dict[str, float]:
        """Fit step-function selection model.

        Models selection probability as step function based on p-value.

        Args:
            cutpoints: P-value cutpoints for step function

        Returns:
            Dictionary with selection parameters and adjusted effect
        """
        # Compute p-values (two-tailed)
        p_values = 2 * (1 - stats.norm.cdf(np.abs(self.z_scores)))

        # Categorize by p-value
        categories = np.digitize(p_values, cutpoints)

        def neg_log_likelihood(params):
            """Negative log-likelihood for selection model."""
            mu = params[0]  # True effect
            tau = np.exp(params[1])  # Between-study SD
            # Selection weights (constrained to [0, 1])
            weights = 1 / (1 + np.exp(-params[2:]))

            ll = 0
            for i in range(self.n):
                # Likelihood of observed effect
                sigma_i = np.sqrt(self.se[i]**2 + tau**2)
                ll_obs = stats.norm.logpdf(self.effects[i], mu, sigma_i)

                # Selection probability
                cat = categories[i]
                if cat < len(weights):
                    p_select = weights[cat]
                else:
                    p_select = weights[-1]

                ll += ll_obs + np.log(p_select + 1e-10)

            return -ll

        # Initial values
        init_params = np.concatenate([
            [np.mean(self.effects)],  # mu
            [0],  # log(tau)
            [0] * (len(cutpoints) + 1)  # log-odds of selection weights
        ])

        # Optimize
        try:
            result = minimize(neg_log_likelihood, init_params, method='L-BFGS-B')

            mu_adj = result.x[0]
            tau_adj = np.exp(result.x[1])
            weights = 1 / (1 + np.exp(-result.x[2:]))

            return {
                'adjusted_effect': mu_adj,
                'adjusted_tau': tau_adj,
                'selection_weights': weights,
                'unadjusted_effect': np.mean(self.effects),
                'bias_correction': mu_adj - np.mean(self.effects),
                'converged': result.success
            }
        except Exception as e:
            warnings.warn(f"Selection model failed to converge: {str(e)}")
            return {
                'adjusted_effect': np.nan,
                'adjusted_tau': np.nan,
                'selection_weights': None,
                'unadjusted_effect': np.mean(self.effects),
                'bias_correction': np.nan,
                'converged': False
            }

    def test_egger(self) -> Dict[str, float]:
        """Egger's test for funnel plot asymmetry.

        Tests whether smaller studies show different effects.

        Returns:
            Dictionary with test statistics
        """
        # Precision (inverse variance)
        precision = 1 / self.se

        # Regress effect on precision
        X = np.column_stack([np.ones(self.n), precision])
        y = self.effects

        # Weighted least squares (weights = precision^2)
        W = np.diag(precision**2)
        beta = np.linalg.inv(X.T @ W @ X) @ X.T @ W @ y

        # Standard error of intercept
        residuals = y - X @ beta
        mse = (residuals.T @ W @ residuals) / (self.n - 2)
        se_intercept = np.sqrt(mse * np.linalg.inv(X.T @ W @ X)[0, 0])

        # Test statistic
        t_stat = beta[0] / se_intercept
        p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), self.n - 2))

        return {
            'intercept': beta[0],
            'se_intercept': se_intercept,
            't_statistic': t_stat,
            'p_value': p_value,
            'bias_detected': p_value < 0.05
        }

    def trim_and_fill(self, side: str = 'auto') -> Dict[str, any]:
        """Trim-and-fill method for estimating missing studies.

        Args:
            side: Which side to impute ('left', 'right', 'auto')

        Returns:
            Dictionary with adjusted estimate and imputed studies
        """
        # Rank studies by effect size
        ranks = stats.rankdata(self.effects)

        # Find center of distribution
        if side == 'auto':
            # Use sign of Egger's test
            egger = self.test_egger()
            side = 'left' if egger['intercept'] < 0 else 'right'

        # Identify potentially missing studies
        median_rank = (self.n + 1) / 2
        if side == 'left':
            trimmed = self.effects < np.median(self.effects)
        else:
            trimmed = self.effects > np.median(self.effects)

        n_trimmed = np.sum(trimmed)

        # Estimate effect after trimming
        effect_trimmed = np.mean(self.effects[~trimmed])

        # Impute missing studies (mirror image)
        if n_trimmed > 0:
            effects_filled = np.concatenate([
                self.effects,
                2 * effect_trimmed - self.effects[trimmed]
            ])
            se_filled = np.concatenate([
                self.se,
                self.se[trimmed]
            ])

            # Adjusted estimate
            weights = 1 / se_filled**2
            effect_adj = np.sum(weights * effects_filled) / np.sum(weights)
        else:
            effects_filled = self.effects
            se_filled = self.se
            effect_adj = np.mean(self.effects)

        return {
            'n_imputed': n_trimmed,
            'adjusted_effect': effect_adj,
            'imputed_effects': 2 * effect_trimmed - self.effects[trimmed] if n_trimmed > 0 else np.array([]),
            'imputed_se': self.se[trimmed] if n_trimmed > 0 else np.array([]),
            'unadjusted_effect': np.mean(self.effects)
        }


class ComparisonAdjustedFunnel:
    """Comparison-adjusted funnel plot for network meta-analysis.

    Extends standard funnel plot to network setting by adjusting for
    comparison type.

    References:
        Chaimani & Salanti (2012). Using network meta-analysis to evaluate
        the existence of small-study effects. Research Synthesis Methods.
    """

    def __init__(self,
                 effects: np.ndarray,
                 se: np.ndarray,
                 comparisons: np.ndarray,
                 comparison_estimates: Dict[str, float]):
        """Initialize comparison-adjusted funnel plot.

        Args:
            effects: Observed effect sizes
            se: Standard errors
            comparisons: Comparison labels for each study
            comparison_estimates: Network estimates for each comparison
        """
        self.effects = np.array(effects)
        self.se = np.array(se)
        self.comparisons = np.array(comparisons)
        self.comparison_estimates = comparison_estimates

    def compute_adjusted_effects(self) -> np.ndarray:
        """Compute comparison-adjusted effects.

        Subtracts the comparison-specific network estimate from each study.

        Returns:
            Adjusted effect sizes
        """
        adjusted = np.zeros_like(self.effects)

        for i, comp in enumerate(self.comparisons):
            if comp in self.comparison_estimates:
                adjusted[i] = self.effects[i] - self.comparison_estimates[comp]
            else:
                # Try reverse comparison
                comp_parts = comp.split('-')
                if len(comp_parts) == 2:
                    reverse_comp = f"{comp_parts[1]}-{comp_parts[0]}"
                    if reverse_comp in self.comparison_estimates:
                        adjusted[i] = self.effects[i] + self.comparison_estimates[reverse_comp]
                    else:
                        adjusted[i] = self.effects[i]

        return adjusted

    def test_asymmetry(self) -> Dict[str, float]:
        """Test for funnel plot asymmetry using adjusted effects.

        Returns:
            Dictionary with test results
        """
        adjusted_effects = self.compute_adjusted_effects()

        # Precision
        precision = 1 / self.se

        # Regression
        X = np.column_stack([np.ones(len(self.effects)), precision])
        y = adjusted_effects

        # Weighted least squares
        W = np.diag(precision**2)
        beta = np.linalg.inv(X.T @ W @ X) @ X.T @ W @ y

        # Standard error
        residuals = y - X @ beta
        mse = (residuals.T @ W @ residuals) / (len(self.effects) - 2)
        se_intercept = np.sqrt(mse * np.linalg.inv(X.T @ W @ X)[0, 0])

        # Test
        t_stat = beta[0] / se_intercept
        p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), len(self.effects) - 2))

        return {
            'intercept': beta[0],
            'se': se_intercept,
            't_statistic': t_stat,
            'p_value': p_value,
            'small_study_effects': p_value < 0.05
        }

    def plot(self,
            figsize: tuple = (10, 8),
            comparison_colors: Optional[Dict] = None):
        """Create comparison-adjusted funnel plot.

        Args:
            figsize: Figure size
            comparison_colors: Optional color mapping for comparisons
        """
        adjusted_effects = self.compute_adjusted_effects()

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

        # Standard funnel plot
        ax1.scatter(self.effects, 1/self.se, alpha=0.6)
        ax1.axvline(x=0, color='black', linestyle='--')
        ax1.set_xlabel('Effect Size')
        ax1.set_ylabel('Precision (1/SE)')
        ax1.set_title('Standard Funnel Plot')
        ax1.invert_yaxis()
        ax1.grid(True, alpha=0.3)

        # Comparison-adjusted funnel plot
        if comparison_colors is None:
            unique_comps = np.unique(self.comparisons)
            comparison_colors = {
                comp: plt.cm.tab10(i % 10)
                for i, comp in enumerate(unique_comps)
            }

        for comp in np.unique(self.comparisons):
            mask = self.comparisons == comp
            ax2.scatter(
                adjusted_effects[mask],
                1/self.se[mask],
                label=comp,
                alpha=0.6,
                color=comparison_colors.get(comp)
            )

        ax2.axvline(x=0, color='black', linestyle='--')
        ax2.set_xlabel('Comparison-Adjusted Effect')
        ax2.set_ylabel('Precision (1/SE)')
        ax2.set_title('Comparison-Adjusted Funnel Plot')
        ax2.invert_yaxis()
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig


class NetworkMetaBias:
    """Comprehensive publication bias assessment for network meta-analysis.

    Integrates multiple methods:
    - Comparison-adjusted funnel plots
    - Network-wide bias detection
    - Sensitivity to bias adjustment
    """

    def __init__(self, nma_data):
        """Initialize network meta-bias assessment.

        Args:
            nma_data: NMAData object with study information
        """
        self.data = nma_data

    def assess_all_comparisons(self) -> pd.DataFrame:
        """Assess publication bias for all direct comparisons.

        Returns:
            DataFrame with bias assessment for each comparison
        """
        results = []

        # Group studies by comparison
        comparison_groups = {}
        for study in self.data.studies:
            for i in range(len(study.treatments)):
                for j in range(i + 1, len(study.treatments)):
                    comp = f"{study.treatments[i]}-{study.treatments[j]}"
                    if comp not in comparison_groups:
                        comparison_groups[comp] = []

                    comparison_groups[comp].append({
                        'effect': study.effects[j-1] if hasattr(study, 'effects') else None,
                        'se': study.se[j-1] if hasattr(study, 'se') else None
                    })

        # Test each comparison
        for comp, studies in comparison_groups.items():
            if len(studies) < 3:
                continue  # Need at least 3 studies for tests

            effects = np.array([s['effect'] for s in studies if s['effect'] is not None])
            se = np.array([s['se'] for s in studies if s['se'] is not None])

            if len(effects) < 3:
                continue

            # Create selection model
            sel_model = SelectionModel(effects, se)

            # Egger's test
            egger = sel_model.test_egger()

            # Trim-and-fill
            taf = sel_model.trim_and_fill()

            results.append({
                'comparison': comp,
                'n_studies': len(effects),
                'egger_p': egger['p_value'],
                'egger_bias_detected': egger['bias_detected'],
                'taf_n_imputed': taf['n_imputed'],
                'effect_unadjusted': np.mean(effects),
                'effect_adjusted_taf': taf['adjusted_effect']
            })

        return pd.DataFrame(results)

    def network_wide_test(self,
                         network_estimates: Dict[str, float]) -> Dict[str, any]:
        """Network-wide test for small-study effects.

        Uses comparison-adjusted funnel plot approach.

        Args:
            network_estimates: Dictionary of comparison -> network estimate

        Returns:
            Test results
        """
        # Collect all studies
        effects = []
        se = []
        comparisons = []

        for study in self.data.studies:
            if not hasattr(study, 'effects') or not hasattr(study, 'se'):
                continue

            for i in range(len(study.treatments)):
                for j in range(i + 1, len(study.treatments)):
                    comp = f"{study.treatments[i]}-{study.treatments[j]}"
                    effects.append(study.effects[j-1])
                    se.append(study.se[j-1])
                    comparisons.append(comp)

        if len(effects) < 10:
            return {
                'test_performed': False,
                'reason': 'Insufficient studies for network-wide test'
            }

        # Comparison-adjusted funnel plot
        caf = ComparisonAdjustedFunnel(
            np.array(effects),
            np.array(se),
            np.array(comparisons),
            network_estimates
        )

        test_result = caf.test_asymmetry()

        return {
            'test_performed': True,
            'p_value': test_result['p_value'],
            'small_study_effects_detected': test_result['small_study_effects'],
            'intercept': test_result['intercept'],
            'n_studies': len(effects)
        }


def detect_small_study_effects(effects: np.ndarray,
                               se: np.ndarray,
                               method: str = 'egger') -> Dict[str, float]:
    """Convenience function to detect small-study effects.

    Args:
        effects: Effect sizes
        se: Standard errors
        method: Detection method ('egger', 'trim_fill', 'selection')

    Returns:
        Test results
    """
    sel_model = SelectionModel(effects, se)

    if method == 'egger':
        return sel_model.test_egger()
    elif method == 'trim_fill':
        return sel_model.trim_and_fill()
    elif method == 'selection':
        return sel_model.fit_step_function()
    else:
        raise ValueError(f"Unknown method: {method}")
