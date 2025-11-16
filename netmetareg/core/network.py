"""
Treatment network graph structure and analysis.

This module handles the network structure of treatment comparisons,
including connectivity analysis, loop detection, and network geometry.
"""

import numpy as np
import networkx as nx
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from .data_structure import NMAData, Study


class TreatmentNetwork:
    """Represents the network structure of treatment comparisons.

    This class uses graph theory to analyze the geometry of the treatment
    network, detect inconsistency loops, and identify node-splitting opportunities.

    Attributes:
        data: NMAData object containing study information
        graph: NetworkX graph representing treatment network
        direct_evidence: Dictionary mapping treatment pairs to studies with direct evidence
    """

    def __init__(self, data: NMAData):
        """Initialize treatment network.

        Args:
            data: NMAData object
        """
        self.data = data
        self.graph = None
        self.direct_evidence = defaultdict(list)
        self._build_network()

    def _build_network(self):
        """Build network graph from data."""
        self.graph = nx.Graph()

        # Add all treatments as nodes
        for treatment in self.data.treatments:
            self.graph.add_node(treatment)

        # Add edges for each study
        for study in self.data.studies:
            # For each study, add edges between all treatment pairs
            for i in range(len(study.treatments)):
                for j in range(i + 1, len(study.treatments)):
                    t1, t2 = study.treatments[i], study.treatments[j]
                    pair = tuple(sorted([t1, t2]))

                    # Add edge if not present
                    if not self.graph.has_edge(t1, t2):
                        self.graph.add_edge(t1, t2, weight=0, studies=[])

                    # Increment weight (number of studies)
                    self.graph[t1][t2]['weight'] += 1
                    self.graph[t1][t2]['studies'].append(study.study_id)

                    # Track direct evidence
                    self.direct_evidence[pair].append(study.study_id)

    @property
    def n_treatments(self) -> int:
        """Number of treatments in network."""
        return self.graph.number_of_nodes()

    @property
    def n_comparisons(self) -> int:
        """Number of direct treatment comparisons."""
        return self.graph.number_of_edges()

    def is_connected(self) -> bool:
        """Check if treatment network is fully connected.

        Returns:
            True if all treatments are connected (directly or indirectly)
        """
        return nx.is_connected(self.graph)

    def get_components(self) -> List[Set[str]]:
        """Get connected components of the network.

        Returns:
            List of sets, each containing treatments in a connected component
        """
        return [set(c) for c in nx.connected_components(self.graph)]

    def get_disconnected_treatments(self) -> List[str]:
        """Get treatments that are disconnected from main network.

        Returns:
            List of treatment names in smaller components
        """
        if self.is_connected():
            return []

        components = self.get_components()
        # Find largest component
        main_component = max(components, key=len)

        # Return treatments not in main component
        disconnected = []
        for component in components:
            if component != main_component:
                disconnected.extend(list(component))

        return disconnected

    def find_cycles(self, min_length: int = 3) -> List[List[str]]:
        """Find all cycles (loops) in the network.

        These cycles are potential sources of inconsistency in network meta-analysis.

        Args:
            min_length: Minimum cycle length to report (default 3 = triangles)

        Returns:
            List of cycles, each represented as a list of treatment names
        """
        # Use simple cycles algorithm
        cycles = list(nx.simple_cycles(self.graph.to_directed()))

        # Filter by length and convert back to undirected
        unique_cycles = []
        seen = set()

        for cycle in cycles:
            if len(cycle) >= min_length:
                # Normalize cycle representation (start with smallest node)
                normalized = tuple(sorted(cycle))
                if normalized not in seen:
                    seen.add(normalized)
                    unique_cycles.append(list(normalized))

        return unique_cycles

    def find_triangles(self) -> List[Tuple[str, str, str]]:
        """Find all triangular loops in the network.

        Triangles are the simplest inconsistency loops.

        Returns:
            List of triangles, each as a tuple of 3 treatment names
        """
        triangles = []
        for clique in nx.enumerate_all_cliques(self.graph):
            if len(clique) == 3:
                triangles.append(tuple(sorted(clique)))
            elif len(clique) > 3:
                # Also extract all triangles from larger cliques
                from itertools import combinations
                for triangle in combinations(clique, 3):
                    triangles.append(tuple(sorted(triangle)))

        return list(set(triangles))  # Remove duplicates

    def get_node_splitting_pairs(self) -> List[Tuple[str, str]]:
        """Identify treatment pairs suitable for node-splitting.

        Node-splitting can be performed for comparisons that have both:
        1. Direct evidence (studies directly comparing the treatments)
        2. Indirect evidence (paths through other treatments)

        Returns:
            List of treatment pairs (as tuples) suitable for node-splitting
        """
        candidates = []

        for t1, t2 in self.graph.edges():
            # Check if there's direct evidence
            if not self.has_direct_evidence(t1, t2):
                continue

            # Check if there's indirect evidence (path excluding direct edge)
            temp_graph = self.graph.copy()
            temp_graph.remove_edge(t1, t2)

            if nx.has_path(temp_graph, t1, t2):
                candidates.append(tuple(sorted([t1, t2])))

        return candidates

    def has_direct_evidence(self, t1: str, t2: str) -> bool:
        """Check if there is direct evidence for a treatment comparison.

        Args:
            t1: First treatment
            t2: Second treatment

        Returns:
            True if any study directly compares t1 and t2
        """
        pair = tuple(sorted([t1, t2]))
        return len(self.direct_evidence[pair]) > 0

    def get_indirect_paths(self, t1: str, t2: str, max_length: int = 5) -> List[List[str]]:
        """Get all indirect paths between two treatments.

        Args:
            t1: First treatment
            t2: Second treatment
            max_length: Maximum path length to consider

        Returns:
            List of paths, each as a list of treatment names
        """
        # Create graph without direct edge
        temp_graph = self.graph.copy()
        if temp_graph.has_edge(t1, t2):
            temp_graph.remove_edge(t1, t2)

        # Find all simple paths
        try:
            paths = list(nx.all_simple_paths(temp_graph, t1, t2, cutoff=max_length))
        except nx.NetworkXNoPath:
            paths = []

        return paths

    def get_design_matrix(self) -> np.ndarray:
        """Get design matrix for network structure.

        The design matrix X has dimensions (n_comparisons × n_treatments)
        where X[i,j] = 1 if treatment j is the active treatment in comparison i,
        X[i,j] = -1 if treatment j is the control, and 0 otherwise.

        Returns:
            Design matrix as numpy array
        """
        treatments = sorted(self.data.treatments)
        treatment_idx = {t: i for i, t in enumerate(treatments)}

        comparisons = []
        for study in self.data.studies:
            if study.is_two_arm:
                comparisons.append((study.treatments[0], study.treatments[1]))
            else:
                # Multi-arm: all comparisons to baseline
                for i in range(1, study.n_arms):
                    comparisons.append((study.treatments[0], study.treatments[i]))

        n_comp = len(comparisons)
        n_trt = len(treatments)
        X = np.zeros((n_comp, n_trt))

        for i, (t1, t2) in enumerate(comparisons):
            X[i, treatment_idx[t1]] = -1
            X[i, treatment_idx[t2]] = 1

        return X

    def get_study_design_types(self) -> Dict[str, List[str]]:
        """Categorize studies by their design (which treatments they compare).

        Returns:
            Dictionary mapping design signature to list of study IDs
        """
        designs = defaultdict(list)

        for study in self.data.studies:
            # Create design signature (sorted tuple of treatments)
            signature = tuple(sorted(study.treatments))
            designs[signature].append(study.study_id)

        return dict(designs)

    def get_multi_arm_studies(self) -> List[Study]:
        """Get all multi-arm studies.

        Returns:
            List of Study objects with more than 2 arms
        """
        return [s for s in self.data.studies if s.is_multi_arm]

    def calculate_network_metrics(self) -> Dict[str, float]:
        """Calculate various network geometry metrics.

        Returns:
            Dictionary of network metrics
        """
        metrics = {}

        # Basic metrics
        metrics['n_treatments'] = self.n_treatments
        metrics['n_comparisons'] = self.n_comparisons
        metrics['n_studies'] = self.data.n_studies
        metrics['is_connected'] = self.is_connected()

        # Density: ratio of actual edges to possible edges
        max_edges = self.n_treatments * (self.n_treatments - 1) / 2
        metrics['density'] = self.n_comparisons / max_edges if max_edges > 0 else 0

        # Multi-arm proportion
        n_multi_arm = len(self.get_multi_arm_studies())
        metrics['prop_multi_arm'] = n_multi_arm / self.data.n_studies if self.data.n_studies > 0 else 0

        # Average degree
        if self.n_treatments > 0:
            degrees = [d for _, d in self.graph.degree()]
            metrics['mean_degree'] = np.mean(degrees)
            metrics['median_degree'] = np.median(degrees)

        # Loop metrics
        triangles = self.find_triangles()
        metrics['n_triangles'] = len(triangles)

        # Node-splitting opportunities
        ns_pairs = self.get_node_splitting_pairs()
        metrics['n_node_splitting_pairs'] = len(ns_pairs)

        # Clustering coefficient
        metrics['clustering_coefficient'] = nx.average_clustering(self.graph)

        # Average path length (if connected)
        if self.is_connected():
            metrics['avg_path_length'] = nx.average_shortest_path_length(self.graph)
        else:
            metrics['avg_path_length'] = np.nan

        return metrics

    def visualize_network(self, output_file: Optional[str] = None):
        """Create a visualization of the treatment network.

        Args:
            output_file: Optional file path to save visualization
        """
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 8))

        # Use spring layout for positioning
        pos = nx.spring_layout(self.graph, k=2, iterations=50)

        # Draw nodes
        nx.draw_networkx_nodes(
            self.graph, pos,
            node_color='lightblue',
            node_size=3000,
            ax=ax
        )

        # Draw edges with width proportional to number of studies
        edges = self.graph.edges()
        weights = [self.graph[u][v]['weight'] for u, v in edges]
        max_weight = max(weights) if weights else 1

        nx.draw_networkx_edges(
            self.graph, pos,
            width=[5 * w / max_weight for w in weights],
            alpha=0.6,
            ax=ax
        )

        # Draw labels
        nx.draw_networkx_labels(
            self.graph, pos,
            font_size=10,
            font_weight='bold',
            ax=ax
        )

        # Add edge labels (number of studies)
        edge_labels = {(u, v): str(self.graph[u][v]['weight']) for u, v in edges}
        nx.draw_networkx_edge_labels(
            self.graph, pos,
            edge_labels,
            font_size=8,
            ax=ax
        )

        ax.set_title('Treatment Network Graph', fontsize=16, fontweight='bold')
        ax.axis('off')
        plt.tight_layout()

        if output_file:
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
        else:
            plt.show()

        return fig

    def summary(self) -> str:
        """Generate a text summary of the network.

        Returns:
            Multi-line string describing network structure
        """
        metrics = self.calculate_network_metrics()

        lines = [
            "=" * 60,
            "TREATMENT NETWORK SUMMARY",
            "=" * 60,
            f"Number of treatments: {metrics['n_treatments']}",
            f"Number of direct comparisons: {metrics['n_comparisons']}",
            f"Number of studies: {metrics['n_studies']}",
            f"Network density: {metrics['density']:.3f}",
            f"",
            f"Connected: {'Yes' if metrics['is_connected'] else 'No'}",
        ]

        if not metrics['is_connected']:
            disconnected = self.get_disconnected_treatments()
            lines.append(f"Disconnected treatments: {', '.join(disconnected)}")

        lines.extend([
            f"",
            f"Multi-arm studies: {metrics['prop_multi_arm']:.1%}",
            f"Mean treatment degree: {metrics['mean_degree']:.1f}",
            f"",
            f"Number of triangular loops: {metrics['n_triangles']}",
            f"Node-splitting opportunities: {metrics['n_node_splitting_pairs']}",
            f"",
            f"Clustering coefficient: {metrics['clustering_coefficient']:.3f}",
        ])

        if not np.isnan(metrics['avg_path_length']):
            lines.append(f"Average path length: {metrics['avg_path_length']:.2f}")

        lines.append("=" * 60)

        return "\n".join(lines)
