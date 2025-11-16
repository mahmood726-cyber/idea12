"""
Bayesian Network Meta-Analysis models.

This module implements Bayesian models for NMA using PyMC, including:
- Contrast-based models
- Arm-based models
- Random effects models
- Meta-regression with covariates
- Treatment class effects
"""

import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
from typing import Optional, Dict, List, Union, Tuple
from dataclasses import dataclass

from ..core.data_structure import NMAData
from ..core.network import TreatmentNetwork


@dataclass
class BayesianNMAResults:
    """Results from Bayesian NMA model.

    Attributes:
        trace: Posterior samples (ArviZ InferenceData)
        model: PyMC model object
        treatment_effects: Posterior summaries for treatment effects
        heterogeneity: Between-study standard deviation (tau)
        dic: Deviance Information Criterion
        waic: Widely Applicable Information Criterion
        convergence_diagnostics: Rhat and effective sample size
    """
    trace: az.InferenceData
    model: pm.Model
    treatment_effects: pd.DataFrame
    heterogeneity: Optional[Dict[str, float]] = None
    dic: Optional[float] = None
    waic: Optional[float] = None
    convergence_diagnostics: Optional[pd.DataFrame] = None

    def summary(self) -> pd.DataFrame:
        """Get summary statistics for all parameters."""
        return az.summary(self.trace)

    def plot_trace(self):
        """Create trace plots for MCMC diagnostics."""
        return az.plot_trace(self.trace)

    def plot_forest(self, var_names: Optional[List[str]] = None):
        """Create forest plot of treatment effects."""
        if var_names is None:
            var_names = ['d']
        return az.plot_forest(self.trace, var_names=var_names)


class BayesianNMA:
    """Bayesian Network Meta-Analysis.

    Implements Bayesian hierarchical models for NMA using contrast-based
    parameterization. Supports random effects, meta-regression, and
    multi-arm trials.

    Model specification (contrast-based):
        y_ik ~ Normal(delta_ik, se_ik^2)  # Observed effect in study i, arm k
        delta_i1 = 0                        # Baseline arm
        delta_ik ~ Normal(d[t_ik] - d[t_i1] + X_i * beta[t_ik], tau^2)  # Random effects
        d[1] = 0                            # Reference treatment
        d[k] ~ Normal(0, 100^2)             # Vague priors for treatment effects
        tau ~ HalfNormal(sigma=1)           # Between-study heterogeneity

    With meta-regression:
        delta_ik ~ Normal(d[t_ik] - d[t_i1] + X_i * (beta + gamma[t_ik]), tau^2)
        where gamma[t_ik] are treatment-by-covariate interactions
    """

    def __init__(self,
                 data: NMAData,
                 reference_treatment: Optional[str] = None,
                 random_effects: bool = True,
                 prior_sd_d: float = 100.0,
                 prior_sd_tau: float = 1.0):
        """Initialize Bayesian NMA model.

        Args:
            data: NMAData object containing study data
            reference_treatment: Reference treatment (default: first treatment)
            random_effects: Whether to use random effects model
            prior_sd_d: Standard deviation for treatment effect priors
            prior_sd_tau: Standard deviation for heterogeneity prior
        """
        self.data = data
        self.network = TreatmentNetwork(data)

        if reference_treatment:
            self.data.reference_treatment = reference_treatment

        self.random_effects = random_effects
        self.prior_sd_d = prior_sd_d
        self.prior_sd_tau = prior_sd_tau

        self.model = None
        self.trace = None

    def _prepare_data_contrast_based(self) -> Dict:
        """Prepare data in contrast-based format for PyMC.

        Returns:
            Dictionary with data arrays for model
        """
        studies = []
        y = []
        se = []
        treatment_1 = []
        treatment_2 = []

        # Create treatment index mapping
        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}
        n_treatments = len(self.data.treatments)
        ref_idx = treatment_idx[self.data.reference_treatment]

        for study in self.data.studies:
            if study.effects is None or study.se is None:
                continue

            # For each non-baseline arm
            for k in range(1, study.n_arms):
                studies.append(study.study_id)
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

    def build_model(self,
                   covariates: Optional[List[str]] = None,
                   interactions: bool = False,
                   center_covariates: bool = True) -> pm.Model:
        """Build PyMC model for network meta-analysis.

        Args:
            covariates: List of covariate names to include in meta-regression
            interactions: Whether to include treatment-by-covariate interactions
            center_covariates: Whether to center covariates at network mean

        Returns:
            PyMC model object
        """
        data_dict = self._prepare_data_contrast_based()

        with pm.Model() as model:
            # Data containers
            y_obs = pm.Data('y_obs', data_dict['y'])
            se_obs = pm.Data('se_obs', data_dict['se'])
            t1 = pm.Data('t1', data_dict['treatment_1'])
            t2 = pm.Data('t2', data_dict['treatment_2'])

            # Treatment effects (relative to reference)
            # d[ref] = 0 by construction
            d_raw = pm.Normal('d_raw',
                             mu=0,
                             sigma=self.prior_sd_d,
                             shape=data_dict['n_treatments'] - 1)

            # Insert zero for reference treatment
            d = pm.Deterministic('d',
                                pm.math.concatenate([
                                    d_raw[:data_dict['ref_idx']],
                                    [0],
                                    d_raw[data_dict['ref_idx']:]
                                ]))

            # Basic treatment effect (relative effect for each comparison)
            basic_effect = d[t2] - d[t1]

            # Add meta-regression if covariates specified
            if covariates:
                X, params = self.data.get_covariate_matrix(center=center_covariates)
                X_pm = pm.Data('X', X)

                if interactions:
                    # Treatment-by-covariate interactions
                    # beta shape: (n_covariates, n_treatments)
                    beta = pm.Normal('beta',
                                   mu=0,
                                   sigma=1,
                                   shape=(len(covariates), data_dict['n_treatments']))

                    # Interaction effect for each observation
                    # This is sum over covariates of: X_i[p] * (beta[p, t2] - beta[p, t1])
                    interaction_effect = pm.math.sum(
                        X_pm[:, None] * (beta[:, t2] - beta[:, t1]).T,
                        axis=1
                    )
                    basic_effect = basic_effect + interaction_effect
                else:
                    # Main effects only (no interaction)
                    beta = pm.Normal('beta', mu=0, sigma=1, shape=len(covariates))
                    basic_effect = basic_effect + pm.math.dot(X_pm, beta)

            if self.random_effects:
                # Between-study heterogeneity
                tau = pm.HalfNormal('tau', sigma=self.prior_sd_tau)

                # Random effects for each observation
                delta = pm.Normal('delta',
                                mu=basic_effect,
                                sigma=tau,
                                shape=data_dict['n_obs'])
            else:
                # Fixed effects (no heterogeneity)
                delta = pm.Deterministic('delta', basic_effect)

            # Likelihood
            y_hat = pm.Normal('y_hat',
                            mu=delta,
                            sigma=se_obs,
                            observed=y_obs)

        self.model = model
        return model

    def fit(self,
           draws: int = 2000,
           tune: int = 1000,
           chains: int = 4,
           target_accept: float = 0.95,
           **kwargs) -> BayesianNMAResults:
        """Fit the Bayesian NMA model using MCMC.

        Args:
            draws: Number of posterior samples per chain
            tune: Number of tuning steps
            chains: Number of MCMC chains
            target_accept: Target acceptance rate for NUTS sampler
            **kwargs: Additional arguments passed to pm.sample()

        Returns:
            BayesianNMAResults object
        """
        if self.model is None:
            self.build_model()

        with self.model:
            # Sample from posterior
            self.trace = pm.sample(
                draws=draws,
                tune=tune,
                chains=chains,
                target_accept=target_accept,
                return_inferencedata=True,
                **kwargs
            )

            # Add posterior predictive
            pm.sample_posterior_predictive(
                self.trace,
                extend_inferencedata=True
            )

        # Extract treatment effects
        treatment_effects = self._extract_treatment_effects()

        # Calculate heterogeneity
        heterogeneity = None
        if self.random_effects and 'tau' in self.trace.posterior:
            tau_samples = self.trace.posterior['tau'].values.flatten()
            heterogeneity = {
                'mean': float(np.mean(tau_samples)),
                'median': float(np.median(tau_samples)),
                'sd': float(np.std(tau_samples)),
                'q025': float(np.percentile(tau_samples, 2.5)),
                'q975': float(np.percentile(tau_samples, 97.5))
            }

        # Model comparison criteria
        waic = az.waic(self.trace)

        # Convergence diagnostics
        convergence = az.summary(self.trace, var_names=['d'])

        results = BayesianNMAResults(
            trace=self.trace,
            model=self.model,
            treatment_effects=treatment_effects,
            heterogeneity=heterogeneity,
            waic=waic.elpd_waic,
            convergence_diagnostics=convergence
        )

        return results

    def _extract_treatment_effects(self) -> pd.DataFrame:
        """Extract and summarize treatment effects from posterior.

        Returns:
            DataFrame with treatment effect summaries
        """
        d_samples = self.trace.posterior['d'].values

        # Reshape to (n_samples, n_treatments)
        d_samples = d_samples.reshape(-1, d_samples.shape[-1])

        results = []
        for i, treatment in enumerate(self.data.treatments):
            samples = d_samples[:, i]

            result = {
                'treatment': treatment,
                'mean': np.mean(samples),
                'sd': np.std(samples),
                'median': np.median(samples),
                'q025': np.percentile(samples, 2.5),
                'q975': np.percentile(samples, 97.5),
                'prob_positive': np.mean(samples > 0)
            }
            results.append(result)

        return pd.DataFrame(results)

    def predict(self,
                covariate_values: Optional[Dict[str, float]] = None,
                treatment_pair: Optional[Tuple[str, str]] = None,
                n_samples: int = 1000) -> Dict:
        """Predict treatment effect for new population.

        Args:
            covariate_values: Dictionary of covariate values for target population
            treatment_pair: Tuple of (treatment_1, treatment_2) to compare
            n_samples: Number of posterior samples to use

        Returns:
            Dictionary with prediction summaries
        """
        if self.trace is None:
            raise ValueError("Model must be fitted before prediction")

        # Get posterior samples for d
        d_samples = self.trace.posterior['d'].values
        d_samples = d_samples.reshape(-1, d_samples.shape[-1])

        # Sample subset
        if d_samples.shape[0] > n_samples:
            idx = np.random.choice(d_samples.shape[0], n_samples, replace=False)
            d_samples = d_samples[idx]

        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}

        if treatment_pair:
            t1_idx = treatment_idx[treatment_pair[0]]
            t2_idx = treatment_idx[treatment_pair[1]]
            predictions = d_samples[:, t2_idx] - d_samples[:, t1_idx]
        else:
            # All pairwise comparisons to reference
            ref_idx = treatment_idx[self.data.reference_treatment]
            predictions = d_samples - d_samples[:, ref_idx:ref_idx+1]

        # Add covariate effects if present
        if covariate_values and 'beta' in self.trace.posterior:
            beta_samples = self.trace.posterior['beta'].values
            beta_samples = beta_samples.reshape(-1, beta_samples.shape[-1])

            if beta_samples.shape[0] > n_samples:
                idx = np.random.choice(beta_samples.shape[0], n_samples, replace=False)
                beta_samples = beta_samples[idx]

            # Create covariate vector
            X_new = np.array([covariate_values.get(cov, 0)
                            for cov in self.data.covariate_names])

            # Add regression effect
            reg_effect = beta_samples @ X_new
            if treatment_pair is None:
                predictions += reg_effect[:, None]
            else:
                predictions += reg_effect

        # Summarize predictions
        if treatment_pair:
            summary = {
                'comparison': f"{treatment_pair[0]} vs {treatment_pair[1]}",
                'mean': float(np.mean(predictions)),
                'sd': float(np.std(predictions)),
                'median': float(np.median(predictions)),
                'q025': float(np.percentile(predictions, 2.5)),
                'q975': float(np.percentile(predictions, 97.5)),
                'samples': predictions
            }
        else:
            summary = {}
            for i, treatment in enumerate(self.data.treatments):
                if treatment == self.data.reference_treatment:
                    continue
                samples = predictions[:, i]
                summary[treatment] = {
                    'mean': float(np.mean(samples)),
                    'sd': float(np.std(samples)),
                    'median': float(np.median(samples)),
                    'q025': float(np.percentile(samples, 2.5)),
                    'q975': float(np.percentile(samples, 97.5)),
                    'samples': samples
                }

        return summary

    def calculate_sucra(self) -> pd.DataFrame:
        """Calculate Surface Under Cumulative Ranking (SUCRA) scores.

        SUCRA represents the probability that a treatment is among the best.

        Returns:
            DataFrame with SUCRA scores for each treatment
        """
        if self.trace is None:
            raise ValueError("Model must be fitted before calculating SUCRA")

        # Get posterior samples
        d_samples = self.trace.posterior['d'].values
        d_samples = d_samples.reshape(-1, d_samples.shape[-1])

        n_samples, n_treatments = d_samples.shape

        # For each sample, rank treatments (1 = best = highest d)
        ranks = np.zeros_like(d_samples)
        for i in range(n_samples):
            ranks[i] = n_treatments - np.argsort(np.argsort(d_samples[i]))

        # Calculate SUCRA
        sucra_scores = []
        for i, treatment in enumerate(self.data.treatments):
            # SUCRA = sum of probabilities of being rank 1, 2, ..., n-1
            # divided by (n-1)
            cumulative_prob = 0
            for rank in range(1, n_treatments):
                prob_at_least_rank = np.mean(ranks[:, i] <= rank)
                cumulative_prob += prob_at_least_rank

            sucra = cumulative_prob / (n_treatments - 1)

            sucra_scores.append({
                'treatment': treatment,
                'sucra': sucra,
                'mean_rank': np.mean(ranks[:, i]),
                'median_rank': np.median(ranks[:, i])
            })

        df = pd.DataFrame(sucra_scores)
        return df.sort_values('sucra', ascending=False)
