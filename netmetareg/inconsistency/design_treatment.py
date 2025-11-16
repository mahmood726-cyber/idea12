"""
Design-by-treatment interaction model for inconsistency detection.

This model tests whether treatment effects vary by study design,
which can indicate inconsistency in the network.
"""

import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
from typing import Optional, Dict, List
from dataclasses import dataclass

from ..core.data_structure import NMAData
from ..core.network import TreatmentNetwork


@dataclass
class DesignTreatmentResults:
    """Results from design-by-treatment interaction analysis.

    Attributes:
        design_effects: Effect estimates by design type
        interaction_parameters: Design-by-treatment interaction estimates
        inconsistency_test: Global test for inconsistency
        trace: Posterior samples
    """
    design_effects: pd.DataFrame
    interaction_parameters: pd.DataFrame
    inconsistency_test: Dict[str, float]
    trace: Optional[az.InferenceData] = None


class DesignTreatmentInteraction:
    """Design-by-treatment interaction model.

    This model extends the standard NMA to include design-specific effects.
    Inconsistency is detected if treatment effects differ significantly
    across designs.

    Model:
        delta_ik = d[t_ik] - d[t_i1] + gamma[design_i, t_ik] + epsilon_ik

    where gamma[design, treatment] represents the design-by-treatment interaction.
    """

    def __init__(self, data: NMAData):
        """Initialize design-by-treatment model.

        Args:
            data: NMAData object with design information
        """
        self.data = data
        self.network = TreatmentNetwork(data)

    def identify_designs(self) -> Dict[str, List[str]]:
        """Identify unique study designs in the network.

        Returns:
            Dictionary mapping design signatures to study IDs
        """
        return self.network.get_study_design_types()

    def fit(self,
           draws: int = 2000,
           tune: int = 1000,
           **kwargs) -> DesignTreatmentResults:
        """Fit design-by-treatment interaction model.

        Args:
            draws: Number of MCMC draws
            tune: Number of tuning steps
            **kwargs: Additional sampler arguments

        Returns:
            DesignTreatmentResults object
        """
        data_dict = self._prepare_data()

        with pm.Model() as model:
            # Basic treatment effects
            n_treatments = data_dict['n_treatments']
            ref_idx = data_dict['ref_idx']

            d_raw = pm.Normal('d_raw', mu=0, sigma=100, shape=n_treatments - 1)
            d = pm.Deterministic('d',
                                pm.math.concatenate([
                                    d_raw[:ref_idx],
                                    [0],
                                    d_raw[ref_idx:]
                                ]))

            # Design-by-treatment interactions
            n_designs = data_dict['n_designs']
            gamma = pm.Normal('gamma',
                            mu=0,
                            sigma=10,
                            shape=(n_designs, n_treatments))

            # Heterogeneity
            tau = pm.HalfNormal('tau', sigma=1)

            # Expected effects
            basic_effects = d[data_dict['t2']] - d[data_dict['t1']]

            # Add design interactions
            design_effects = gamma[data_dict['designs'], data_dict['t2']] - \
                           gamma[data_dict['designs'], data_dict['t1']]

            expected = basic_effects + design_effects

            # Random effects
            delta = pm.Normal('delta',
                            mu=expected,
                            sigma=tau,
                            shape=data_dict['n_obs'])

            # Likelihood
            pm.Normal('y',
                     mu=delta,
                     sigma=data_dict['se'],
                     observed=data_dict['y'])

            # Sample
            trace = pm.sample(
                draws=draws,
                tune=tune,
                return_inferencedata=True,
                **kwargs
            )

        # Extract results
        results = self._extract_results(trace, data_dict)
        results.trace = trace

        return results

    def _prepare_data(self) -> Dict:
        """Prepare data for model fitting.

        Returns:
            Dictionary with data arrays
        """
        # Get unique designs
        design_types = self.identify_designs()
        design_list = sorted(design_types.keys())
        design_idx = {d: i for i, d in enumerate(design_list)}

        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}

        y = []
        se = []
        t1 = []
        t2 = []
        designs = []

        for study in self.data.studies:
            if study.effects is None or study.se is None:
                continue

            # Get design signature
            design_sig = tuple(sorted(study.treatments))
            design_id = design_idx[design_sig]

            for k in range(1, study.n_arms):
                y.append(study.effects[k - 1])
                se.append(study.se[k - 1])
                t1.append(treatment_idx[study.treatments[0]])
                t2.append(treatment_idx[study.treatments[k]])
                designs.append(design_id)

        return {
            'n_obs': len(y),
            'n_treatments': len(self.data.treatments),
            'n_designs': len(design_list),
            'ref_idx': treatment_idx[self.data.reference_treatment],
            'y': np.array(y),
            'se': np.array(se),
            't1': np.array(t1, dtype=int),
            't2': np.array(t2, dtype=int),
            'designs': np.array(designs, dtype=int),
            'design_names': design_list,
            'treatment_names': self.data.treatments
        }

    def _extract_results(self,
                        trace: az.InferenceData,
                        data_dict: Dict) -> DesignTreatmentResults:
        """Extract and summarize results.

        Args:
            trace: Posterior samples
            data_dict: Data dictionary

        Returns:
            DesignTreatmentResults object
        """
        # Extract design effects
        gamma_samples = trace.posterior['gamma'].values
        gamma_samples = gamma_samples.reshape(-1, gamma_samples.shape[-2], gamma_samples.shape[-1])

        # Summarize gamma parameters
        interaction_list = []
        for i, design in enumerate(data_dict['design_names']):
            for j, treatment in enumerate(data_dict['treatment_names']):
                samples = gamma_samples[:, i, j]
                interaction_list.append({
                    'design': str(design),
                    'treatment': treatment,
                    'mean': np.mean(samples),
                    'sd': np.std(samples),
                    'q025': np.percentile(samples, 2.5),
                    'q975': np.percentile(samples, 97.5),
                    'prob_positive': np.mean(samples > 0)
                })

        interactions_df = pd.DataFrame(interaction_list)

        # Summarize by design
        design_effects = []
        for i, design in enumerate(data_dict['design_names']):
            # Average absolute interaction across treatments
            abs_interactions = np.abs(gamma_samples[:, i, :])
            mean_abs_interaction = np.mean(abs_interactions)

            design_effects.append({
                'design': str(design),
                'mean_abs_interaction': mean_abs_interaction,
                'max_interaction': np.max(abs_interactions)
            })

        design_effects_df = pd.DataFrame(design_effects)

        # Global inconsistency test
        # Test if any gamma significantly different from 0
        # Compute probability that max|gamma| > threshold
        max_abs_gamma = np.max(np.abs(gamma_samples), axis=(1, 2))
        prob_inconsistency = np.mean(max_abs_gamma > 1.0)  # Threshold of 1.0

        inconsistency_test = {
            'prob_any_interaction': prob_inconsistency,
            'mean_max_abs_gamma': np.mean(max_abs_gamma),
            'median_max_abs_gamma': np.median(max_abs_gamma)
        }

        return DesignTreatmentResults(
            design_effects=design_effects_df,
            interaction_parameters=interactions_df,
            inconsistency_test=inconsistency_test
        )

    def plot_interactions(self, results: DesignTreatmentResults):
        """Create heatmap of design-by-treatment interactions.

        Args:
            results: DesignTreatmentResults object
        """
        import matplotlib.pyplot as plt
        import seaborn as sns

        # Reshape interactions into matrix
        df = results.interaction_parameters
        designs = df['design'].unique()
        treatments = df['treatment'].unique()

        matrix = np.zeros((len(designs), len(treatments)))
        for i, design in enumerate(designs):
            for j, treatment in enumerate(treatments):
                value = df[(df['design'] == design) &
                          (df['treatment'] == treatment)]['mean'].values
                if len(value) > 0:
                    matrix[i, j] = value[0]

        # Plot
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.heatmap(matrix,
                   xticklabels=treatments,
                   yticklabels=[str(d) for d in designs],
                   cmap='RdBu_r',
                   center=0,
                   annot=True,
                   fmt='.2f',
                   ax=ax)

        ax.set_title('Design-by-Treatment Interactions')
        ax.set_xlabel('Treatment')
        ax.set_ylabel('Study Design')

        plt.tight_layout()
        return fig
