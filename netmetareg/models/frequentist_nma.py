"""
Frequentist Network Meta-Analysis models.

This module implements frequentist approaches to NMA using:
- Generalized least squares (contrast-based)
- Mixed effects meta-regression
- Multivariate meta-analysis for multi-arm trials
"""

import numpy as np
import pandas as pd
from scipy import stats, optimize
from scipy.linalg import block_diag
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from ..core.data_structure import NMAData
from ..core.network import TreatmentNetwork


@dataclass
class FrequentistNMAResults:
    """Results from frequentist NMA model.

    Attributes:
        treatment_effects: Point estimates and confidence intervals
        vcov: Variance-covariance matrix of treatment effects
        heterogeneity: Heterogeneity statistics (I^2, tau^2, Q)
        residuals: Model residuals
        fitted_values: Fitted values
        aic: Akaike Information Criterion
        bic: Bayesian Information Criterion
    """
    treatment_effects: pd.DataFrame
    vcov: np.ndarray
    heterogeneity: Optional[Dict[str, float]] = None
    residuals: Optional[np.ndarray] = None
    fitted_values: Optional[np.ndarray] = None
    aic: Optional[float] = None
    bic: Optional[float] = None

    def summary(self) -> pd.DataFrame:
        """Get summary of treatment effects."""
        return self.treatment_effects


class FrequentistNMA:
    """Frequentist Network Meta-Analysis.

    Implements contrast-based NMA using generalized least squares (GLS)
    with proper accounting for multi-arm trial correlations.

    Model specification:
        y = X * d + epsilon
        epsilon ~ N(0, V)

    where:
        y = vector of observed contrasts
        X = design matrix (contrasts to treatments)
        d = treatment effects (to be estimated)
        V = variance-covariance matrix (accounts for within- and between-study variance)

    For multi-arm trials, within-study correlations are 0.5.
    """

    def __init__(self,
                 data: NMAData,
                 reference_treatment: Optional[str] = None,
                 random_effects: bool = True,
                 method: str = 'REML'):
        """Initialize frequentist NMA model.

        Args:
            data: NMAData object
            reference_treatment: Reference treatment
            random_effects: Whether to use random effects (vs fixed effects)
            method: Estimation method ('ML' or 'REML')
        """
        self.data = data
        self.network = TreatmentNetwork(data)

        if reference_treatment:
            self.data.reference_treatment = reference_treatment

        self.random_effects = random_effects
        self.method = method

        self.results = None

    def _prepare_data(self) -> Dict:
        """Prepare data for GLS estimation.

        Returns:
            Dictionary with y, X, S matrices
        """
        y_list = []
        X_list = []
        S_list = []  # Within-study variance-covariance matrices

        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}
        n_treatments = len(self.data.treatments)
        ref_idx = treatment_idx[self.data.reference_treatment]

        for study in self.data.studies:
            if study.effects is None or study.se is None:
                continue

            n_arms = study.n_arms
            n_contrasts = n_arms - 1

            # Observed effects (relative to baseline arm)
            y_study = study.effects

            # Design matrix for this study
            X_study = np.zeros((n_contrasts, n_treatments - 1))

            # Variance-covariance matrix
            # For multi-arm trials, correlation = 0.5 between contrasts sharing baseline
            S_study = np.zeros((n_contrasts, n_contrasts))

            for k in range(n_contrasts):
                # Variance
                S_study[k, k] = study.se[k] ** 2

                # Treatment indicator
                t_baseline = treatment_idx[study.treatments[0]]
                t_active = treatment_idx[study.treatments[k + 1]]

                # Map to reduced parameter space (excluding reference)
                if t_active < ref_idx:
                    col_active = t_active
                else:
                    col_active = t_active - 1

                if t_baseline < ref_idx:
                    col_baseline = t_baseline
                else:
                    col_baseline = t_baseline - 1

                # Set design matrix entry
                if t_active != ref_idx:
                    X_study[k, col_active] = 1
                if t_baseline != ref_idx:
                    X_study[k, col_baseline] = -1

                # Covariance with other contrasts in same study
                for j in range(k):
                    # Both share baseline, so correlation = 0.5
                    S_study[k, j] = 0.5 * study.se[k] * study.se[j]
                    S_study[j, k] = S_study[k, j]

            y_list.append(y_study)
            X_list.append(X_study)
            S_list.append(S_study)

        # Stack into full matrices
        y = np.concatenate(y_list)
        X = np.vstack(X_list)
        S = block_diag(*S_list)

        return {
            'y': y,
            'X': X,
            'S': S,
            'n_obs': len(y),
            'n_treatments': n_treatments,
            'treatment_names': self.data.treatments,
            'ref_idx': ref_idx
        }

    def _estimate_tau_squared(self, y: np.ndarray, X: np.ndarray, S: np.ndarray) -> float:
        """Estimate between-study heterogeneity using DerSimonian-Laird method.

        Args:
            y: Outcome vector
            X: Design matrix
            S: Within-study variance-covariance matrix

        Returns:
            Estimated tau^2
        """
        # Fixed effects fit
        S_inv = np.linalg.pinv(S)
        XtSX_inv = np.linalg.pinv(X.T @ S_inv @ X)
        beta_fe = XtSX_inv @ X.T @ S_inv @ y

        # Cochran's Q statistic
        residuals = y - X @ beta_fe
        Q = residuals.T @ S_inv @ residuals

        # Degrees of freedom
        df = y.shape[0] - X.shape[1]

        if df <= 0:
            return 0.0

        # Expected value of Q under null (no heterogeneity)
        # E[Q] = df if no heterogeneity
        # Var component estimator
        C = np.trace(S_inv) - np.trace(X.T @ S_inv @ X @ XtSX_inv)

        tau_sq = max(0, (Q - df) / C)

        return tau_sq

    def fit(self) -> FrequentistNMAResults:
        """Fit the frequentist NMA model.

        Returns:
            FrequentistNMAResults object
        """
        data_dict = self._prepare_data()
        y = data_dict['y']
        X = data_dict['X']
        S = data_dict['S']

        # Estimate heterogeneity
        tau_sq = 0.0
        if self.random_effects:
            tau_sq = self._estimate_tau_squared(y, X, S)

        # Add heterogeneity to variance matrix
        V = S + tau_sq * np.eye(S.shape[0])

        # GLS estimation
        V_inv = np.linalg.pinv(V)
        XtVX = X.T @ V_inv @ X
        XtVX_inv = np.linalg.pinv(XtVX)
        beta = XtVX_inv @ X.T @ V_inv @ y

        # Standard errors
        se = np.sqrt(np.diag(XtVX_inv))

        # Reconstruct full treatment effects (including reference = 0)
        ref_idx = data_dict['ref_idx']
        n_treatments = data_dict['n_treatments']

        d_full = np.zeros(n_treatments)
        se_full = np.zeros(n_treatments)

        # Insert estimates
        for i in range(n_treatments):
            if i == ref_idx:
                d_full[i] = 0
                se_full[i] = 0
            elif i < ref_idx:
                d_full[i] = beta[i]
                se_full[i] = se[i]
            else:
                d_full[i] = beta[i - 1]
                se_full[i] = se[i - 1]

        # Build results DataFrame
        results_list = []
        for i, treatment in enumerate(data_dict['treatment_names']):
            ci_lower = d_full[i] - 1.96 * se_full[i]
            ci_upper = d_full[i] + 1.96 * se_full[i]
            z_score = d_full[i] / se_full[i] if se_full[i] > 0 else 0
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

            results_list.append({
                'treatment': treatment,
                'effect': d_full[i],
                'se': se_full[i],
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'z': z_score,
                'p_value': p_value
            })

        treatment_effects = pd.DataFrame(results_list)

        # Calculate heterogeneity statistics
        heterogeneity = None
        if self.random_effects:
            # Cochran's Q
            fitted = X @ beta
            residuals = y - fitted
            V_inv_fe = np.linalg.pinv(S)
            Q = residuals.T @ V_inv_fe @ residuals
            df = y.shape[0] - X.shape[1]

            # I^2 statistic
            I_sq = max(0, 100 * (Q - df) / Q) if Q > 0 else 0

            # Heterogeneity variance
            tau = np.sqrt(tau_sq)

            # H statistic
            H = np.sqrt(Q / df) if df > 0 else 1

            heterogeneity = {
                'tau_squared': tau_sq,
                'tau': tau,
                'I_squared': I_sq,
                'H': H,
                'Q': Q,
                'Q_df': df,
                'Q_p_value': 1 - stats.chi2.cdf(Q, df) if df > 0 else np.nan
            }

        # Model fit statistics
        fitted_values = X @ beta
        residuals = y - fitted_values

        # Log-likelihood (assuming normality)
        sign, logdet = np.linalg.slogdet(V)
        ll = -0.5 * (len(y) * np.log(2 * np.pi) + logdet + residuals.T @ V_inv @ residuals)

        # AIC and BIC
        n_params = X.shape[1]
        if self.random_effects:
            n_params += 1  # Add tau^2

        aic = -2 * ll + 2 * n_params
        bic = -2 * ll + n_params * np.log(len(y))

        # Create variance-covariance matrix for full parameter vector
        vcov_full = np.zeros((n_treatments, n_treatments))
        for i in range(n_treatments):
            for j in range(n_treatments):
                if i == ref_idx or j == ref_idx:
                    vcov_full[i, j] = 0
                else:
                    i_idx = i if i < ref_idx else i - 1
                    j_idx = j if j < ref_idx else j - 1
                    vcov_full[i, j] = XtVX_inv[i_idx, j_idx]

        self.results = FrequentistNMAResults(
            treatment_effects=treatment_effects,
            vcov=vcov_full,
            heterogeneity=heterogeneity,
            residuals=residuals,
            fitted_values=fitted_values,
            aic=aic,
            bic=bic
        )

        return self.results

    def predict(self,
                treatment_1: str,
                treatment_2: str) -> Dict[str, float]:
        """Predict treatment effect for a specific comparison.

        Args:
            treatment_1: First treatment
            treatment_2: Second treatment

        Returns:
            Dictionary with prediction statistics
        """
        if self.results is None:
            raise ValueError("Model must be fitted before prediction")

        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}
        i1 = treatment_idx[treatment_1]
        i2 = treatment_idx[treatment_2]

        effects = self.results.treatment_effects

        d1 = effects.loc[effects['treatment'] == treatment_1, 'effect'].values[0]
        d2 = effects.loc[effects['treatment'] == treatment_2, 'effect'].values[0]

        # Relative effect
        d_rel = d2 - d1

        # Variance of difference
        var_rel = (self.results.vcov[i1, i1] +
                  self.results.vcov[i2, i2] -
                  2 * self.results.vcov[i1, i2])
        se_rel = np.sqrt(var_rel)

        # Confidence interval
        ci_lower = d_rel - 1.96 * se_rel
        ci_upper = d_rel + 1.96 * se_rel

        # p-value
        z = d_rel / se_rel if se_rel > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))

        return {
            'comparison': f'{treatment_2} vs {treatment_1}',
            'effect': d_rel,
            'se': se_rel,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'z': z,
            'p_value': p_value
        }

    def rank_treatments(self, method: str = 'SUCRA') -> pd.DataFrame:
        """Rank treatments using frequentist analogue of SUCRA.

        Args:
            method: Ranking method ('SUCRA' or 'P-score')

        Returns:
            DataFrame with treatment rankings
        """
        if self.results is None:
            raise ValueError("Model must be fitted before ranking")

        effects = self.results.treatment_effects['effect'].values
        vcov = self.results.vcov

        n_treatments = len(effects)
        rankings = []

        for i in range(n_treatments):
            # Calculate P-score: probability of being better than average
            # P_i = (1/(n-1)) * sum_{j != i} Phi((d_i - d_j) / se_ij)
            p_score = 0
            for j in range(n_treatments):
                if i != j:
                    diff = effects[i] - effects[j]
                    se_diff = np.sqrt(vcov[i, i] + vcov[j, j] - 2 * vcov[i, j])
                    if se_diff > 0:
                        p_score += stats.norm.cdf(diff / se_diff)

            p_score /= (n_treatments - 1)

            rankings.append({
                'treatment': self.data.treatments[i],
                'effect': effects[i],
                'p_score': p_score
            })

        df = pd.DataFrame(rankings)
        df = df.sort_values('p_score', ascending=False)
        df['rank'] = range(1, n_treatments + 1)

        return df
