"""
Simulation utilities for validation and testing.

This module provides functions to generate synthetic network meta-analysis
data with known parameters, allowing validation of estimation methods.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from ..core.data_structure import NMAData, Study


@dataclass
class SimulationParameters:
    """Parameters for generating synthetic NMA data.

    Attributes:
        n_treatments: Number of treatments in network
        n_studies: Number of studies
        true_effects: True treatment effects (relative to reference)
        tau: Between-study standard deviation
        study_sizes: Sample sizes for study arms
        covariate_effects: True covariate effect coefficients
        interactions: True interaction coefficients (if any)
        inconsistency: Inconsistency parameters for specific comparisons
    """
    n_treatments: int
    n_studies: int
    true_effects: np.ndarray
    tau: float = 0.2
    study_sizes: Tuple[int, int] = (100, 100)
    covariate_effects: Optional[Dict[str, float]] = None
    interactions: Optional[Dict[str, np.ndarray]] = None
    inconsistency: Optional[Dict[Tuple[int, int], float]] = None


class NMASimulator:
    """Simulator for network meta-analysis data.

    Generates synthetic NMA datasets with known ground truth for
    validation and testing purposes.
    """

    def __init__(self, params: SimulationParameters, random_state: int = 42):
        """Initialize simulator.

        Args:
            params: Simulation parameters
            random_state: Random seed for reproducibility
        """
        self.params = params
        self.random_state = random_state
        np.random.seed(random_state)

    def generate_network(self,
                        network_type: str = 'complete',
                        prop_multi_arm: float = 0.2) -> NMAData:
        """Generate a synthetic network.

        Args:
            network_type: Type of network ('complete', 'star', 'chain', 'random')
            prop_multi_arm: Proportion of multi-arm studies

        Returns:
            NMAData object with synthetic data
        """
        if network_type == 'complete':
            studies = self._generate_complete_network(prop_multi_arm)
        elif network_type == 'star':
            studies = self._generate_star_network(prop_multi_arm)
        elif network_type == 'chain':
            studies = self._generate_chain_network()
        elif network_type == 'random':
            studies = self._generate_random_network(prop_multi_arm)
        else:
            raise ValueError(f"Unknown network type: {network_type}")

        return NMAData(studies=studies, reference_treatment="T0")

    def _generate_complete_network(self, prop_multi_arm: float) -> List[Study]:
        """Generate complete network (all pairwise comparisons).

        Args:
            prop_multi_arm: Proportion of multi-arm studies

        Returns:
            List of Study objects
        """
        studies = []
        study_id = 0

        # Generate pairwise comparisons
        comparisons = []
        for i in range(self.params.n_treatments):
            for j in range(i + 1, self.params.n_treatments):
                comparisons.append((i, j))

        # Assign studies to comparisons
        n_studies_per_comparison = max(1, self.params.n_studies // len(comparisons))

        for i, j in comparisons:
            for _ in range(n_studies_per_comparison):
                treatments = [f"T{i}", f"T{j}"]
                study = self._generate_study(
                    study_id=f"S{study_id}",
                    treatments=treatments,
                    treatment_indices=[i, j]
                )
                studies.append(study)
                study_id += 1

        # Add some multi-arm studies
        n_multi_arm = int(prop_multi_arm * self.params.n_studies)
        for _ in range(n_multi_arm):
            # Random 3-arm study
            treatment_indices = np.random.choice(
                self.params.n_treatments,
                size=3,
                replace=False
            )
            treatments = [f"T{idx}" for idx in treatment_indices]
            study = self._generate_study(
                study_id=f"S{study_id}",
                treatments=treatments,
                treatment_indices=treatment_indices
            )
            studies.append(study)
            study_id += 1

        return studies[:self.params.n_studies]

    def _generate_star_network(self, prop_multi_arm: float) -> List[Study]:
        """Generate star network (all comparisons to reference).

        Args:
            prop_multi_arm: Proportion of multi-arm studies

        Returns:
            List of Study objects
        """
        studies = []
        study_id = 0

        # Each active treatment compared to reference
        n_per_comparison = self.params.n_studies // (self.params.n_treatments - 1)

        for j in range(1, self.params.n_treatments):
            for _ in range(n_per_comparison):
                treatments = ["T0", f"T{j}"]
                study = self._generate_study(
                    study_id=f"S{study_id}",
                    treatments=treatments,
                    treatment_indices=[0, j]
                )
                studies.append(study)
                study_id += 1

        return studies

    def _generate_chain_network(self) -> List[Study]:
        """Generate chain network (sequential comparisons).

        Returns:
            List of Study objects
        """
        studies = []
        study_id = 0

        # Each adjacent pair
        n_per_comparison = self.params.n_studies // (self.params.n_treatments - 1)

        for i in range(self.params.n_treatments - 1):
            for _ in range(n_per_comparison):
                treatments = [f"T{i}", f"T{i+1}"]
                study = self._generate_study(
                    study_id=f"S{study_id}",
                    treatments=treatments,
                    treatment_indices=[i, i + 1]
                )
                studies.append(study)
                study_id += 1

        return studies

    def _generate_random_network(self, prop_multi_arm: float) -> List[Study]:
        """Generate random network structure.

        Args:
            prop_multi_arm: Proportion of multi-arm studies

        Returns:
            List of Study objects
        """
        studies = []

        for i in range(self.params.n_studies):
            # Randomly decide 2-arm vs 3-arm
            if np.random.random() < prop_multi_arm:
                n_arms = 3
            else:
                n_arms = 2

            # Random treatment selection
            treatment_indices = np.random.choice(
                self.params.n_treatments,
                size=n_arms,
                replace=False
            )
            treatments = [f"T{idx}" for idx in treatment_indices]

            study = self._generate_study(
                study_id=f"S{i}",
                treatments=treatments,
                treatment_indices=treatment_indices
            )
            studies.append(study)

        return studies

    def _generate_study(self,
                       study_id: str,
                       treatments: List[str],
                       treatment_indices: np.ndarray) -> Study:
        """Generate a single study with known parameters.

        Args:
            study_id: Study identifier
            treatments: Treatment names
            treatment_indices: Indices for true effects

        Returns:
            Study object
        """
        n_arms = len(treatments)
        baseline_idx = treatment_indices[0]

        # Generate covariates
        covariates = {}
        if self.params.covariate_effects:
            for cov_name in self.params.covariate_effects.keys():
                # Generate from reasonable range
                if cov_name == 'age':
                    covariates[cov_name] = np.random.normal(50, 10)
                elif cov_name == 'severity':
                    covariates[cov_name] = np.random.normal(25, 5)
                elif cov_name.startswith('prop_'):
                    covariates[cov_name] = np.random.uniform(0.3, 0.7)
                else:
                    covariates[cov_name] = np.random.normal(0, 1)

        # Generate true effects
        effects = []
        se_values = []

        for k in range(1, n_arms):
            active_idx = treatment_indices[k]

            # Basic treatment effect
            true_delta = self.params.true_effects[active_idx] - \
                        self.params.true_effects[baseline_idx]

            # Add covariate effects
            if self.params.covariate_effects:
                for cov_name, beta in self.params.covariate_effects.items():
                    if cov_name in covariates:
                        # Center at mean value
                        mean_val = 50 if cov_name == 'age' else \
                                  25 if cov_name == 'severity' else 0.5
                        true_delta += beta * (covariates[cov_name] - mean_val)

            # Add interactions if specified
            if self.params.interactions:
                for cov_name, gamma_array in self.params.interactions.items():
                    if cov_name in covariates:
                        mean_val = 50 if cov_name == 'age' else \
                                  25 if cov_name == 'severity' else 0.5
                        interaction = (gamma_array[active_idx] - gamma_array[baseline_idx])
                        true_delta += interaction * (covariates[cov_name] - mean_val)

            # Add inconsistency if specified
            if self.params.inconsistency:
                comparison = tuple(sorted([baseline_idx, active_idx]))
                if comparison in self.params.inconsistency:
                    true_delta += self.params.inconsistency[comparison]

            # Add between-study heterogeneity
            true_delta += np.random.normal(0, self.params.tau)

            # Generate observed effect with sampling variance
            n1, n2 = self.params.study_sizes
            se = np.sqrt(1/n1 + 1/n2)  # For log OR

            observed_effect = np.random.normal(true_delta, se)

            effects.append(observed_effect)
            se_values.append(se)

        study = Study(
            study_id=study_id,
            treatments=treatments,
            effects=np.array(effects),
            se=np.array(se_values),
            n=np.array([self.params.study_sizes[0]] * n_arms),
            covariates=covariates
        )

        return study


def run_validation_study(true_params: SimulationParameters,
                         n_simulations: int = 100,
                         method: str = 'bayesian') -> pd.DataFrame:
    """Run validation study comparing estimates to true parameters.

    Args:
        true_params: True parameter values
        n_simulations: Number of simulation replications
        method: Estimation method ('bayesian' or 'frequentist')

    Returns:
        DataFrame with bias, coverage, and MSE statistics
    """
    from ..models.bayesian_nma import BayesianNMA
    from ..models.frequentist_nma import FrequentistNMA

    results = []

    for sim in range(n_simulations):
        # Generate data
        simulator = NMASimulator(true_params, random_state=sim)
        data = simulator.generate_network(network_type='complete')

        try:
            # Fit model
            if method == 'bayesian':
                model = BayesianNMA(data)
                fit_results = model.fit(draws=1000, tune=500, chains=2)
                estimates = fit_results.treatment_effects['mean'].values
                se_estimates = fit_results.treatment_effects['sd'].values
                ci_lower = fit_results.treatment_effects['q025'].values
                ci_upper = fit_results.treatment_effects['q975'].values
            else:
                model = FrequentistNMA(data)
                fit_results = model.fit()
                estimates = fit_results.treatment_effects['effect'].values
                se_estimates = fit_results.treatment_effects['se'].values
                ci_lower = fit_results.treatment_effects['ci_lower'].values
                ci_upper = fit_results.treatment_effects['ci_upper'].values

            # Calculate metrics for each treatment
            for j in range(len(estimates)):
                true_value = true_params.true_effects[j]

                results.append({
                    'simulation': sim,
                    'treatment': j,
                    'true_value': true_value,
                    'estimate': estimates[j],
                    'se': se_estimates[j],
                    'bias': estimates[j] - true_value,
                    'coverage': 1 if ci_lower[j] <= true_value <= ci_upper[j] else 0,
                    'ci_width': ci_upper[j] - ci_lower[j]
                })
        except Exception as e:
            print(f"Simulation {sim} failed: {e}")
            continue

    df = pd.DataFrame(results)

    # Summarize across simulations
    summary = df.groupby('treatment').agg({
        'bias': 'mean',
        'se': 'mean',
        'coverage': 'mean',
        'ci_width': 'mean'
    }).reset_index()

    # Add empirical SE and RMSE
    empirical_se = df.groupby('treatment')['estimate'].std().values
    rmse = np.sqrt(df.groupby('treatment')['bias'].apply(lambda x: (x**2).mean()).values)

    summary['empirical_se'] = empirical_se
    summary['rmse'] = rmse
    summary['true_value'] = true_params.true_effects

    return summary
