"""
Network coherence and contribution analysis.

Quantifies the contribution of different evidence sources to network estimates
and assesses network robustness.

References:
    Papakonstantinou et al. (2018). CINeMA: Software for semiautomated assessment
    of the confidence in the results of network meta-analysis. Campbell Systematic Reviews.

    König et al. (2013). Visualizing the flow of evidence in network meta-analysis.
    Journal of Clinical Epidemiology.
"""

import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
from scipy.linalg import inv, pinv


class NetworkCoherence:
    """Assess network coherence and contribution of evidence sources.

    Provides methods for:
    - Contribution matrix (how much each direct comparison contributes)
    - Network disconnection analysis
    - Evidence flow visualization
    - Robustness to study removal
    """

    def __init__(self, network_data):
        """Initialize network coherence analysis.

        Args:
            network_data: NMAData or TreatmentNetwork object
        """
        self.data = network_data
        self.contribution_matrix = None

    def compute_contribution_matrix(self) -> pd.DataFrame:
        """Compute contribution matrix.

        The contribution matrix C[i,j] indicates how much the direct
        comparison i contributes to the network estimate j.

        Returns:
            DataFrame with contribution percentages
        """
        # Build network graph
        G = self._build_network_graph()

        # Get all treatment pairs
        treatments = list(G.nodes())
        n_treatments = len(treatments)

        # Initialize contribution matrix
        direct_comparisons = list(G.edges())
        n_comparisons = len(direct_comparisons)

        # Map edges to indices
        edge_to_idx = {edge: i for i, edge in enumerate(direct_comparisons)}

        # Build design matrix (incidence matrix)
        # Each row is a study, each column is a basic parameter
        X = np.zeros((n_comparisons, n_treatments - 1))

        for i, (t1, t2) in enumerate(direct_comparisons):
            if t1 != treatments[0]:  # Not reference
                X[i, treatments.index(t1) - 1] = 1
            if t2 != treatments[0]:
                X[i, treatments.index(t2) - 1] = 1

        # Compute hat matrix (contribution matrix)
        # H = X(X'X)^{-1}X'
        XtX = X.T @ X
        XtX_inv = pinv(XtX)  # Use pseudo-inverse for numerical stability
        H = X @ XtX_inv @ X.T

        # Convert to DataFrame
        contribution_df = pd.DataFrame(
            H,
            index=[f"{t1}-{t2}" for t1, t2 in direct_comparisons],
            columns=[f"{t1}-{t2}" for t1, t2 in direct_comparisons]
        )

        self.contribution_matrix = contribution_df
        return contribution_df

    def _build_network_graph(self) -> nx.Graph:
        """Build network graph from data."""
        G = nx.Graph()

        # Add nodes (treatments)
        if hasattr(self.data, 'treatments'):
            treatments = self.data.treatments
        else:
            treatments = self.data.get_treatments()

        G.add_nodes_from(treatments)

        # Add edges (comparisons)
        if hasattr(self.data, 'studies'):
            studies = self.data.studies
        else:
            studies = self.data.get_studies()

        for study in studies:
            for i in range(len(study.treatments)):
                for j in range(i + 1, len(study.treatments)):
                    t1, t2 = study.treatments[i], study.treatments[j]
                    if G.has_edge(t1, t2):
                        G[t1][t2]['weight'] += 1
                    else:
                        G.add_edge(t1, t2, weight=1)

        return G

    def assess_network_connectivity(self) -> Dict[str, any]:
        """Assess network connectivity and identify critical edges.

        Returns:
            Dictionary with connectivity metrics
        """
        G = self._build_network_graph()

        metrics = {
            'n_treatments': G.number_of_nodes(),
            'n_comparisons': G.number_of_edges(),
            'is_connected': nx.is_connected(G),
            'n_components': nx.number_connected_components(G),
            'diameter': nx.diameter(G) if nx.is_connected(G) else None,
            'average_degree': np.mean([d for _, d in G.degree()]),
        }

        # Identify bridges (critical edges whose removal disconnects network)
        bridges = list(nx.bridges(G))
        metrics['n_bridges'] = len(bridges)
        metrics['bridges'] = bridges

        # Articulation points (critical nodes)
        articulation_points = list(nx.articulation_points(G))
        metrics['articulation_points'] = articulation_points

        return metrics

    def compute_evidence_flow(self,
                             comparison: Tuple[str, str]) -> Dict[str, float]:
        """Compute how evidence flows to a specific comparison.

        Args:
            comparison: Tuple of (treatment1, treatment2)

        Returns:
            Dictionary mapping source comparisons to contribution weights
        """
        if self.contribution_matrix is None:
            self.compute_contribution_matrix()

        comparison_str = f"{comparison[0]}-{comparison[1]}"
        reverse_str = f"{comparison[1]}-{comparison[0]}"

        if comparison_str in self.contribution_matrix.columns:
            contributions = self.contribution_matrix[comparison_str]
        elif reverse_str in self.contribution_matrix.columns:
            contributions = self.contribution_matrix[reverse_str]
        else:
            raise ValueError(f"Comparison {comparison} not in network")

        # Filter to non-zero contributions
        contrib_dict = contributions[np.abs(contributions) > 0.01].to_dict()

        return contrib_dict

    def leave_one_out_sensitivity(self) -> pd.DataFrame:
        """Assess sensitivity to removing each comparison.

        Returns:
            DataFrame with impact metrics for each comparison
        """
        G = self._build_network_graph()
        original_edges = list(G.edges())

        sensitivity_results = []

        for edge in original_edges:
            # Remove edge
            G_temp = G.copy()
            G_temp.remove_edge(*edge)

            # Check impact
            still_connected = nx.is_connected(G_temp)
            n_components = nx.number_connected_components(G_temp)

            sensitivity_results.append({
                'comparison': f"{edge[0]}-{edge[1]}",
                'is_bridge': edge in nx.bridges(G),
                'disconnects_network': not still_connected,
                'n_components_after_removal': n_components,
                'impact': 'Critical' if not still_connected else 'Non-critical'
            })

        return pd.DataFrame(sensitivity_results)

    def plot_network(self,
                    node_size: int = 3000,
                    font_size: int = 12,
                    figsize: tuple = (10, 8)):
        """Visualize treatment network with contribution information.

        Args:
            node_size: Size of nodes
            font_size: Font size for labels
            figsize: Figure size
        """
        G = self._build_network_graph()

        fig, ax = plt.subplots(figsize=figsize)

        # Layout
        pos = nx.spring_layout(G, seed=42)

        # Draw nodes
        nx.draw_networkx_nodes(
            G, pos,
            node_size=node_size,
            node_color='lightblue',
            edgecolors='black',
            linewidths=2,
            ax=ax
        )

        # Draw edges with width proportional to number of studies
        edges = G.edges()
        weights = [G[u][v]['weight'] for u, v in edges]
        max_weight = max(weights)

        nx.draw_networkx_edges(
            G, pos,
            width=[5 * w / max_weight for w in weights],
            alpha=0.6,
            ax=ax
        )

        # Draw labels
        nx.draw_networkx_labels(
            G, pos,
            font_size=font_size,
            font_weight='bold',
            ax=ax
        )

        # Edge labels (number of studies)
        edge_labels = {(u, v): f"{w}" for (u, v), w in zip(edges, weights)}
        nx.draw_networkx_edge_labels(
            G, pos,
            edge_labels,
            font_size=font_size - 2,
            ax=ax
        )

        ax.set_title('Treatment Network\n(Edge labels show number of studies)',
                    fontsize=14)
        ax.axis('off')
        plt.tight_layout()

        return fig

    def plot_contribution_heatmap(self, figsize: tuple = (12, 10)):
        """Plot heatmap of contribution matrix.

        Args:
            figsize: Figure size
        """
        if self.contribution_matrix is None:
            self.compute_contribution_matrix()

        fig, ax = plt.subplots(figsize=figsize)

        import seaborn as sns
        sns.heatmap(
            self.contribution_matrix,
            annot=True,
            fmt='.2f',
            cmap='RdYlBu_r',
            center=0,
            vmin=-0.5,
            vmax=1.0,
            cbar_kws={'label': 'Contribution'},
            ax=ax
        )

        ax.set_title('Contribution Matrix\n(How direct evidence contributes to network estimates)')
        ax.set_xlabel('Network Estimate')
        ax.set_ylabel('Direct Comparison')

        plt.tight_layout()
        return fig


def contribution_matrix(network_data) -> pd.DataFrame:
    """Convenience function to compute contribution matrix.

    Args:
        network_data: NMAData or TreatmentNetwork object

    Returns:
        Contribution matrix DataFrame
    """
    coherence = NetworkCoherence(network_data)
    return coherence.compute_contribution_matrix()


def assess_network_robustness(network_data) -> Dict:
    """Comprehensive network robustness assessment.

    Args:
        network_data: NMAData or TreatmentNetwork object

    Returns:
        Dictionary with all robustness metrics and analyses
    """
    coherence = NetworkCoherence(network_data)

    results = {
        'connectivity': coherence.assess_network_connectivity(),
        'contribution_matrix': coherence.compute_contribution_matrix(),
        'sensitivity': coherence.leave_one_out_sensitivity()
    }

    return results


class NetworkDiversity:
    """Assess diversity of evidence in network meta-analysis.

    Quantifies how diverse the evidence base is in terms of:
    - Number of independent paths between treatments
    - Redundancy of evidence
    - Balance of evidence across comparisons
    """

    def __init__(self, network_data):
        """Initialize network diversity analysis."""
        self.data = network_data
        self.G = self._build_graph()

    def _build_graph(self) -> nx.Graph:
        """Build network graph."""
        G = nx.Graph()

        if hasattr(self.data, 'treatments'):
            treatments = self.data.treatments
            studies = self.data.studies
        else:
            treatments = self.data.get_treatments()
            studies = self.data.get_studies()

        G.add_nodes_from(treatments)

        for study in studies:
            for i in range(len(study.treatments)):
                for j in range(i + 1, len(study.treatments)):
                    t1, t2 = study.treatments[i], study.treatments[j]
                    if G.has_edge(t1, t2):
                        G[t1][t2]['weight'] += 1
                    else:
                        G.add_edge(t1, t2, weight=1)

        return G

    def compute_path_diversity(self) -> pd.DataFrame:
        """Compute number of independent paths between all treatment pairs.

        Returns:
            DataFrame with path counts
        """
        treatments = list(self.G.nodes())
        n_treatments = len(treatments)

        path_data = []

        for i, t1 in enumerate(treatments):
            for j, t2 in enumerate(treatments):
                if i < j:
                    # Count simple paths
                    paths = list(nx.all_simple_paths(self.G, t1, t2))
                    n_paths = len(paths)

                    # Direct evidence?
                    has_direct = self.G.has_edge(t1, t2)

                    path_data.append({
                        'comparison': f"{t1}-{t2}",
                        'n_paths': n_paths,
                        'has_direct': has_direct,
                        'shortest_path_length': nx.shortest_path_length(self.G, t1, t2),
                        'diversity_score': n_paths / nx.shortest_path_length(self.G, t1, t2)
                    })

        return pd.DataFrame(path_data)

    def compute_evidence_balance(self) -> Dict[str, float]:
        """Compute balance of evidence across network.

        Returns:
            Dictionary with balance metrics
        """
        # Get study counts per comparison
        edge_weights = [self.G[u][v]['weight'] for u, v in self.G.edges()]

        # Gini coefficient for inequality
        sorted_weights = np.sort(edge_weights)
        n = len(sorted_weights)
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * sorted_weights)) / (n * np.sum(sorted_weights)) - (n + 1) / n

        return {
            'mean_studies_per_comparison': np.mean(edge_weights),
            'median_studies_per_comparison': np.median(edge_weights),
            'min_studies': np.min(edge_weights),
            'max_studies': np.max(edge_weights),
            'gini_coefficient': gini,  # 0 = perfect equality, 1 = perfect inequality
            'cv': np.std(edge_weights) / np.mean(edge_weights)  # Coefficient of variation
        }
