"""Inconsistency detection and modeling for network meta-analysis."""

from .node_splitting import NodeSplitting
from .design_treatment import DesignTreatmentInteraction

__all__ = ['NodeSplitting', 'DesignTreatmentInteraction']
