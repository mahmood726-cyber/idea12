"""
Advanced Bayesian Network Meta-Analysis models.

This module implements state-of-the-art Bayesian methods for NMA:
- Horseshoe and Regularized Horseshoe priors for sparse covariate selection
- Robust models with Student-t likelihoods
- Treatment-specific heterogeneity models
- Posterior predictive checks
- Advanced model diagnostics

References:
    - Carvalho et al. (2010). The horseshoe estimator for sparse signals. Biometrika.
    - Piironen & Vehtari (2017). Sparsity information and regularization in the horseshoe. ECML.
    - Gelman et al. (2014). Understanding predictive information criteria for Bayesian models. Statistics and Computing.
"""

import numpy as np
import pandas as pd
import pymc as pm
import pytensor.tensor as pt
import arviz as az
from typing import Optional, Dict, List, Union, Tuple
from dataclasses import dataclass
from scipy import stats

from ..core.data_structure import NMAData
from ..core.network import TreatmentNetwork
from .bayesian_nma import BayesianNMAResults


@dataclass
class AdvancedBayesianResults(BayesianNMAResults):
    """Extended results for advanced Bayesian models.

    Attributes:
        loo: Leave-one-out cross-validation results
        posterior_predictive: Posterior predictive samples
        prior_predictive: Prior predictive samples
        divergences: Number of divergent transitions
        shrinkage_diagnostics: Diagnostics for shrinkage priors
    """
    loo: Optional[az.ELPDData] = None
    posterior_predictive: Optional[az.InferenceData] = None
    prior_predictive: Optional[az.InferenceData] = None
    divergences: Optional[int] = None
    shrinkage_diagnostics: Optional[pd.DataFrame] = None


class HorseshoeMetaRegression:
    """Network Meta-Regression with Horseshoe Prior for Sparse Covariate Selection.

    The horseshoe prior is a continuous shrinkage prior that provides:
    - Strong shrinkage for noise covariates (to exactly zero)
    - Minimal shrinkage for true signals
    - Automatic selection without cross-validation
    - Superior performance to LASSO in Bayesian settings

    Model specification:
        y_ik ~ Normal(mu_ik, se_ik^2)
        mu_ik = d[t_ik] - d[t_i1] + X_i * beta
        beta_p ~ Normal(0, tau_p * tau_global)  # Horseshoe
        tau_p ~ HalfCauchy(0, 1)  # Local shrinkage
        tau_global ~ HalfCauchy(0, scale_global)  # Global shrinkage

    For Regularized Horseshoe (recommended):
        lambda_tilde_p ~ HalfCauchy(0, 1)
        c^2 ~ InverseGamma(slab_df/2, slab_df*slab_scale^2/2)
        tau_p = lambda_tilde_p * sqrt(c^2 / (c^2 + tau_global^2 * lambda_tilde_p^2))

    References:
        Carvalho et al. (2010). The horseshoe estimator. Biometrika, 97(2), 465-480.
        Piironen & Vehtari (2017). Sparsity information and regularization. ECML.
    """

    def __init__(self,
                 data: NMAData,
                 covariates: List[str],
                 reference_treatment: Optional[str] = None,
                 regularized: bool = True,
                 prior_sd_d: float = 1.5,
                 prior_sd_tau: float = 0.5,
                 slab_scale: float = 2.0,
                 slab_df: float = 4.0):
        """Initialize Horseshoe meta-regression model.

        Args:
            data: NMAData object with study data
            covariates: List of covariate names
            reference_treatment: Reference treatment
            regularized: Use regularized horseshoe (recommended)
            prior_sd_d: SD for treatment effect priors
            prior_sd_tau: Scale for heterogeneity prior
            slab_scale: Scale for regularized horseshoe slab
            slab_df: Degrees of freedom for slab
        """
        self.data = data
        self.covariates = covariates
        self.network = TreatmentNetwork(data)
        self.regularized = regularized
        self.prior_sd_d = prior_sd_d
        self.prior_sd_tau = prior_sd_tau
        self.slab_scale = slab_scale
        self.slab_df = slab_df

        if reference_treatment:
            self.data.reference_treatment = reference_treatment

        self.model = None
        self.trace = None

    def _calculate_expected_sparsity(self, n_covariates: int,
                                     expected_nonzero: int) -> float:
        """Calculate global shrinkage scale based on expected sparsity.

        Args:
            n_covariates: Total number of covariates
            expected_nonzero: Expected number of non-zero coefficients

        Returns:
            Scale parameter for global shrinkage
        """
        p = n_covariates
        p0 = expected_nonzero
        # Piironen & Vehtari (2017) recommendation
        scale_global = p0 / (p - p0) / np.sqrt(len(self.data.studies))
        return scale_global

    def build_model(self,
                    expected_nonzero: Optional[int] = None,
                    center_covariates: bool = True) -> pm.Model:
        """Build horseshoe meta-regression model.

        Args:
            expected_nonzero: Expected number of truly active covariates
            center_covariates: Center covariates at network mean

        Returns:
            PyMC model object
        """
        # Prepare data
        data_dict = self._prepare_data(center_covariates)

        n_treatments = data_dict['n_treatments']
        n_obs = data_dict['n_obs']
        n_cov = len(self.covariates)

        # Calculate scale_global
        if expected_nonzero is None:
            expected_nonzero = max(1, n_cov // 3)  # Default: expect 1/3 active
        scale_global = self._calculate_expected_sparsity(n_cov, expected_nonzero)

        with pm.Model() as model:
            # Data
            y_obs = pm.Data('y', data_dict['y'])
            se_obs = pm.Data('se', data_dict['se'])
            X = pm.Data('X', data_dict['X'])
            t1 = pm.Data('t1', data_dict['treatment_1'])
            t2 = pm.Data('t2', data_dict['treatment_2'])

            # Treatment effects (basic parameters)
            d = pm.Normal('d', mu=0, sigma=self.prior_sd_d,
                         shape=n_treatments)
            d_fixed = pm.Deterministic('d_fixed',
                                      pt.set_subtensor(d[data_dict['ref_idx']], 0))

            # Heterogeneity
            tau = pm.HalfNormal('tau', sigma=self.prior_sd_tau)

            # Horseshoe prior for regression coefficients
            # Global shrinkage
            tau_global = pm.HalfCauchy('tau_global', beta=scale_global)

            if self.regularized:
                # Regularized horseshoe (Piironen & Vehtari 2017)
                # Local shrinkage parameters
                lambda_tilde = pm.HalfCauchy('lambda_tilde', beta=1, shape=n_cov)

                # Slab regularization
                c_squared = pm.InverseGamma('c_squared',
                                           alpha=self.slab_df/2,
                                           beta=self.slab_df * self.slab_scale**2 / 2)

                # Regularized local shrinkage
                lambda_reg = pm.Deterministic('lambda_reg',
                    lambda_tilde * pt.sqrt(c_squared /
                    (c_squared + tau_global**2 * lambda_tilde**2)))

                # Regression coefficients
                beta_raw = pm.Normal('beta_raw', mu=0, sigma=1, shape=n_cov)
                beta = pm.Deterministic('beta', beta_raw * lambda_reg * tau_global)

            else:
                # Standard horseshoe
                lambda_local = pm.HalfCauchy('lambda_local', beta=1, shape=n_cov)
                beta_raw = pm.Normal('beta_raw', mu=0, sigma=1, shape=n_cov)
                beta = pm.Deterministic('beta', beta_raw * lambda_local * tau_global)

            # Linear predictor
            treatment_contrast = d_fixed[t2] - d_fixed[t1]
            regression_effect = pm.math.dot(X, beta)
            mu = treatment_contrast + regression_effect

            # Likelihood (accounting for random effects)
            sigma_total = pt.sqrt(se_obs**2 + tau**2)
            y_like = pm.Normal('y_like', mu=mu, sigma=sigma_total, observed=y_obs)

            # Store model components
            model.add_coord('treatment', data_dict['treatment_names'])
            model.add_coord('covariate', self.covariates)

        self.model = model
        return model

    def _prepare_data(self, center_covariates: bool = True) -> Dict:
        """Prepare data for horseshoe model."""
        studies = []
        y = []
        se = []
        treatment_1 = []
        treatment_2 = []
        X_list = []

        # Treatment indexing
        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}
        n_treatments = len(self.data.treatments)
        ref_idx = treatment_idx[self.data.reference_treatment]

        # Collect covariate values for centering
        if center_covariates:
            cov_values = {cov: [] for cov in self.covariates}
            for study in self.data.studies:
                if hasattr(study, 'covariates') and study.covariates:
                    for cov in self.covariates:
                        if cov in study.covariates:
                            cov_values[cov].append(study.covariates[cov])

            cov_means = {cov: np.mean(vals) if vals else 0
                        for cov, vals in cov_values.items()}
        else:
            cov_means = {cov: 0 for cov in self.covariates}

        # Prepare contrast data
        for study in self.data.studies:
            if study.effects is None or study.se is None:
                continue

            # Get covariates for this study
            X_study = []
            for cov in self.covariates:
                val = 0
                if hasattr(study, 'covariates') and study.covariates:
                    val = study.covariates.get(cov, cov_means[cov])
                X_study.append(val - cov_means[cov])

            # Create contrasts
            for k in range(1, study.n_arms):
                studies.append(study.study_id)
                y.append(study.effects[k-1])
                se.append(study.se[k-1])
                treatment_1.append(treatment_idx[study.treatments[0]])
                treatment_2.append(treatment_idx[study.treatments[k]])
                X_list.append(X_study)

        return {
            'n_obs': len(y),
            'n_treatments': n_treatments,
            'y': np.array(y),
            'se': np.array(se),
            'X': np.array(X_list),
            'treatment_1': np.array(treatment_1, dtype=int),
            'treatment_2': np.array(treatment_2, dtype=int),
            'ref_idx': ref_idx,
            'treatment_names': self.data.treatments
        }

    def fit(self,
            draws: int = 2000,
            tune: int = 1000,
            chains: int = 4,
            target_accept: float = 0.95,
            **kwargs) -> AdvancedBayesianResults:
        """Fit horseshoe meta-regression model.

        Args:
            draws: Number of posterior samples per chain
            tune: Number of tuning steps
            chains: Number of MCMC chains
            target_accept: Target acceptance rate (higher for complex models)
            **kwargs: Additional arguments for pm.sample()

        Returns:
            AdvancedBayesianResults object
        """
        if self.model is None:
            self.build_model()

        with self.model:
            # Sample
            trace = pm.sample(
                draws=draws,
                tune=tune,
                chains=chains,
                target_accept=target_accept,
                return_inferencedata=True,
                **kwargs
            )

            # Posterior predictive samples
            post_pred = pm.sample_posterior_predictive(trace)

            # Compute LOO-CV
            loo = az.loo(trace, pointwise=True)

            # Check convergence
            convergence = az.summary(trace, var_names=['d', 'tau', 'beta'])

            # Extract treatment effects
            treatment_effects = self._extract_treatment_effects(trace)

            # Shrinkage diagnostics
            shrinkage_diag = self._compute_shrinkage_diagnostics(trace)

            # Check for divergences
            divergences = trace.sample_stats.diverging.sum().item()

            if divergences > 0:
                print(f"Warning: {divergences} divergent transitions detected.")
                print("Consider increasing target_accept or reparameterizing.")

        results = AdvancedBayesianResults(
            trace=trace,
            model=self.model,
            treatment_effects=treatment_effects,
            loo=loo,
            posterior_predictive=post_pred,
            convergence_diagnostics=convergence,
            divergences=divergences,
            shrinkage_diagnostics=shrinkage_diag
        )

        self.trace = trace
        return results

    def _extract_treatment_effects(self, trace: az.InferenceData) -> pd.DataFrame:
        """Extract summary of treatment effects."""
        summary = az.summary(trace, var_names=['d_fixed'])
        summary.index = self.data.treatments
        return summary

    def _compute_shrinkage_diagnostics(self, trace: az.InferenceData) -> pd.DataFrame:
        """Compute diagnostics for shrinkage performance.

        Returns DataFrame with:
        - Effective number of parameters
        - Posterior inclusion probabilities
        - Shrinkage factors
        """
        beta_samples = trace.posterior['beta'].values
        # Flatten chains and draws
        beta_flat = beta_samples.reshape(-1, beta_samples.shape[-1])

        diagnostics = []
        for i, cov in enumerate(self.covariates):
            beta_i = beta_flat[:, i]

            # Posterior inclusion probability (|beta| > threshold)
            threshold = 0.01  # Practical significance threshold
            pip = np.mean(np.abs(beta_i) > threshold)

            # Posterior mean and credible interval
            mean_beta = np.mean(beta_i)
            ci_lower, ci_upper = np.percentile(beta_i, [2.5, 97.5])

            # Effective shrinkage
            if self.regularized:
                lambda_reg = trace.posterior['lambda_reg'].values.reshape(-1, len(self.covariates))[:, i]
                tau_global = trace.posterior['tau_global'].values.flatten()
                shrinkage_factor = np.mean(lambda_reg * tau_global)
            else:
                lambda_local = trace.posterior['lambda_local'].values.reshape(-1, len(self.covariates))[:, i]
                tau_global = trace.posterior['tau_global'].values.flatten()
                shrinkage_factor = np.mean(lambda_local * tau_global)

            diagnostics.append({
                'covariate': cov,
                'posterior_mean': mean_beta,
                'ci_lower': ci_lower,
                'ci_upper': ci_upper,
                'inclusion_prob': pip,
                'shrinkage_scale': shrinkage_factor,
                'selected': pip > 0.5  # Select if PIP > 0.5
            })

        return pd.DataFrame(diagnostics)

    def posterior_predictive_check(self,
                                   test_statistic: str = 'mean') -> Dict[str, float]:
        """Perform posterior predictive check.

        Args:
            test_statistic: Statistic to compute ('mean', 'variance', 'min', 'max')

        Returns:
            Dictionary with p-value and test statistic
        """
        if self.trace is None:
            raise ValueError("Model must be fit before running predictive checks")

        # Observed data
        y_obs = self.model['y'].get_value()

        # Posterior predictive samples
        y_rep = self.trace.posterior_predictive['y_like'].values

        # Compute test statistic
        if test_statistic == 'mean':
            T_obs = np.mean(y_obs)
            T_rep = np.mean(y_rep, axis=(0, 1, 2))
        elif test_statistic == 'variance':
            T_obs = np.var(y_obs)
            T_rep = np.var(y_rep, axis=(0, 1, 2))
        elif test_statistic == 'min':
            T_obs = np.min(y_obs)
            T_rep = np.min(y_rep, axis=(0, 1, 2))
        elif test_statistic == 'max':
            T_obs = np.max(y_obs)
            T_rep = np.max(y_rep, axis=(0, 1, 2))
        else:
            raise ValueError(f"Unknown test statistic: {test_statistic}")

        # Bayesian p-value
        p_value = np.mean(T_rep >= T_obs)

        return {
            'test_statistic': test_statistic,
            'observed': T_obs,
            'posterior_mean': np.mean(T_rep),
            'p_value': p_value,
            'extreme': p_value < 0.025 or p_value > 0.975
        }


class RobustNMA:
    """Robust Network Meta-Analysis with Student-t Likelihood.

    Uses Student-t distribution instead of Normal for outlier resistance.
    The degrees of freedom parameter controls tail thickness:
    - nu = 3-5: Heavy tails, robust to outliers
    - nu = 30+: Approximately normal
    - nu estimated from data (recommended)

    Model:
        y_ik ~ StudentT(nu, mu_ik, sigma_ik)
        mu_ik = d[t_ik] - d[t_i1]
        sigma_ik = se_ik (fixed)
        nu ~ Gamma(2, 0.1)  # Weakly informative, favors nu ~ 4-10

    References:
        Geweke (1993). Bayesian treatment of the independent Student-t linear model.
        Journal of Applied Econometrics.
    """

    def __init__(self,
                 data: NMAData,
                 reference_treatment: Optional[str] = None,
                 prior_sd_d: float = 1.5,
                 prior_sd_tau: float = 0.5,
                 estimate_nu: bool = True):
        """Initialize robust NMA model.

        Args:
            data: NMAData object
            reference_treatment: Reference treatment
            prior_sd_d: SD for treatment effect priors
            prior_sd_tau: Scale for heterogeneity prior
            estimate_nu: Estimate degrees of freedom (True) or fix nu=4
        """
        self.data = data
        self.network = TreatmentNetwork(data)
        self.prior_sd_d = prior_sd_d
        self.prior_sd_tau = prior_sd_tau
        self.estimate_nu = estimate_nu

        if reference_treatment:
            self.data.reference_treatment = reference_treatment

        self.model = None
        self.trace = None

    def build_model(self) -> pm.Model:
        """Build robust NMA model with Student-t likelihood."""
        data_dict = self._prepare_data()

        n_treatments = data_dict['n_treatments']
        n_obs = data_dict['n_obs']

        with pm.Model() as model:
            # Data
            y_obs = pm.Data('y', data_dict['y'])
            se_obs = pm.Data('se', data_dict['se'])
            t1 = pm.Data('t1', data_dict['treatment_1'])
            t2 = pm.Data('t2', data_dict['treatment_2'])

            # Treatment effects
            d = pm.Normal('d', mu=0, sigma=self.prior_sd_d, shape=n_treatments)
            d_fixed = pm.Deterministic('d_fixed',
                                      pt.set_subtensor(d[data_dict['ref_idx']], 0))

            # Heterogeneity
            tau = pm.HalfNormal('tau', sigma=self.prior_sd_tau)

            # Degrees of freedom for Student-t
            if self.estimate_nu:
                # Exponential prior on 1/nu gives reasonable values
                nu = pm.Gamma('nu', alpha=2, beta=0.1)
            else:
                nu = 4  # Fixed at 4 (moderately heavy tails)

            # Linear predictor
            mu = d_fixed[t2] - d_fixed[t1]

            # Student-t likelihood (more robust to outliers)
            sigma_total = pt.sqrt(se_obs**2 + tau**2)

            # StudentT with estimated scale
            y_like = pm.StudentT('y_like', nu=nu, mu=mu,
                                sigma=sigma_total, observed=y_obs)

            model.add_coord('treatment', data_dict['treatment_names'])

        self.model = model
        return model

    def _prepare_data(self) -> Dict:
        """Prepare data for robust model."""
        y = []
        se = []
        treatment_1 = []
        treatment_2 = []

        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}
        n_treatments = len(self.data.treatments)
        ref_idx = treatment_idx[self.data.reference_treatment]

        for study in self.data.studies:
            if study.effects is None or study.se is None:
                continue

            for k in range(1, study.n_arms):
                y.append(study.effects[k-1])
                se.append(study.se[k-1])
                treatment_1.append(treatment_idx[study.treatments[0]])
                treatment_2.append(treatment_idx[study.treatments[k]])

        return {
            'n_obs': len(y),
            'n_treatments': n_treatments,
            'y': np.array(y),
            'se': np.array(se),
            'treatment_1': np.array(treatment_1, dtype=int),
            'treatment_2': np.array(treatment_2, dtype=int),
            'ref_idx': ref_idx,
            'treatment_names': self.data.treatments
        }

    def fit(self,
            draws: int = 2000,
            tune: int = 1000,
            chains: int = 4,
            **kwargs) -> AdvancedBayesianResults:
        """Fit robust NMA model."""
        if self.model is None:
            self.build_model()

        with self.model:
            trace = pm.sample(
                draws=draws,
                tune=tune,
                chains=chains,
                return_inferencedata=True,
                **kwargs
            )

            # Posterior predictive
            post_pred = pm.sample_posterior_predictive(trace)

            # LOO-CV
            loo = az.loo(trace, pointwise=True)

            # Convergence diagnostics
            convergence = az.summary(trace)

            # Treatment effects
            treatment_effects = az.summary(trace, var_names=['d_fixed'])
            treatment_effects.index = self.data.treatments

            # Divergences
            divergences = trace.sample_stats.diverging.sum().item()

        results = AdvancedBayesianResults(
            trace=trace,
            model=self.model,
            treatment_effects=treatment_effects,
            loo=loo,
            posterior_predictive=post_pred,
            convergence_diagnostics=convergence,
            divergences=divergences
        )

        self.trace = trace
        return results

    def detect_outliers(self, threshold: float = 3.0) -> pd.DataFrame:
        """Detect potential outliers using standardized residuals.

        Args:
            threshold: Threshold for flagging outliers (default: 3 SD)

        Returns:
            DataFrame with potential outliers
        """
        if self.trace is None:
            raise ValueError("Model must be fit first")

        # Get posterior mean predictions
        mu_samples = self.trace.posterior['y_like'].values
        mu_mean = mu_samples.mean(axis=(0, 1))

        # Observed values
        y_obs = self.model['y'].get_value()
        se_obs = self.model['se'].get_value()

        # Standardized residuals
        residuals = (y_obs - mu_mean) / se_obs

        # Flag outliers
        outliers = []
        for i, (resid, y, se) in enumerate(zip(residuals, y_obs, se_obs)):
            if np.abs(resid) > threshold:
                outliers.append({
                    'index': i,
                    'observed': y,
                    'predicted': mu_mean[i],
                    'std_residual': resid,
                    'se': se
                })

        return pd.DataFrame(outliers)
