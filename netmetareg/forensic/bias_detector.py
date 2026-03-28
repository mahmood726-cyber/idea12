"""
Forensic Bias Detection Module
===============================

Implements three metrics for detecting and quantifying bias in discordant
meta-analyses where observational studies and RCTs disagree.

Author: Integrated from validated R implementation
Date: January 2025
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import warnings


@dataclass
class ForensicResults:
    """Results from forensic bias analysis"""
    discordance_index: float
    e_value_point: float
    e_value_lower: Optional[float]
    inflation_factor: float
    nominal_n: int
    effective_n: float
    evidence_grade: str
    interpretation: Dict[str, str]

    def to_dict(self) -> Dict:
        """Convert results to dictionary"""
        return {
            'Discordance_Index': round(self.discordance_index, 2),
            'E_Value': round(self.e_value_point, 2),
            'E_Value_Lower': round(self.e_value_lower, 2) if self.e_value_lower else None,
            'Inflation_Factor': f"{int(round(self.inflation_factor, 0))}x",
            'Nominal_N': self.nominal_n,
            'Effective_N': int(round(self.effective_n, 0)),
            'Evidence_Grade': self.evidence_grade,
            'Interpretation': self.interpretation
        }

    def __str__(self) -> str:
        """Formatted string representation"""
        lines = [
            "="*70,
            "FORENSIC BIAS ANALYSIS RESULTS",
            "="*70,
            "",
            "METRIC 1: DISCORDANCE INDEX",
            f"  DI Score: {self.discordance_index:.2f}",
            f"  Evidence Grade: {self.evidence_grade}",
            "",
            "METRIC 2: CONFOUNDING SCORE (E-VALUE)",
            f"  Point Estimate: {self.e_value_point:.2f}",
            f"  Lower CI: {self.e_value_lower:.2f}" if self.e_value_lower else "",
            "",
            "METRIC 3: INFORMATION INFLATION",
            f"  Nominal Sample Size: {self.nominal_n:,}",
            f"  Effective Sample Size: {self.effective_n:,.0f}",
            f"  Inflation Factor: {self.inflation_factor:.0f}x",
            "",
            "INTERPRETATION",
            "="*70
        ]

        for key, value in self.interpretation.items():
            lines.append(f"{key}: {value}")

        lines.append("="*70)
        return "\n".join(lines)


class ForensicAnalyzer:
    """
    Forensic Meta-Analysis: Detect and Quantify Bias in Discordant Evidence

    This class implements the three-metric framework for identifying when
    observational studies provide misleading evidence compared to RCTs.

    Parameters
    ----------
    obs_data : pd.DataFrame
        Observational studies data with columns: study, effect, se, n
    rct_data : pd.DataFrame
        RCT data with columns: study, effect, se, n
    effect_type : str
        Type of effect size: 'log_hr', 'log_or', 'log_rr', 'smd'
    rare_outcome : bool
        Whether outcome is rare (<15%). Affects E-value calculation.

    Attributes
    ----------
    obs_pooled : dict
        Pooled observational estimate {effect, se, n}
    rct_pooled : dict
        Pooled RCT estimate {effect, se, n}

    Methods
    -------
    analyze()
        Run complete forensic analysis
    calculate_discordance()
        Calculate Discordance Index
    calculate_confounding_score()
        Calculate E-Value
    calculate_inflation()
        Calculate Inflation Factor

    Examples
    --------
    >>> obs = pd.DataFrame({
    ...     'study': ['Bavishi', 'Liu', 'SwedeHF'],
    ...     'effect': [np.log(0.81), np.log(0.91), np.log(0.93)],
    ...     'se': [0.046, 0.021, 0.036],
    ...     'n': [27099, 21206, 19083]
    ... })
    >>> rct = pd.DataFrame({
    ...     'study': ['REBOOT', 'REDUCE-AMI'],
    ...     'effect': [np.log(0.97), np.log(0.96)],
    ...     'se': [0.051, 0.095],
    ...     'n': [17801, 5020]
    ... })
    >>> analyzer = ForensicAnalyzer(obs, rct, effect_type='log_hr')
    >>> results = analyzer.analyze()
    >>> print(results)
    """

    def __init__(
        self,
        obs_data: pd.DataFrame,
        rct_data: pd.DataFrame,
        effect_type: str = 'log_hr',
        rare_outcome: bool = False,
        sigma_ref: Optional[float] = None
    ):
        self.obs_data = obs_data.copy()
        self.rct_data = rct_data.copy()
        self.effect_type = effect_type
        self.rare_outcome = rare_outcome

        # Set reference sigma based on effect type
        if sigma_ref is None:
            self.sigma_ref = self._get_default_sigma()
        else:
            self.sigma_ref = sigma_ref

        # Clean and validate data (order matters!)
        self._check_missing_data()  # Remove missing first
        self._validate_data()       # Then validate
        self._check_edge_cases()    # Then check edge cases

        # Pool estimates
        self.obs_pooled = self._pool_studies(self.obs_data)
        self.rct_pooled = self._pool_studies(self.rct_data)

    def _get_default_sigma(self) -> float:
        """Get default reference sigma based on effect type"""
        sigma_defaults = {
            'log_hr': 2.0,
            'log_or': 2.0,
            'log_rr': 2.0,
            'smd': 0.25,  # Standardized mean difference
            'md': 5.0     # Mean difference (domain-specific)
        }

        if self.effect_type not in sigma_defaults:
            warnings.warn(
                f"Unknown effect type '{self.effect_type}'. Using sigma=2.0. "
                f"Consider specifying sigma_ref explicitly."
            )
            return 2.0

        return sigma_defaults[self.effect_type]

    def _validate_data(self):
        """Validate input data"""
        required_cols = ['effect', 'se', 'n']

        for col in required_cols:
            if col not in self.obs_data.columns:
                raise ValueError(f"obs_data missing required column: {col}")
            if col not in self.rct_data.columns:
                raise ValueError(f"rct_data missing required column: {col}")

        if len(self.obs_data) == 0:
            raise ValueError("obs_data must contain at least one study")
        if len(self.rct_data) == 0:
            raise ValueError("rct_data must contain at least one study")

        # Check for valid numeric values
        for df, name in [(self.obs_data, 'obs_data'), (self.rct_data, 'rct_data')]:
            if not np.isfinite(df['effect']).all():
                raise ValueError(f"{name} contains non-finite effect sizes")
            if not (df['se'] > 0).all():
                raise ValueError(f"{name} contains non-positive standard errors")
            if not (df['n'] > 0).all():
                raise ValueError(f"{name} contains non-positive sample sizes")

    def _check_missing_data(self):
        """Check for missing data and remove if necessary"""
        required_cols = ['effect', 'se', 'n']

        # Only check if columns exist
        obs_cols = [c for c in required_cols if c in self.obs_data.columns]
        rct_cols = [c for c in required_cols if c in self.rct_data.columns]

        if len(obs_cols) == len(required_cols):
            obs_missing = self.obs_data[obs_cols].isnull().any(axis=1)

            if obs_missing.any():
                n_missing = obs_missing.sum()
                warnings.warn(
                    f"Removing {n_missing} observational studies with missing data"
                )
                self.obs_data = self.obs_data[~obs_missing].copy()

        if len(rct_cols) == len(required_cols):
            rct_missing = self.rct_data[rct_cols].isnull().any(axis=1)

            if rct_missing.any():
                n_missing = rct_missing.sum()
                warnings.warn(
                    f"Removing {n_missing} RCT studies with missing data"
                )
                self.rct_data = self.rct_data[~rct_missing].copy()

    def _check_edge_cases(self):
        """Check for edge cases and issue warnings"""
        # Small number of studies
        if len(self.obs_data) < 2:
            warnings.warn(
                "Only 1 observational study. Heterogeneity and ESS metrics may be unreliable."
            )

        if len(self.rct_data) < 2:
            warnings.warn(
                "Only 1 RCT. Discordance Index has reduced power."
            )

        # Very small sample sizes
        if (self.obs_data['n'] < 50).any():
            warnings.warn(
                "Some observational studies have N < 50. Results may be unstable."
            )

        if (self.rct_data['n'] < 50).any():
            warnings.warn(
                "Some RCTs have N < 50. Results may be unstable."
            )

        # Extreme heterogeneity
        if len(self.obs_data) >= 3:
            q_stat = self._calculate_q_statistic(self.obs_data)
            df = len(self.obs_data) - 1
            # Critical value for Q at p=0.01
            from scipy import stats
            critical_q = stats.chi2.ppf(0.99, df)
            if q_stat > critical_q:
                warnings.warn(
                    f"Extreme heterogeneity in observational data (Q={q_stat:.1f}, df={df}). "
                    f"Consider subgroup analysis."
                )

    def _pool_studies(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Pool studies using inverse-variance weighting

        Returns pooled effect, SE, and total N
        """
        # Inverse variance weights
        weights = 1 / (data['se'] ** 2)

        # Pooled effect
        pooled_effect = np.sum(data['effect'] * weights) / np.sum(weights)

        # Pooled SE
        pooled_se = np.sqrt(1 / np.sum(weights))

        # Total N
        total_n = data['n'].sum()

        return {
            'effect': pooled_effect,
            'se': pooled_se,
            'n': total_n,
            'n_studies': len(data)
        }

    def calculate_discordance(self) -> Tuple[float, str]:
        """
        Calculate Discordance Index (DI)

        The DI quantifies how much observational and RCT estimates differ,
        accounting for sampling uncertainty.

        Formula: DI = |Effect_obs - Effect_rct| / sqrt(SE_obs² + SE_rct²)

        Interpretation (ROC-Optimized Thresholds):
        - DI < 1.5: Grade A (Estimates agree - can trust pooled evidence)
        - 1.5 <= DI < 2.5: Grade B (Moderate conflict - trust RCTs)
        - DI >= 2.5: Grade C (Severe conflict - await new trials)

        Note: Thresholds optimized using ROC analysis on 15 medical reversal cases
        (AUC=0.900, 90% sensitivity, 80% specificity at DI=2.43)

        Returns
        -------
        di : float
            Discordance Index value
        grade : str
            Evidence grade (A, B, or C)
        """
        diff = abs(self.obs_pooled['effect'] - self.rct_pooled['effect'])
        combined_se = np.sqrt(self.obs_pooled['se']**2 + self.rct_pooled['se']**2)

        di = diff / combined_se

        # Grade assignment (ROC-optimized thresholds)
        if di < 1.5:
            grade = "Grade A (Trust Pooled)"
        elif di < 2.5:
            grade = "Grade B (Trust RCTs)"
        else:
            grade = "Grade C (Conflict - Await New Trials)"

        return di, grade

    def calculate_confounding_score(self) -> Tuple[float, Optional[float]]:
        """
        Calculate E-Value (Confounding Score)

        The E-Value quantifies the minimum strength of association that
        unmeasured confounding would need to have with both the treatment
        and outcome to explain away the observed effect.

        Based on VanderWeele & Ding (2017).

        Interpretation:
        - E-Value < 1.5: Weak confounding (e.g., frailty) can explain result
        - E-Value 1.5-2.0: Moderate confounding needed
        - E-Value > 2.0: Strong confounding needed

        Returns
        -------
        e_value_point : float
            E-value for point estimate
        e_value_lower : float or None
            E-value for lower confidence limit
        """
        # Get observational estimate on original scale
        if self.effect_type in ['log_hr', 'log_or', 'log_rr']:
            hr_obs = np.exp(self.obs_pooled['effect'])
            hr_lower = np.exp(self.obs_pooled['effect'] - 1.96 * self.obs_pooled['se'])
            hr_upper = np.exp(self.obs_pooled['effect'] + 1.96 * self.obs_pooled['se'])
        else:
            raise NotImplementedError(f"E-value not implemented for {self.effect_type}")

        # Calculate E-value for HR/OR/RR
        # Formula: E = RR + sqrt(RR * (RR - 1))  [for protective effects]
        # For harmful effects (RR > 1): E = RR + sqrt(RR * (RR - 1))
        # For protective effects (RR < 1): E = 1/RR + sqrt(1/RR * (1/RR - 1))

        def e_value_formula(rr):
            """Calculate E-value for given RR"""
            if rr >= 1:
                return rr + np.sqrt(rr * (rr - 1))
            else:
                rr_inv = 1 / rr
                return rr_inv + np.sqrt(rr_inv * (rr_inv - 1))

        e_value_point = e_value_formula(hr_obs)

        # E-value for lower CI (closer to null)
        if hr_obs < 1:
            # Protective effect - use upper CI (closer to 1)
            e_value_lower = e_value_formula(hr_upper) if hr_upper < 1 else None
        else:
            # Harmful effect - use lower CI
            e_value_lower = e_value_formula(hr_lower) if hr_lower > 1 else None

        return e_value_point, e_value_lower

    def calculate_inflation(self, sigma: Optional[float] = None) -> Tuple[float, int, float]:
        """
        Calculate Information Inflation Factor

        Uses variance-based approximation for Effective Sample Size (ESS).
        For full Bayesian ESS calculation, use BayesianESSCalculator.

        The inflation factor shows how much the "big data" sample size
        is inflated due to heterogeneity and bias.

        Parameters
        ----------
        sigma : float, optional
            Reference variance for effect size. If None, uses self.sigma_ref.

        Returns
        -------
        inflation_factor : float
            Nominal N / Effective N
        nominal_n : int
            Total observational sample size
        effective_n : float
            Bayesian effective sample size
        """
        if sigma is None:
            sigma = self.sigma_ref

        nominal_n = self.obs_pooled['n']

        # Variance-based ESS approximation
        # ESS ≈ (sigma / SE)²
        effective_n = (sigma / self.obs_pooled['se']) ** 2

        # Calculate heterogeneity adjustment
        # If we have multiple studies, adjust for between-study variance
        if self.obs_pooled['n_studies'] > 1:
            # Estimate tau² from data
            q_stat = self._calculate_q_statistic(self.obs_data)
            tau_sq = max(0, (q_stat - (self.obs_pooled['n_studies'] - 1)) /
                         np.sum(1 / self.obs_data['se']**2))

            # Adjust ESS for heterogeneity
            # ESS_adj = ESS / (1 + tau²/sigma²)
            heterogeneity_penalty = 1 + tau_sq / (sigma ** 2)
            effective_n = effective_n / heterogeneity_penalty

        inflation_factor = nominal_n / effective_n

        return inflation_factor, nominal_n, effective_n

    def _calculate_q_statistic(self, data: pd.DataFrame) -> float:
        """Calculate Cochran's Q statistic for heterogeneity"""
        pooled = self._pool_studies(data)
        weights = 1 / (data['se'] ** 2)
        q = np.sum(weights * (data['effect'] - pooled['effect']) ** 2)
        return q

    def analyze(self, use_bayesian_ess: bool = False) -> ForensicResults:
        """
        Run complete forensic analysis

        Parameters
        ----------
        use_bayesian_ess : bool
            If True, uses full Bayesian ESS calculation (requires PyMC)
            If False, uses variance-based approximation (faster)

        Returns
        -------
        results : ForensicResults
            Complete forensic analysis results
        """
        # Calculate all three metrics
        di, grade = self.calculate_discordance()
        e_value_point, e_value_lower = self.calculate_confounding_score()

        if use_bayesian_ess:
            # Use full Bayesian calculation
            try:
                from .bayesian_ess import BayesianESSCalculator
                ess_calc = BayesianESSCalculator(self.obs_data)
                inflation_factor, nominal_n, effective_n = ess_calc.calculate()
            except ImportError:
                warnings.warn("PyMC not available. Using variance-based ESS approximation.")
                inflation_factor, nominal_n, effective_n = self.calculate_inflation()
        else:
            # Use variance-based approximation
            inflation_factor, nominal_n, effective_n = self.calculate_inflation()

        # Generate interpretation
        interpretation = self._generate_interpretation(
            di, e_value_point, inflation_factor
        )

        return ForensicResults(
            discordance_index=di,
            e_value_point=e_value_point,
            e_value_lower=e_value_lower,
            inflation_factor=inflation_factor,
            nominal_n=nominal_n,
            effective_n=effective_n,
            evidence_grade=grade,
            interpretation=interpretation
        )

    def _generate_interpretation(
        self,
        di: float,
        e_value: float,
        inflation: float
    ) -> Dict[str, str]:
        """Generate clinical interpretation of results"""
        interp = {}

        # Discordance
        if di < 1.0:
            interp['Discordance'] = "Low conflict - observational and RCT estimates agree"
        elif di < 2.0:
            interp['Discordance'] = "Moderate conflict - prefer RCT evidence"
        else:
            interp['Discordance'] = "Severe conflict - observational evidence likely biased"

        # Confounding
        if e_value < 1.5:
            interp['Confounding'] = "Weak confounding (e.g., frailty, health user bias) can fully explain the observational benefit"
        elif e_value < 2.0:
            interp['Confounding'] = "Moderate unmeasured confounding needed to explain away effect"
        else:
            interp['Confounding'] = "Strong unmeasured confounding would be needed"

        # Inflation
        if inflation > 100:
            interp['Inflation'] = f"Massive false precision ({inflation:.0f}x) - 'big data' is not high-quality data"
        elif inflation > 50:
            interp['Inflation'] = f"Substantial inflation ({inflation:.0f}x) - heterogeneity reduces information"
        elif inflation > 10:
            interp['Inflation'] = f"Moderate inflation ({inflation:.0f}x) - some precision loss"
        else:
            interp['Inflation'] = "Minimal inflation - data relatively homogeneous"

        # Overall recommendation
        if di >= 2.0 and e_value < 1.5:
            interp['Recommendation'] = "HIGH RISK OF BIAS: Do not trust observational evidence. Await adequately powered RCTs."
        elif di >= 1.0 and e_value < 2.0:
            interp['Recommendation'] = "MODERATE RISK OF BIAS: Observational evidence should be downgraded. Prefer RCT estimates."
        elif inflation > 100:
            interp['Recommendation'] = "FALSE PRECISION WARNING: Large sample size does not compensate for bias. Exercise caution."
        else:
            interp['Recommendation'] = "LOW RISK OF BIAS: Observational and RCT evidence reasonably concordant."

        return interp


# Convenience functions for standalone use
def calculate_discordance_index(
    obs_effect: float,
    obs_se: float,
    rct_effect: float,
    rct_se: float
) -> Tuple[float, str]:
    """
    Calculate Discordance Index for single pooled estimates

    Parameters
    ----------
    obs_effect : float
        Pooled observational effect (log scale)
    obs_se : float
        Standard error of observational effect
    rct_effect : float
        Pooled RCT effect (log scale)
    rct_se : float
        Standard error of RCT effect

    Returns
    -------
    di : float
        Discordance Index
    grade : str
        Evidence grade
    """
    diff = abs(obs_effect - rct_effect)
    combined_se = np.sqrt(obs_se**2 + rct_se**2)
    di = diff / combined_se

    if di < 1.5:
        grade = "Grade A"
    elif di < 2.5:
        grade = "Grade B"
    else:
        grade = "Grade C"

    return di, grade


def calculate_e_value(
    hr: float,
    hr_lower: Optional[float] = None,
    protective: bool = True
) -> Tuple[float, Optional[float]]:
    """
    Calculate E-Value for hazard ratio

    Parameters
    ----------
    hr : float
        Hazard ratio (NOT log-transformed)
    hr_lower : float, optional
        Lower 95% CI for HR
    protective : bool
        True if HR < 1 (protective effect)

    Returns
    -------
    e_value_point : float
        E-value for point estimate
    e_value_lower : float or None
        E-value for lower CI
    """
    def e_formula(rr):
        if rr >= 1:
            return rr + np.sqrt(rr * (rr - 1))
        else:
            rr_inv = 1 / rr
            return rr_inv + np.sqrt(rr_inv * (rr_inv - 1))

    e_value_point = e_formula(hr)
    e_value_lower = e_formula(hr_lower) if hr_lower is not None else None

    return e_value_point, e_value_lower


def calculate_inflation_factor(
    effect_sizes: np.ndarray,
    standard_errors: np.ndarray,
    sample_sizes: np.ndarray,
    sigma: float = 2.0
) -> Tuple[float, float]:
    """
    Calculate information inflation factor

    Parameters
    ----------
    effect_sizes : array
        Study-level effect sizes (log scale)
    standard_errors : array
        Study-level standard errors
    sample_sizes : array
        Study-level sample sizes
    sigma : float
        Reference variance

    Returns
    -------
    inflation_factor : float
    effective_n : float
    """
    # Pool studies
    weights = 1 / (standard_errors ** 2)
    pooled_se = np.sqrt(1 / np.sum(weights))

    # Calculate ESS
    effective_n = (sigma / pooled_se) ** 2

    # Heterogeneity adjustment
    if len(effect_sizes) > 1:
        pooled_effect = np.sum(effect_sizes * weights) / np.sum(weights)
        q = np.sum(weights * (effect_sizes - pooled_effect) ** 2)
        tau_sq = max(0, (q - (len(effect_sizes) - 1)) / np.sum(weights))
        heterogeneity_penalty = 1 + tau_sq / (sigma ** 2)
        effective_n = effective_n / heterogeneity_penalty

    nominal_n = np.sum(sample_sizes)
    inflation_factor = nominal_n / effective_n

    return inflation_factor, effective_n
