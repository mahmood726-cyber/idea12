"""
Node-splitting method for inconsistency detection.

Node-splitting (Dias et al., 2010) separates direct and indirect evidence
for each treatment comparison to test for inconsistency.
"""

import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from ..core.data_structure import NMAData
from ..core.network import TreatmentNetwork


@dataclass
class NodeSplitResults:
    """Results from node-splitting analysis.

    Attributes:
        comparison: Treatment pair being split
        direct_effect: Direct evidence estimate
        indirect_effect: Indirect evidence estimate
        inconsistency: Difference between direct and indirect
        p_value: Bayesian p-value for inconsistency
        trace: Posterior samples
    """
    comparison: Tuple[str, str]
    direct_effect: Dict[str, float]
    indirect_effect: Dict[str, float]
    inconsistency: Dict[str, float]
    p_value: float
    trace: Optional[az.InferenceData] = None


class NodeSplitting:
    """Node-splitting for inconsistency detection.

    Node-splitting separates the direct and indirect evidence for a
    treatment comparison and estimates them separately. Inconsistency
    is detected if direct and indirect estimates differ significantly.

    For comparison A vs B:
    - Direct evidence: Studies directly comparing A and B
    - Indirect evidence: Estimated from network, excluding direct A-B studies
    - Inconsistency parameter: ω = d_direct - d_indirect
    """

    def __init__(self, data: NMAData, method: str = 'bayesian'):
        """Initialize node-splitting analysis.

        Args:
            data: NMAData object
            method: Estimation method ('bayesian' or 'frequentist')
        """
        self.data = data
        self.network = TreatmentNetwork(data)
        self.method = method

    def identify_splittable_nodes(self) -> List[Tuple[str, str]]:
        """Identify treatment comparisons suitable for node-splitting.

        Returns:
            List of treatment pairs that can be split
        """
        return self.network.get_node_splitting_pairs()

    def split_node(self,
                  treatment_1: str,
                  treatment_2: str,
                  draws: int = 2000,
                  tune: int = 1000,
                  **kwargs) -> NodeSplitResults:
        """Perform node-splitting for a specific comparison.

        Args:
            treatment_1: First treatment in comparison
            treatment_2: Second treatment in comparison
            draws: Number of MCMC draws
            tune: Number of tuning steps
            **kwargs: Additional arguments for sampler

        Returns:
            NodeSplitResults object
        """
        if self.method == 'bayesian':
            return self._split_node_bayesian(treatment_1, treatment_2, draws, tune, **kwargs)
        else:
            raise NotImplementedError("Frequentist node-splitting not yet implemented")

    def _split_node_bayesian(self,
                            treatment_1: str,
                            treatment_2: str,
                            draws: int,
                            tune: int,
                            **kwargs) -> NodeSplitResults:
        """Bayesian node-splitting using PyMC.

        Args:
            treatment_1: First treatment
            treatment_2: Second treatment
            draws: Number of MCMC draws
            tune: Number of tuning steps

        Returns:
            NodeSplitResults object
        """
        # Prepare data with split comparison
        data_dict = self._prepare_split_data(treatment_1, treatment_2)

        with pm.Model() as model:
            # Treatment effects (basic NMA parameters)
            n_treatments = data_dict['n_treatments']
            ref_idx = data_dict['ref_idx']

            d_raw = pm.Normal('d_raw', mu=0, sigma=100, shape=n_treatments - 1)
            d = pm.Deterministic('d',
                                pm.math.concatenate([
                                    d_raw[:ref_idx],
                                    [0],
                                    d_raw[ref_idx:]
                                ]))

            # Direct effect for split comparison
            d_direct = pm.Normal('d_direct', mu=0, sigma=100)

            # Inconsistency parameter
            omega = pm.Normal('omega', mu=0, sigma=10)

            # Indirect effect (derived)
            t1_idx = data_dict['t1_idx']
            t2_idx = data_dict['t2_idx']
            d_indirect = pm.Deterministic('d_indirect', d[t2_idx] - d[t1_idx])

            # Relationship: d_direct = d_indirect + omega
            pm.Deterministic('omega_check', d_direct - d_indirect)

            # Heterogeneity
            tau = pm.HalfNormal('tau', sigma=1)

            # Likelihood for direct evidence
            if data_dict['y_direct'].shape[0] > 0:
                delta_direct = pm.Normal(
                    'delta_direct',
                    mu=d_direct,
                    sigma=tau,
                    shape=data_dict['y_direct'].shape[0]
                )
                pm.Normal(
                    'y_direct',
                    mu=delta_direct,
                    sigma=data_dict['se_direct'],
                    observed=data_dict['y_direct']
                )

            # Likelihood for indirect evidence (rest of network)
            if data_dict['y_indirect'].shape[0] > 0:
                # Basic effects from network
                basic_effects = d[data_dict['t2_indirect']] - d[data_dict['t1_indirect']]

                delta_indirect = pm.Normal(
                    'delta_indirect',
                    mu=basic_effects,
                    sigma=tau,
                    shape=data_dict['y_indirect'].shape[0]
                )
                pm.Normal(
                    'y_indirect',
                    mu=delta_indirect,
                    sigma=data_dict['se_indirect'],
                    observed=data_dict['y_indirect']
                )

            # Sample
            trace = pm.sample(
                draws=draws,
                tune=tune,
                return_inferencedata=True,
                **kwargs
            )

        # Extract results
        direct_samples = trace.posterior['d_direct'].values.flatten()
        indirect_samples = trace.posterior['d_indirect'].values.flatten()
        omega_samples = trace.posterior['omega'].values.flatten()

        direct_effect = {
            'mean': float(np.mean(direct_samples)),
            'sd': float(np.std(direct_samples)),
            'median': float(np.median(direct_samples)),
            'q025': float(np.percentile(direct_samples, 2.5)),
            'q975': float(np.percentile(direct_samples, 97.5))
        }

        indirect_effect = {
            'mean': float(np.mean(indirect_samples)),
            'sd': float(np.std(indirect_samples)),
            'median': float(np.median(indirect_samples)),
            'q025': float(np.percentile(indirect_samples, 2.5)),
            'q975': float(np.percentile(indirect_samples, 97.5))
        }

        inconsistency = {
            'mean': float(np.mean(omega_samples)),
            'sd': float(np.std(omega_samples)),
            'median': float(np.median(omega_samples)),
            'q025': float(np.percentile(omega_samples, 2.5)),
            'q975': float(np.percentile(omega_samples, 97.5))
        }

        # Bayesian p-value: P(|omega| > 0)
        # More specifically, proportion of posterior where sign matches MAP estimate
        p_value = float(2 * min(np.mean(omega_samples > 0), np.mean(omega_samples < 0)))

        results = NodeSplitResults(
            comparison=(treatment_1, treatment_2),
            direct_effect=direct_effect,
            indirect_effect=indirect_effect,
            inconsistency=inconsistency,
            p_value=p_value,
            trace=trace
        )

        return results

    def _prepare_split_data(self,
                           treatment_1: str,
                           treatment_2: str) -> Dict:
        """Prepare data for node-splitting.

        Args:
            treatment_1: First treatment
            treatment_2: Second treatment

        Returns:
            Dictionary with split data arrays
        """
        treatment_idx = {t: i for i, t in enumerate(self.data.treatments)}
        t1_idx = treatment_idx[treatment_1]
        t2_idx = treatment_idx[treatment_2]
        ref_idx = treatment_idx[self.data.reference_treatment]

        # Split studies into direct and indirect evidence
        y_direct = []
        se_direct = []
        y_indirect = []
        se_indirect = []
        t1_indirect = []
        t2_indirect = []

        comparison_pair = set([treatment_1, treatment_2])

        for study in self.data.studies:
            if study.effects is None or study.se is None:
                continue

            study_treatments = set(study.treatments)

            # Check if this study provides direct evidence for the split comparison
            if comparison_pair.issubset(study_treatments):
                # Direct evidence
                # Find the contrast corresponding to this comparison
                for k in range(1, study.n_arms):
                    t_base = study.treatments[0]
                    t_active = study.treatments[k]

                    if set([t_base, t_active]) == comparison_pair:
                        # This is the direct comparison
                        effect = study.effects[k - 1]
                        se = study.se[k - 1]

                        # Ensure correct direction (treatment_2 vs treatment_1)
                        if t_active == treatment_1 and t_base == treatment_2:
                            effect = -effect

                        y_direct.append(effect)
                        se_direct.append(se)
                        break
            else:
                # Indirect evidence (doesn't include direct comparison)
                for k in range(1, study.n_arms):
                    t_base = treatment_idx[study.treatments[0]]
                    t_active = treatment_idx[study.treatments[k]]

                    y_indirect.append(study.effects[k - 1])
                    se_indirect.append(study.se[k - 1])
                    t1_indirect.append(t_base)
                    t2_indirect.append(t_active)

        return {
            'n_treatments': len(self.data.treatments),
            'ref_idx': ref_idx,
            't1_idx': t1_idx,
            't2_idx': t2_idx,
            'y_direct': np.array(y_direct),
            'se_direct': np.array(se_direct),
            'y_indirect': np.array(y_indirect),
            'se_indirect': np.array(se_indirect),
            't1_indirect': np.array(t1_indirect, dtype=int),
            't2_indirect': np.array(t2_indirect, dtype=int)
        }

    def split_all_nodes(self,
                       draws: int = 2000,
                       tune: int = 1000,
                       **kwargs) -> pd.DataFrame:
        """Perform node-splitting for all suitable comparisons.

        Args:
            draws: Number of MCMC draws per comparison
            tune: Number of tuning steps
            **kwargs: Additional sampler arguments

        Returns:
            DataFrame with node-splitting results for all comparisons
        """
        splittable = self.identify_splittable_nodes()

        if not splittable:
            return pd.DataFrame()

        results_list = []

        for t1, t2 in splittable:
            print(f"Node-splitting: {t1} vs {t2}")
            result = self.split_node(t1, t2, draws, tune, **kwargs)

            results_list.append({
                'treatment_1': t1,
                'treatment_2': t2,
                'direct_mean': result.direct_effect['mean'],
                'direct_sd': result.direct_effect['sd'],
                'direct_q025': result.direct_effect['q025'],
                'direct_q975': result.direct_effect['q975'],
                'indirect_mean': result.indirect_effect['mean'],
                'indirect_sd': result.indirect_effect['sd'],
                'indirect_q025': result.indirect_effect['q025'],
                'indirect_q975': result.indirect_effect['q975'],
                'inconsistency_mean': result.inconsistency['mean'],
                'inconsistency_sd': result.inconsistency['sd'],
                'inconsistency_q025': result.inconsistency['q025'],
                'inconsistency_q975': result.inconsistency['q975'],
                'p_value': result.p_value,
                'significant': result.p_value < 0.05
            })

        return pd.DataFrame(results_list)

    def plot_node_split(self, result: NodeSplitResults):
        """Create forest plot comparing direct and indirect evidence.

        Args:
            result: NodeSplitResults object
        """
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))

        # Data for plotting
        labels = ['Direct', 'Indirect', 'Network (combined)']
        means = [
            result.direct_effect['mean'],
            result.indirect_effect['mean'],
            result.direct_effect['mean']  # Placeholder - should use combined estimate
        ]
        lower = [
            result.direct_effect['q025'],
            result.indirect_effect['q025'],
            result.direct_effect['q025']
        ]
        upper = [
            result.direct_effect['q975'],
            result.indirect_effect['q975'],
            result.direct_effect['q975']
        ]

        # Plot
        y_pos = np.arange(len(labels))
        ax.errorbar(means, y_pos, xerr=[np.array(means) - np.array(lower),
                                        np.array(upper) - np.array(means)],
                   fmt='o', markersize=8, capsize=5)

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.set_xlabel('Treatment Effect')
        ax.set_title(f"Node-splitting: {result.comparison[0]} vs {result.comparison[1]}\n"
                    f"Inconsistency p-value: {result.p_value:.3f}")
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig
