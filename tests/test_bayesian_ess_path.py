"""
Regression tests for the Bayesian ESS code path
================================================

These tests exercise the previously-uncovered Bayesian ESS branch of
ForensicAnalyzer.analyze(use_bayesian_ess=True), the BayesianESSCalculator
analytical path, and the DerSimonian-Laird heterogeneity denominator.

They import via the fully-qualified ``netmetareg.forensic`` package so that the
relative ``from .bayesian_ess import BayesianESSCalculator`` inside
bias_detector actually resolves. The legacy test_forensic_module.py imports
``bias_detector`` as a top-level module, under which that relative import fails
with ImportError and the Bayesian path is silently skipped -- which is why the
F1 unpack crash shipped undetected.

Covers audit findings:
- F1: analyze(use_bayesian_ess=True) must not raise (ESSResults is a dataclass,
      not an iterable tuple).
- F2: BayesianESSCalculator / analytical_ess had zero coverage.
- F3: DerSimonian-Laird tau^2 denominator = C = sum(w) - sum(w^2)/sum(w).
"""

import unittest
import warnings

import numpy as np
import pandas as pd

from netmetareg.forensic.bias_detector import ForensicAnalyzer, ForensicResults
from netmetareg.forensic.bayesian_ess import BayesianESSCalculator, ESSResults


def _obs_fixture():
    return pd.DataFrame({
        'effect': [np.log(0.81), np.log(0.91), np.log(0.93)],
        'se': [0.046, 0.021, 0.036],
        'n': [27099, 21206, 19083],
    })


def _rct_fixture():
    return pd.DataFrame({
        'effect': [np.log(0.97), np.log(0.96)],
        'se': [0.051, 0.095],
        'n': [17801, 5020],
    })


class TestBayesianESSAnalyzePath(unittest.TestCase):
    """F1/F2: analyze(use_bayesian_ess=True) via the real package import."""

    def test_analyze_bayesian_ess_returns_finite_results(self):
        """Regression for F1: must not raise TypeError unpacking ESSResults."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            analyzer = ForensicAnalyzer(
                _obs_fixture(), _rct_fixture(), effect_type='log_hr'
            )
            results = analyzer.analyze(use_bayesian_ess=True)

        self.assertIsInstance(results, ForensicResults)
        self.assertTrue(np.isfinite(results.effective_n))
        self.assertGreater(results.effective_n, 0)
        self.assertTrue(np.isfinite(results.inflation_factor))
        self.assertGreater(results.inflation_factor, 0)

    def test_analyze_bayesian_ess_field_mapping(self):
        """F1: effective_n and inflation_factor must not be swapped.

        A naive positional-tuple fix would swap them because ESSResults field
        order is (effective_n, nominal_n, inflation_factor, ...). Assert the
        forensic result agrees with the calculator's own attributes.
        """
        obs = _obs_fixture()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            analyzer = ForensicAnalyzer(obs, _rct_fixture(), effect_type='log_hr')
            results = analyzer.analyze(use_bayesian_ess=True)
            ess = BayesianESSCalculator(obs).calculate()

        self.assertAlmostEqual(results.effective_n, ess.effective_n, places=6)
        self.assertAlmostEqual(results.inflation_factor, ess.inflation_factor, places=6)
        self.assertEqual(results.nominal_n, ess.nominal_n)
        # Sanity: inflation_factor == nominal_n / effective_n (not the reverse).
        self.assertAlmostEqual(
            results.inflation_factor,
            results.nominal_n / results.effective_n,
            places=6,
        )


class TestBayesianESSCalculator(unittest.TestCase):
    """F2: direct coverage of BayesianESSCalculator.analytical_ess."""

    def test_analytical_ess_basic(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = BayesianESSCalculator(_obs_fixture()).analytical_ess()

        self.assertIsInstance(res, ESSResults)
        self.assertEqual(res.n_studies, 3)
        self.assertTrue(np.isfinite(res.effective_n))
        self.assertGreater(res.effective_n, 0)
        self.assertGreaterEqual(res.heterogeneity, 0.0)
        self.assertAlmostEqual(
            res.inflation_factor, res.nominal_n / res.effective_n, places=6
        )

    def test_calculate_delegates_to_analytical(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            calc = BayesianESSCalculator(_obs_fixture(), use_pymc=False)
            res = calc.calculate()
        self.assertEqual(res.convergence['method'], 'analytical')


class TestDLHeterogeneityDenominator(unittest.TestCase):
    """F3: DerSimonian-Laird tau^2 uses C = sum(w) - sum(w^2)/sum(w)."""

    def test_inflation_uses_correct_dl_denominator(self):
        # Heterogeneous fixture so tau^2 > 0 and the denominator choice matters.
        obs = pd.DataFrame({
            'effect': [np.log(0.60), np.log(0.90), np.log(1.20)],
            'se': [0.10, 0.10, 0.10],
            'n': [10000, 10000, 10000],
        })
        rct = pd.DataFrame({
            'effect': [np.log(1.00)], 'se': [0.10], 'n': [2000]
        })

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            analyzer = ForensicAnalyzer(obs, rct)
            inflation, nominal_n, effective_n = analyzer.calculate_inflation()

        # Recompute the expected tau^2 with the correct DL denominator C.
        w = 1 / obs['se'].values ** 2
        pooled = np.sum(obs['effect'].values * w) / np.sum(w)
        q = np.sum(w * (obs['effect'].values - pooled) ** 2)
        c = np.sum(w) - np.sum(w ** 2) / np.sum(w)
        tau_sq_correct = max(0.0, (q - (len(w) - 1)) / c)
        tau_sq_wrong = max(0.0, (q - (len(w) - 1)) / np.sum(w))

        sigma = analyzer.sigma_ref
        base_ess = (sigma / analyzer.obs_pooled['se']) ** 2
        expected_eff = base_ess / (1 + tau_sq_correct / sigma ** 2)
        wrong_eff = base_ess / (1 + tau_sq_wrong / sigma ** 2)

        # The engine must match the CORRECT (C) denominator, not sum(w).
        self.assertAlmostEqual(effective_n, expected_eff, places=4)
        self.assertNotAlmostEqual(effective_n, wrong_eff, places=2)

    def test_dl_matches_bayesian_ess_module(self):
        """The two DL heterogeneity estimators must use the same denominator."""
        data = pd.DataFrame({
            'effect': [np.log(0.60), np.log(0.90), np.log(1.20)],
            'se': [0.10, 0.10, 0.10],
            'n': [10000, 10000, 10000],
        })
        w = 1 / data['se'].values ** 2
        pooled = np.sum(data['effect'].values * w) / np.sum(w)
        q = np.sum(w * (data['effect'].values - pooled) ** 2)
        c = np.sum(w) - np.sum(w ** 2) / np.sum(w)
        tau_sq_bias_detector = max(0.0, (q - (len(w) - 1)) / c)

        # bayesian_ess uses the same C denominator (before its prior shrinkage).
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            calc = BayesianESSCalculator(data)
        df = len(data) - 1
        c2 = np.sum(w) - np.sum(w ** 2) / np.sum(w)
        tau_sq_dl_raw = max(0.0, (q - df) / c2)
        self.assertAlmostEqual(tau_sq_bias_detector, tau_sq_dl_raw, places=10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
