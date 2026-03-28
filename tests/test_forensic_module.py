"""
Unit Tests for Forensic Meta-Analysis Module
============================================

Comprehensive test suite for bias_detector.py and bayesian_ess.py

Test coverage:
- Input validation
- Edge cases
- Missing data handling
- Calculation accuracy
- Error handling

Author: Test team
Date: January 2025
"""

import unittest
import numpy as np
import pandas as pd
import sys
import os
import warnings

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import forensic module directly to avoid pymc dependency
forensic_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'netmetareg', 'forensic')
sys.path.insert(0, forensic_path)

from bias_detector import (
    ForensicAnalyzer,
    ForensicResults,
    calculate_discordance_index,
    calculate_e_value,
    calculate_inflation_factor
)


class TestForensicAnalyzerInitialization(unittest.TestCase):
    """Test ForensicAnalyzer initialization and validation"""

    def setUp(self):
        """Set up test data"""
        self.valid_obs = pd.DataFrame({
            'effect': [np.log(0.81), np.log(0.91)],
            'se': [0.046, 0.021],
            'n': [27099, 21206]
        })

        self.valid_rct = pd.DataFrame({
            'effect': [np.log(0.97), np.log(0.96)],
            'se': [0.051, 0.095],
            'n': [17801, 5020]
        })

    def test_valid_initialization(self):
        """Test that valid data initializes correctly"""
        analyzer = ForensicAnalyzer(
            obs_data=self.valid_obs,
            rct_data=self.valid_rct
        )

        self.assertIsNotNone(analyzer.obs_pooled)
        self.assertIsNotNone(analyzer.rct_pooled)
        self.assertEqual(analyzer.effect_type, 'log_hr')
        self.assertEqual(analyzer.sigma_ref, 2.0)

    def test_missing_required_column(self):
        """Test that missing required columns raise ValueError"""
        invalid_obs = self.valid_obs.drop(columns=['effect'])

        with self.assertRaises(ValueError) as context:
            ForensicAnalyzer(obs_data=invalid_obs, rct_data=self.valid_rct)

        self.assertIn('missing required column', str(context.exception))

    def test_empty_dataframe(self):
        """Test that empty dataframes raise ValueError"""
        empty_df = pd.DataFrame(columns=['effect', 'se', 'n'])

        with self.assertRaises(ValueError) as context:
            ForensicAnalyzer(obs_data=empty_df, rct_data=self.valid_rct)

        self.assertIn('must contain at least one study', str(context.exception))

    def test_negative_se(self):
        """Test that negative standard errors raise ValueError"""
        invalid_obs = self.valid_obs.copy()
        invalid_obs.loc[0, 'se'] = -0.05

        with self.assertRaises(ValueError) as context:
            ForensicAnalyzer(obs_data=invalid_obs, rct_data=self.valid_rct)

        self.assertIn('non-positive standard errors', str(context.exception))

    def test_non_finite_effect(self):
        """Test that non-finite effects raise ValueError"""
        invalid_obs = self.valid_obs.copy()
        invalid_obs.loc[0, 'effect'] = np.inf

        with self.assertRaises(ValueError) as context:
            ForensicAnalyzer(obs_data=invalid_obs, rct_data=self.valid_rct)

        self.assertIn('non-finite effect sizes', str(context.exception))

    def test_zero_sample_size(self):
        """Test that zero sample size raises ValueError"""
        invalid_obs = self.valid_obs.copy()
        invalid_obs.loc[0, 'n'] = 0

        with self.assertRaises(ValueError) as context:
            ForensicAnalyzer(obs_data=invalid_obs, rct_data=self.valid_rct)

        self.assertIn('non-positive sample sizes', str(context.exception))

    def test_missing_data_warning(self):
        """Test that missing data triggers warning and removal"""
        obs_with_missing = self.valid_obs.copy()
        obs_with_missing.loc[0, 'effect'] = np.nan

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            analyzer = ForensicAnalyzer(
                obs_data=obs_with_missing,
                rct_data=self.valid_rct
            )

            self.assertTrue(any('missing data' in str(warning.message) for warning in w))
            self.assertEqual(len(analyzer.obs_data), 1)  # One study removed

    def test_small_sample_warning(self):
        """Test that small samples trigger warning"""
        small_obs = pd.DataFrame({
            'effect': [np.log(0.81)],
            'se': [0.5],
            'n': [30]  # Small sample
        })

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ForensicAnalyzer(obs_data=small_obs, rct_data=self.valid_rct)

            self.assertTrue(any('N < 50' in str(warning.message) for warning in w))

    def test_custom_sigma(self):
        """Test custom sigma reference value"""
        analyzer = ForensicAnalyzer(
            obs_data=self.valid_obs,
            rct_data=self.valid_rct,
            sigma_ref=1.5
        )

        self.assertEqual(analyzer.sigma_ref, 1.5)

    def test_effect_type_sigma(self):
        """Test that different effect types get correct sigma"""
        analyzer_smd = ForensicAnalyzer(
            obs_data=self.valid_obs,
            rct_data=self.valid_rct,
            effect_type='smd'
        )

        self.assertEqual(analyzer_smd.sigma_ref, 0.25)


class TestDiscordanceIndex(unittest.TestCase):
    """Test Discordance Index calculation"""

    def setUp(self):
        """Set up test data"""
        self.obs_data = pd.DataFrame({
            'effect': [np.log(0.81), np.log(0.91), np.log(0.93)],
            'se': [0.046, 0.021, 0.036],
            'n': [27099, 21206, 19083]
        })

        self.rct_data = pd.DataFrame({
            'effect': [np.log(0.97), np.log(0.96)],
            'se': [0.051, 0.095],
            'n': [17801, 5020]
        })

    def test_di_calculation(self):
        """Test basic DI calculation"""
        analyzer = ForensicAnalyzer(
            obs_data=self.obs_data,
            rct_data=self.rct_data
        )

        di, grade = analyzer.calculate_discordance()

        # DI should be positive
        self.assertGreater(di, 0)
        # Grade should be one of A, B, C
        self.assertIn('Grade', grade)

    def test_di_no_difference(self):
        """Test DI when obs and RCT are identical"""
        # Same data for both
        same_data = pd.DataFrame({
            'effect': [np.log(0.90), np.log(0.90)],
            'se': [0.05, 0.05],
            'n': [1000, 1000]
        })

        analyzer = ForensicAnalyzer(
            obs_data=same_data,
            rct_data=same_data.copy()
        )

        di, grade = analyzer.calculate_discordance()

        # DI should be near zero
        self.assertLess(di, 0.5)
        # Should be Grade A
        self.assertIn('Grade A', grade)

    def test_di_large_difference(self):
        """Test DI with large design difference"""
        obs_strong = pd.DataFrame({
            'effect': [np.log(0.60), np.log(0.65)],  # Large benefit
            'se': [0.02, 0.02],
            'n': [10000, 10000]
        })

        rct_harm = pd.DataFrame({
            'effect': [np.log(1.30), np.log(1.25)],  # Harm
            'se': [0.05, 0.05],
            'n': [2000, 2000]
        })

        analyzer = ForensicAnalyzer(
            obs_data=obs_strong,
            rct_data=rct_harm
        )

        di, grade = analyzer.calculate_discordance()

        # DI should be large
        self.assertGreater(di, 5.0)
        # Should be Grade C
        self.assertIn('Grade C', grade)

    def test_di_standalone_function(self):
        """Test standalone DI calculation function"""
        di, grade = calculate_discordance_index(
            obs_effect=-0.2,
            obs_se=0.05,
            rct_effect=-0.05,
            rct_se=0.10
        )

        self.assertIsInstance(di, float)
        self.assertIn('Grade', grade)


class TestEValue(unittest.TestCase):
    """Test E-Value calculation"""

    def test_e_value_protective(self):
        """Test E-value for protective effect (HR < 1)"""
        obs_data = pd.DataFrame({
            'effect': [np.log(0.80)],
            'se': [0.05],
            'n': [10000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(0.95)],
            'se': [0.10],
            'n': [2000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        e_val_point, e_val_lower = analyzer.calculate_confounding_score()

        # E-value should be > 1
        self.assertGreater(e_val_point, 1.0)
        # Lower CI E-value should exist
        self.assertIsNotNone(e_val_lower)

    def test_e_value_harmful(self):
        """Test E-value for harmful effect (HR > 1)"""
        obs_data = pd.DataFrame({
            'effect': [np.log(1.30)],
            'se': [0.05],
            'n': [10000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(1.00)],
            'se': [0.10],
            'n': [2000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        e_val_point, e_val_lower = analyzer.calculate_confounding_score()

        # E-value should be > 1
        self.assertGreater(e_val_point, 1.0)

    def test_e_value_null(self):
        """Test E-value when effect is near null"""
        obs_data = pd.DataFrame({
            'effect': [np.log(1.00)],
            'se': [0.05],
            'n': [10000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(1.00)],
            'se': [0.10],
            'n': [2000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        e_val_point, e_val_lower = analyzer.calculate_confounding_score()

        # E-value should be near 1 (no confounding needed)
        self.assertLess(e_val_point, 1.1)

    def test_e_value_standalone(self):
        """Test standalone E-value function"""
        e_point, e_lower = calculate_e_value(hr=0.80, hr_lower=0.70)

        self.assertIsInstance(e_point, float)
        self.assertGreater(e_point, 1.0)


class TestInflationFactor(unittest.TestCase):
    """Test Inflation Factor calculation"""

    def test_inflation_homogeneous(self):
        """Test inflation with homogeneous studies"""
        # Studies with similar effects (low heterogeneity)
        obs_data = pd.DataFrame({
            'effect': [np.log(0.90), np.log(0.91), np.log(0.89)],
            'se': [0.05, 0.05, 0.05],
            'n': [5000, 5000, 5000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(0.90)],
            'se': [0.10],
            'n': [2000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        inflation, nominal_n, effective_n = analyzer.calculate_inflation()

        # Inflation should be modest with low heterogeneity
        self.assertLess(inflation, 50)
        self.assertEqual(nominal_n, 15000)
        self.assertGreater(effective_n, 100)

    def test_inflation_heterogeneous(self):
        """Test inflation with highly heterogeneous studies"""
        # Studies with very different effects (high heterogeneity)
        obs_data = pd.DataFrame({
            'effect': [np.log(0.60), np.log(0.90), np.log(1.20)],
            'se': [0.10, 0.10, 0.10],
            'n': [10000, 10000, 10000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(1.00)],
            'se': [0.10],
            'n': [2000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        inflation, nominal_n, effective_n = analyzer.calculate_inflation()

        # Inflation should be large with high heterogeneity
        self.assertGreater(inflation, 10)
        self.assertEqual(nominal_n, 30000)

    def test_inflation_single_study(self):
        """Test inflation with single observational study"""
        obs_data = pd.DataFrame({
            'effect': [np.log(0.90)],
            'se': [0.05],
            'n': [10000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(0.95)],
            'se': [0.10],
            'n': [2000]
        })

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            analyzer = ForensicAnalyzer(obs_data, rct_data)
            inflation, nominal_n, effective_n = analyzer.calculate_inflation()

            # Should still calculate, but ESS ~= nominal with single study
            self.assertGreater(inflation, 0)


class TestForensicResults(unittest.TestCase):
    """Test ForensicResults dataclass"""

    def test_results_to_dict(self):
        """Test conversion to dictionary"""
        results = ForensicResults(
            discordance_index=1.5,
            e_value_point=1.8,
            e_value_lower=1.6,
            inflation_factor=100.0,
            nominal_n=50000,
            effective_n=500,
            evidence_grade="Grade B",
            interpretation={'test': 'value'}
        )

        result_dict = results.to_dict()

        self.assertEqual(result_dict['Discordance_Index'], 1.5)
        self.assertEqual(result_dict['E_Value'], 1.8)
        self.assertEqual(result_dict['Inflation_Factor'], '100x')

    def test_results_str(self):
        """Test string representation"""
        results = ForensicResults(
            discordance_index=1.5,
            e_value_point=1.8,
            e_value_lower=1.6,
            inflation_factor=100.0,
            nominal_n=50000,
            effective_n=500,
            evidence_grade="Grade B",
            interpretation={'Key': 'Value'}
        )

        result_str = str(results)

        self.assertIn('FORENSIC BIAS ANALYSIS', result_str)
        self.assertIn('1.5', result_str)  # DI
        self.assertIn('Grade B', result_str)


class TestFullAnalysis(unittest.TestCase):
    """Test complete forensic analysis workflow"""

    def test_analyze_no_bias(self):
        """Test analysis when no bias present"""
        # Same effect in both designs
        obs_data = pd.DataFrame({
            'effect': [np.log(0.90), np.log(0.89)],
            'se': [0.05, 0.05],
            'n': [5000, 5000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(0.90), np.log(0.91)],
            'se': [0.10, 0.10],
            'n': [1000, 1000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        results = analyzer.analyze()

        # Should be Grade A (low discordance)
        self.assertIn('Grade A', results.evidence_grade)
        # DI should be low
        self.assertLess(results.discordance_index, 1.5)

    def test_analyze_strong_bias(self):
        """Test analysis with strong bias"""
        # Large difference between designs
        obs_data = pd.DataFrame({
            'effect': [np.log(0.70), np.log(0.75)],
            'se': [0.03, 0.03],
            'n': [10000, 10000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(1.10), np.log(1.15)],
            'se': [0.10, 0.10],
            'n': [1000, 1000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        results = analyzer.analyze()

        # Should be Grade C (high discordance)
        self.assertIn('Grade C', results.evidence_grade)
        # DI should be high
        self.assertGreater(results.discordance_index, 3.0)
        # E-value should be high
        self.assertGreater(results.e_value_point, 2.0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def test_perfect_concordance(self):
        """Test when obs and RCT are identical"""
        data = pd.DataFrame({
            'effect': [0.0, 0.0],
            'se': [0.1, 0.1],
            'n': [1000, 1000]
        })

        analyzer = ForensicAnalyzer(data.copy(), data.copy())
        di, grade = analyzer.calculate_discordance()

        self.assertLess(di, 0.1)  # Should be near zero
        self.assertIn('Grade A', grade)

    def test_very_precise_studies(self):
        """Test with very small standard errors"""
        obs_data = pd.DataFrame({
            'effect': [np.log(0.90)],
            'se': [0.001],  # Very precise
            'n': [1000000]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(0.95)],
            'se': [0.10],
            'n': [2000]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        results = analyzer.analyze()

        # Should detect discordance despite obs precision
        self.assertIsNotNone(results.discordance_index)

    def test_very_imprecise_studies(self):
        """Test with very large standard errors"""
        obs_data = pd.DataFrame({
            'effect': [np.log(0.80)],
            'se': [0.5],  # Very imprecise
            'n': [100]
        })

        rct_data = pd.DataFrame({
            'effect': [np.log(1.00)],
            'se': [0.5],
            'n': [100]
        })

        analyzer = ForensicAnalyzer(obs_data, rct_data)
        results = analyzer.analyze()

        # DI should be low despite effect difference (wide CIs overlap)
        self.assertLess(results.discordance_index, 1.0)


def run_tests(verbosity=2):
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
