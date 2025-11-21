"""
Small-study effects detection and visualization.

Additional methods for detecting and visualizing small-study effects
in network meta-analysis beyond standard publication bias tests.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from typing import Dict, Optional


def contour_enhanced_funnel(effects: np.ndarray,
                            se: np.ndarray,
                            figsize: tuple = (10, 8)):
    """Create contour-enhanced funnel plot.

    Adds contours showing statistical significance regions.

    Args:
        effects: Effect sizes
        se: Standard errors
        figsize: Figure size
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Plot studies
    ax.scatter(effects, 1/se, alpha=0.6, s=100, edgecolors='black', linewidths=1)

    # Pooled estimate
    weights = 1 / se**2
    pooled_effect = np.sum(weights * effects) / np.sum(weights)

    ax.axvline(x=pooled_effect, color='black', linestyle='--', linewidth=2,
              label='Pooled estimate')

    # Add significance contours
    se_range = np.linspace(se.min(), se.max(), 100)
    precision_range = 1 / se_range

    # Two-tailed 95% significance regions
    z_critical = 1.96
    upper_95 = pooled_effect + z_critical * se_range
    lower_95 = pooled_effect - z_critical * se_range

    ax.fill_betweenx(precision_range, lower_95, upper_95,
                     alpha=0.2, color='white',edgecolor='gray',
                     linestyle='--', label='95% significance')

    # 99% regions
    z_critical_99 = 2.576
    upper_99 = pooled_effect + z_critical_99 * se_range
    lower_99 = pooled_effect - z_critical_99 * se_range

    ax.plot(lower_99, precision_range, 'gray', linestyle=':', alpha=0.5)
    ax.plot(upper_99, precision_range, 'gray', linestyle=':', alpha=0.5)

    ax.set_xlabel('Effect Size', fontsize=12)
    ax.set_ylabel('Precision (1/SE)', fontsize=12)
    ax.set_title('Contour-Enhanced Funnel Plot', fontsize=14)
    ax.invert_yaxis()
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def peters_test(effects: np.ndarray,
               se: np.ndarray,
               sample_sizes: np.ndarray) -> Dict[str, float]:
    """Peters' test for funnel plot asymmetry (for binary outcomes).

    Uses sample size instead of precision as predictor.

    Args:
        effects: Effect sizes (log odds ratios)
        se: Standard errors
        sample_sizes: Total sample sizes

    Returns:
        Test statistics
    """
    # Regress effect on 1/sample_size
    X = np.column_stack([np.ones(len(effects)), 1/sample_sizes])
    y = effects

    # Weighted least squares
    weights = 1 / se**2
    W = np.diag(weights)

    beta = np.linalg.inv(X.T @ W @ X) @ X.T @ W @ y

    # Standard error
    residuals = y - X @ beta
    mse = (residuals.T @ W @ residuals) / (len(effects) - 2)
    se_beta = np.sqrt(mse * np.diag(np.linalg.inv(X.T @ W @ X)))

    # Test intercept
    t_stat = beta[1] / se_beta[1]
    p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), len(effects) - 2))

    return {
        'coefficient': beta[1],
        'se': se_beta[1],
        't_statistic': t_stat,
        'p_value': p_value,
        'bias_detected': p_value < 0.05
    }


def harbord_test(effects: np.ndarray,
                se: np.ndarray) -> Dict[str, float]:
    """Harbord's modified test for small-study effects.

    Modified test that performs better with binary outcomes.

    Args:
        effects: Effect sizes (log odds ratios)
        se: Standard errors

    Returns:
        Test statistics
    """
    # Z-statistic
    Z = effects / se

    # Regress Z on 1/sqrt(V) where V = se^2
    X = np.column_stack([np.ones(len(effects)), 1/se])
    y = Z

    # OLS (unweighted for this test)
    beta = np.linalg.inv(X.T @ X) @ X.T @ y

    # Standard error
    residuals = y - X @ beta
    mse = np.sum(residuals**2) / (len(effects) - 2)
    se_beta = np.sqrt(mse * np.diag(np.linalg.inv(X.T @ X)))

    # Test intercept
    t_stat = beta[0] / se_beta[0]
    p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), len(effects) - 2))

    return {
        'intercept': beta[0],
        'se': se_beta[0],
        't_statistic': t_stat,
        'p_value': p_value,
        'bias_detected': p_value < 0.05
    }


def doi_plot(effects: np.ndarray,
            se: np.ndarray,
            figsize: tuple = (10, 6)):
    """Create DOI (Difference Of Indicator) plot.

    Alternative to funnel plot that may be more sensitive to asymmetry.

    Args:
        effects: Effect sizes
        se: Standard errors
        figsize: Figure size

    Reference:
        Furuya-Kanamori et al. (2018). A new improved graphical and quantitative method.
        International Journal of Evidence-Based Healthcare.
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Compute ranks
    n = len(effects)
    ranks = stats.rankdata(effects)

    # Z-scores
    z_scores = effects / se

    # Fractional ranks (centered)
    u = ranks / (n + 1)

    # DOI
    doi = z_scores + stats.norm.ppf(u)

    # Plot
    ax.scatter(doi, ranks, alpha=0.6, s=100, edgecolors='black', linewidths=1)

    # Add reference lines
    ax.axvline(x=0, color='black', linestyle='--', linewidth=2)

    # Add symmetry bounds (LFK index)
    doi_sorted = np.sort(doi)
    lower_bound = doi_sorted[int(0.1 * n)]
    upper_bound = doi_sorted[int(0.9 * n)]

    ax.axvline(x=lower_bound, color='red', linestyle=':', alpha=0.5)
    ax.axvline(x=upper_bound, color='red', linestyle=':', alpha=0.5)

    # LFK index
    lfk = upper_bound + lower_bound

    ax.set_xlabel('DOI', fontsize=12)
    ax.set_ylabel('Rank', fontsize=12)
    ax.set_title(f'DOI Plot (LFK Index = {lfk:.2f})', fontsize=14)
    ax.grid(True, alpha=0.3)

    # Interpretation
    if abs(lfk) < 1:
        interp = "No asymmetry"
    elif abs(lfk) < 2:
        interp = "Minor asymmetry"
    else:
        interp = "Major asymmetry"

    ax.text(0.02, 0.98, f'Interpretation: {interp}',
           transform=ax.transAxes, va='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    return fig


def p_curve_analysis(effects: np.ndarray,
                    se: np.ndarray) -> Dict[str, any]:
    """P-curve analysis to detect p-hacking and publication bias.

    Tests whether distribution of p-values is right-skewed (evidential value)
    or left-skewed (p-hacking/bias).

    Args:
        effects: Effect sizes
        se: Standard errors

    Returns:
        Dictionary with p-curve test results

    Reference:
        Simonsohn et al. (2014). P-curve: A key to the file-drawer.
        Journal of Experimental Psychology: General.
    """
    # Calculate p-values (two-tailed)
    z_scores = np.abs(effects / se)
    p_values = 2 * (1 - stats.norm.cdf(z_scores))

    # Filter to significant results only (p < 0.05)
    sig_p = p_values[p_values < 0.05]

    if len(sig_p) < 10:
        return {
            'n_significant': len(sig_p),
            'sufficient_power': False,
            'evidential_value': None,
            'message': 'Insufficient significant results for p-curve analysis'
        }

    # Test if p-curve is right-skewed (evidential value)
    # Expected distribution under H0: uniform on [0, 0.05]
    # Under evidential value: right-skewed (more low p-values)

    # Stouffer's method for combining p-values
    # Convert to pp-values (what p-values would be if all effects = 0.05 level)
    pp_values = sig_p * 20  # Scale to [0, 1]

    # Test for right skew: use binomial test
    # Under H0, 50% should be < 0.025
    n_below_half = np.sum(pp_values < 0.5)
    n_total = len(pp_values)

    # Binomial test
    p_right_skew = 1 - stats.binom.cdf(n_below_half - 1, n_total, 0.5)

    # Test for 33% power
    # Under 33% power, expect right skew
    p_33_power = 1 - stats.binom.cdf(n_below_half - 1, n_total, 0.57)

    return {
        'n_significant': len(sig_p),
        'n_below_median': n_below_half,
        'p_right_skew': p_right_skew,
        'p_33_power': p_33_power,
        'evidential_value': p_right_skew < 0.05,
        'adequate_power': p_33_power < 0.05,
        'interpretation': _interpret_p_curve(p_right_skew, p_33_power)
    }


def _interpret_p_curve(p_right: float, p_power: float) -> str:
    """Interpret p-curve results."""
    if p_right < 0.05 and p_power < 0.05:
        return "Strong evidential value, adequate power"
    elif p_right < 0.05:
        return "Evidential value present, but may lack power"
    elif p_right > 0.90:
        return "Absence of evidential value, suggests p-hacking"
    else:
        return "Inconclusive"
