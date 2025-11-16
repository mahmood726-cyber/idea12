"""
Basic tests for netmetareg package.

This file contains unit tests for core functionality.
"""

import pytest
import numpy as np
import pandas as pd

from netmetareg.core.data_structure import NMAData, Study
from netmetareg.core.network import TreatmentNetwork
from netmetareg.models.frequentist_nma import FrequentistNMA


class TestStudy:
    """Test Study class."""

    def test_study_creation(self):
        """Test basic study creation."""
        study = Study(
            study_id="Test1",
            treatments=["A", "B"],
            effects=np.array([0.5]),
            se=np.array([0.1]),
            n=np.array([100, 100])
        )

        assert study.study_id == "Test1"
        assert study.n_arms == 2
        assert study.is_two_arm
        assert not study.is_multi_arm

    def test_multi_arm_study(self):
        """Test multi-arm study."""
        study = Study(
            study_id="Test2",
            treatments=["A", "B", "C"],
            effects=np.array([0.5, 0.7]),
            se=np.array([0.1, 0.12]),
            n=np.array([100, 100, 100])
        )

        assert study.n_arms == 3
        assert not study.is_two_arm
        assert study.is_multi_arm

    def test_validation(self):
        """Test data validation."""
        with pytest.raises(ValueError):
            # Wrong number of effects
            Study(
                study_id="Bad",
                treatments=["A", "B"],
                effects=np.array([0.5, 0.6]),  # Should be 1
                se=np.array([0.1])
            )


class TestNMAData:
    """Test NMAData class."""

    @pytest.fixture
    def simple_data(self):
        """Create simple test dataset."""
        studies = [
            Study("S1", ["A", "B"], np.array([0.5]), np.array([0.1])),
            Study("S2", ["B", "C"], np.array([0.3]), np.array([0.12])),
            Study("S3", ["A", "C"], np.array([0.8]), np.array([0.15]))
        ]
        return NMAData(studies, reference_treatment="A")

    def test_nma_data_properties(self, simple_data):
        """Test NMAData properties."""
        assert simple_data.n_studies == 3
        assert simple_data.n_treatments == 3
        assert simple_data.reference_treatment == "A"
        assert set(simple_data.treatments) == {"A", "B", "C"}

    def test_add_study(self, simple_data):
        """Test adding studies."""
        new_study = Study("S4", ["A", "B"], np.array([0.4]), np.array([0.11]))
        simple_data.add_study(new_study)
        assert simple_data.n_studies == 4

    def test_to_dataframe(self, simple_data):
        """Test conversion to DataFrame."""
        df = simple_data.to_dataframe(format='long')
        assert isinstance(df, pd.DataFrame)
        assert 'study' in df.columns
        assert 'treatment' in df.columns

    def test_from_dataframe(self):
        """Test creating from DataFrame."""
        df = pd.DataFrame({
            'study': ['S1', 'S1', 'S2', 'S2'],
            'treatment': ['A', 'B', 'B', 'C'],
            'effect': [0, 0.5, 0, 0.3],
            'se': [0, 0.1, 0, 0.12],
            'n': [100, 100, 100, 100]
        })

        data = NMAData.from_dataframe(
            df,
            study_col='study',
            treatment_col='treatment',
            effect_col='effect',
            se_col='se',
            n_col='n',
            format='arm'
        )

        assert data.n_studies == 2
        assert data.n_treatments == 3


class TestTreatmentNetwork:
    """Test TreatmentNetwork class."""

    @pytest.fixture
    def network_data(self):
        """Create network data."""
        studies = [
            Study("S1", ["A", "B"], np.array([0.5]), np.array([0.1])),
            Study("S2", ["B", "C"], np.array([0.3]), np.array([0.12])),
            Study("S3", ["A", "C"], np.array([0.8]), np.array([0.15]))
        ]
        return NMAData(studies)

    def test_network_connectivity(self, network_data):
        """Test network connectivity."""
        network = TreatmentNetwork(network_data)
        assert network.is_connected()
        assert network.n_treatments == 3
        assert network.n_comparisons == 3

    def test_find_triangles(self, network_data):
        """Test triangle detection."""
        network = TreatmentNetwork(network_data)
        triangles = network.find_triangles()
        assert len(triangles) == 1  # ABC triangle

    def test_node_splitting_pairs(self, network_data):
        """Test node-splitting identification."""
        network = TreatmentNetwork(network_data)
        pairs = network.get_node_splitting_pairs()
        # All comparisons have both direct and indirect evidence
        assert len(pairs) == 3


class TestFrequentistNMA:
    """Test frequentist NMA model."""

    @pytest.fixture
    def nma_data(self):
        """Create test data for NMA."""
        studies = [
            Study("S1", ["A", "B"], np.array([0.5]), np.array([0.1]), np.array([100, 100])),
            Study("S2", ["B", "C"], np.array([0.3]), np.array([0.12]), np.array([100, 100])),
            Study("S3", ["A", "C"], np.array([0.8]), np.array([0.15]), np.array([100, 100])),
            Study("S4", ["A", "B"], np.array([0.6]), np.array([0.11]), np.array([100, 100]))
        ]
        return NMAData(studies, reference_treatment="A")

    def test_fixed_effects_fit(self, nma_data):
        """Test fixed effects model."""
        model = FrequentistNMA(nma_data, random_effects=False)
        results = model.fit()

        assert results.treatment_effects is not None
        assert len(results.treatment_effects) == 3
        assert results.treatment_effects.loc[0, 'treatment'] == "A"
        assert results.treatment_effects.loc[0, 'effect'] == 0.0  # Reference

    def test_random_effects_fit(self, nma_data):
        """Test random effects model."""
        model = FrequentistNMA(nma_data, random_effects=True)
        results = model.fit()

        assert results.heterogeneity is not None
        assert 'tau_squared' in results.heterogeneity
        assert 'I_squared' in results.heterogeneity

    def test_prediction(self, nma_data):
        """Test pairwise prediction."""
        model = FrequentistNMA(nma_data)
        results = model.fit()

        prediction = model.predict("B", "C")
        assert 'effect' in prediction
        assert 'se' in prediction
        assert 'ci_lower' in prediction
        assert 'ci_upper' in prediction

    def test_ranking(self, nma_data):
        """Test treatment ranking."""
        model = FrequentistNMA(nma_data)
        results = model.fit()

        rankings = model.rank_treatments(method='P-score')
        assert len(rankings) == 3
        assert 'p_score' in rankings.columns
        assert 'rank' in rankings.columns


def test_covariate_matrix():
    """Test covariate matrix creation."""
    studies = [
        Study("S1", ["A", "B"], np.array([0.5]), np.array([0.1]),
              covariates={"age": 50, "severity": 10}),
        Study("S2", ["B", "C"], np.array([0.3]), np.array([0.12]),
              covariates={"age": 45, "severity": 12}),
    ]
    data = NMAData(studies)

    X, params = data.get_covariate_matrix(center=True)
    assert X.shape == (2, 2)  # 2 studies, 2 covariates

    # Check centering
    assert np.allclose(X.mean(axis=0), 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
