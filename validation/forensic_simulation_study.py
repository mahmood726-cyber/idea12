"""
Forensic Meta-Analysis Framework: Validation Simulation Studies
================================================================

This script runs comprehensive simulation studies to validate the three
forensic metrics (Discordance Index, E-Value, Inflation Factor).

Four scenarios:
1. No bias (obs = RCT)
2. Weak bias (small confounding)
3. Moderate bias (medium confounding)
4. Strong bias (medical reversal)

Each scenario run 1000 times with different random seeds.

Author: Validation team
Date: January 2025
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import sys
import os
from dataclasses import dataclass
from tqdm import tqdm
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from netmetareg.forensic import ForensicAnalyzer
    FORENSIC_AVAILABLE = True
except ImportError:
    FORENSIC_AVAILABLE = False
    print("Warning: Forensic module not available. Running simulation only.")


@dataclass
class SimulationScenario:
    """Configuration for simulation scenario"""
    name: str
    true_rct_hr: float
    true_obs_hr: float
    tau_sq: float
    n_obs_studies: int
    n_rct_studies: int
    obs_sample_sizes: List[int]
    rct_sample_sizes: List[int]
    expected_di_range: Tuple[float, float]
    expected_e_value: float


class ForensicSimulator:
    """
    Simulation framework for forensic metrics validation

    Generates synthetic meta-analyses with known truth to assess:
    - Discordance Index calibration
    - E-value accuracy
    - Inflation Factor precision
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def generate_study_effects(
        self,
        true_effect: float,
        n_studies: int,
        sample_sizes: List[int],
        tau: float
    ) -> pd.DataFrame:
        """
        Generate study-level effects with heterogeneity

        Parameters
        ----------
        true_effect : float
            True log-HR
        n_studies : int
            Number of studies
        sample_sizes : list
            Sample sizes for each study
        tau : float
            Between-study SD

        Returns
        -------
        data : DataFrame
            Study-level data with effect, se, n
        """
        # Generate true study-specific effects
        if n_studies != len(sample_sizes):
            # Replicate sample sizes if needed
            sample_sizes = sample_sizes * (n_studies // len(sample_sizes) + 1)
            sample_sizes = sample_sizes[:n_studies]

        # Study-specific true effects (with heterogeneity)
        study_effects = self.rng.normal(
            loc=true_effect,
            scale=tau,
            size=n_studies
        )

        # Calculate standard errors based on sample size
        # SE ≈ sqrt(4/N) for log-HR (rule of thumb)
        standard_errors = np.sqrt(4 / np.array(sample_sizes))

        # Generate observed effects (add sampling error)
        observed_effects = self.rng.normal(
            loc=study_effects,
            scale=standard_errors
        )

        return pd.DataFrame({
            'study': [f'Study_{i+1}' for i in range(n_studies)],
            'effect': observed_effects,
            'se': standard_errors,
            'n': sample_sizes,
            'true_effect': study_effects
        })

    def run_single_simulation(
        self,
        scenario: SimulationScenario,
        iteration: int
    ) -> Dict:
        """
        Run a single simulation iteration

        Returns
        -------
        results : dict
            Contains DI, E-value, Inflation, and truth
        """
        # Set seed for reproducibility
        self.rng = np.random.RandomState(self.seed + iteration)

        # Generate observational studies
        obs_data = self.generate_study_effects(
            true_effect=np.log(scenario.true_obs_hr),
            n_studies=scenario.n_obs_studies,
            sample_sizes=scenario.obs_sample_sizes,
            tau=np.sqrt(scenario.tau_sq)
        )

        # Generate RCT studies
        rct_data = self.generate_study_effects(
            true_effect=np.log(scenario.true_rct_hr),
            n_studies=scenario.n_rct_studies,
            sample_sizes=scenario.rct_sample_sizes,
            tau=np.sqrt(scenario.tau_sq)
        )

        # Calculate forensic metrics
        if FORENSIC_AVAILABLE:
            analyzer = ForensicAnalyzer(
                obs_data=obs_data[['effect', 'se', 'n']],
                rct_data=rct_data[['effect', 'se', 'n']],
                effect_type='log_hr',
                rare_outcome=False
            )

            forensic_results = analyzer.analyze(use_bayesian_ess=False)

            return {
                'iteration': iteration,
                'scenario': scenario.name,
                'di': forensic_results.discordance_index,
                'e_value': forensic_results.e_value_point,
                'inflation': forensic_results.inflation_factor,
                'nominal_n': forensic_results.nominal_n,
                'effective_n': forensic_results.effective_n,
                'grade': forensic_results.evidence_grade,
                'true_obs_hr': scenario.true_obs_hr,
                'true_rct_hr': scenario.true_rct_hr,
                'true_confounding_rr': scenario.true_obs_hr / scenario.true_rct_hr,
                'obs_pooled_hr': np.exp(analyzer.obs_pooled['effect']),
                'rct_pooled_hr': np.exp(analyzer.rct_pooled['effect'])
            }
        else:
            # Manual calculation for validation
            return self._calculate_metrics_manual(obs_data, rct_data, scenario, iteration)

    def _calculate_metrics_manual(
        self,
        obs_data: pd.DataFrame,
        rct_data: pd.DataFrame,
        scenario: SimulationScenario,
        iteration: int
    ) -> Dict:
        """Manual metric calculation when forensic module unavailable"""
        # Pool studies using inverse-variance weighting
        def pool(data):
            weights = 1 / (data['se'] ** 2)
            effect = np.sum(data['effect'] * weights) / np.sum(weights)
            se = np.sqrt(1 / np.sum(weights))
            return effect, se

        obs_effect, obs_se = pool(obs_data)
        rct_effect, rct_se = pool(rct_data)

        # Discordance Index
        diff = abs(obs_effect - rct_effect)
        combined_se = np.sqrt(obs_se**2 + rct_se**2)
        di = diff / combined_se

        # E-value (simplified)
        obs_hr = np.exp(obs_effect)
        if obs_hr < 1:
            hr_inv = 1 / obs_hr
            e_value = hr_inv + np.sqrt(hr_inv * (hr_inv - 1))
        else:
            e_value = obs_hr + np.sqrt(obs_hr * (obs_hr - 1))

        # Inflation (simplified)
        nominal_n = obs_data['n'].sum()
        effective_n = (2.0 / obs_se) ** 2
        inflation = nominal_n / effective_n

        # Grade
        if di < 1.0:
            grade = "Grade A"
        elif di < 2.0:
            grade = "Grade B"
        else:
            grade = "Grade C"

        return {
            'iteration': iteration,
            'scenario': scenario.name,
            'di': di,
            'e_value': e_value,
            'inflation': inflation,
            'nominal_n': int(nominal_n),
            'effective_n': effective_n,
            'grade': grade,
            'true_obs_hr': scenario.true_obs_hr,
            'true_rct_hr': scenario.true_rct_hr,
            'true_confounding_rr': scenario.true_obs_hr / scenario.true_rct_hr,
            'obs_pooled_hr': np.exp(obs_effect),
            'rct_pooled_hr': np.exp(rct_effect)
        }

    def run_scenario(
        self,
        scenario: SimulationScenario,
        n_iterations: int = 1000,
        show_progress: bool = True
    ) -> pd.DataFrame:
        """
        Run complete simulation for one scenario

        Parameters
        ----------
        scenario : SimulationScenario
            Scenario configuration
        n_iterations : int
            Number of simulation iterations
        show_progress : bool
            Show progress bar

        Returns
        -------
        results : DataFrame
            Results from all iterations
        """
        results = []

        iterator = range(n_iterations)
        if show_progress:
            iterator = tqdm(iterator, desc=f"Scenario: {scenario.name}")

        for i in iterator:
            try:
                result = self.run_single_simulation(scenario, i)
                results.append(result)
            except Exception as e:
                print(f"Error in iteration {i}: {e}")
                continue

        return pd.DataFrame(results)


def define_scenarios() -> List[SimulationScenario]:
    """Define the four validation scenarios"""

    scenarios = [
        SimulationScenario(
            name="No_Bias",
            true_rct_hr=0.90,
            true_obs_hr=0.90,  # Same as RCT
            tau_sq=0.04,
            n_obs_studies=5,
            n_rct_studies=3,
            obs_sample_sizes=[5000, 10000, 15000, 20000, 8000],
            rct_sample_sizes=[500, 1000, 2000],
            expected_di_range=(0.0, 1.0),
            expected_e_value=1.0
        ),

        SimulationScenario(
            name="Weak_Bias",
            true_rct_hr=0.95,
            true_obs_hr=0.85,  # ~12% confounding (RR ≈ 1.12)
            tau_sq=0.04,
            n_obs_studies=5,
            n_rct_studies=3,
            obs_sample_sizes=[5000, 10000, 15000, 20000, 8000],
            rct_sample_sizes=[500, 1000, 2000],
            expected_di_range=(0.8, 1.5),
            expected_e_value=1.5
        ),

        SimulationScenario(
            name="Moderate_Bias",
            true_rct_hr=1.00,
            true_obs_hr=0.80,  # 25% confounding (RR = 1.25)
            tau_sq=0.04,
            n_obs_studies=5,
            n_rct_studies=3,
            obs_sample_sizes=[5000, 10000, 15000, 20000, 8000],
            rct_sample_sizes=[500, 1000, 2000],
            expected_di_range=(1.5, 2.5),
            expected_e_value=2.0
        ),

        SimulationScenario(
            name="Strong_Bias",
            true_rct_hr=1.20,  # Harm
            true_obs_hr=0.70,  # Apparent benefit
            tau_sq=0.04,
            n_obs_studies=5,
            n_rct_studies=3,
            obs_sample_sizes=[5000, 10000, 15000, 20000, 8000],
            rct_sample_sizes=[500, 1000, 2000],
            expected_di_range=(3.0, 5.0),
            expected_e_value=3.0
        )
    ]

    return scenarios


def analyze_simulation_results(results: pd.DataFrame) -> Dict:
    """
    Analyze simulation results and compute performance metrics

    Parameters
    ----------
    results : DataFrame
        Results from all simulations

    Returns
    -------
    summary : dict
        Performance metrics
    """
    summary = {}

    # Discordance Index statistics
    summary['di_mean'] = results['di'].mean()
    summary['di_sd'] = results['di'].std()
    summary['di_median'] = results['di'].median()
    summary['di_q25'] = results['di'].quantile(0.25)
    summary['di_q75'] = results['di'].quantile(0.75)

    # Grade distribution
    grade_counts = results['grade'].value_counts()
    total = len(results)
    summary['grade_a_pct'] = (grade_counts.get('Grade A', 0) / total) * 100
    summary['grade_b_pct'] = (grade_counts.get('Grade B', 0) / total) * 100
    summary['grade_c_pct'] = (grade_counts.get('Grade C', 0) / total) * 100

    # E-value accuracy
    if 'true_confounding_rr' in results.columns:
        # Compare estimated E-value to true confounding strength
        true_conf = results['true_confounding_rr'].iloc[0]
        if true_conf < 1:
            true_conf = 1 / true_conf

        summary['e_value_mean'] = results['e_value'].mean()
        summary['e_value_sd'] = results['e_value'].std()
        summary['e_value_bias'] = results['e_value'].mean() - true_conf
        summary['e_value_rmse'] = np.sqrt(np.mean((results['e_value'] - true_conf) ** 2))

    # Inflation Factor
    summary['inflation_mean'] = results['inflation'].mean()
    summary['inflation_sd'] = results['inflation'].std()
    summary['inflation_median'] = results['inflation'].median()

    # Coverage probabilities (for Discordance Index)
    # Under null, DI should be < 1.96 in 95% of cases
    summary['di_lt_1_pct'] = (results['di'] < 1.0).mean() * 100
    summary['di_lt_2_pct'] = (results['di'] < 2.0).mean() * 100

    return summary


def run_all_simulations(
    n_iterations: int = 1000,
    output_dir: str = './validation/results',
    save_raw: bool = True
) -> pd.DataFrame:
    """
    Run all four simulation scenarios

    Parameters
    ----------
    n_iterations : int
        Number of iterations per scenario
    output_dir : str
        Directory to save results
    save_raw : bool
        Save raw iteration data

    Returns
    -------
    summary : DataFrame
        Summary statistics for all scenarios
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize simulator
    simulator = ForensicSimulator(seed=42)

    # Get scenarios
    scenarios = define_scenarios()

    # Run simulations
    all_results = []
    summary_data = []

    print("="*80)
    print("FORENSIC META-ANALYSIS: VALIDATION SIMULATION STUDY")
    print("="*80)
    print(f"\nRunning {len(scenarios)} scenarios × {n_iterations} iterations = {len(scenarios) * n_iterations} total")
    print(f"Estimated time: ~{len(scenarios) * n_iterations * 0.05 / 60:.1f} minutes\n")

    for scenario in scenarios:
        print(f"\n{'='*80}")
        print(f"Scenario: {scenario.name}")
        print(f"  True RCT HR: {scenario.true_rct_hr:.2f}")
        print(f"  True Obs HR: {scenario.true_obs_hr:.2f}")
        print(f"  Expected DI range: {scenario.expected_di_range}")
        print(f"{'='*80}\n")

        # Run scenario
        results = simulator.run_scenario(scenario, n_iterations, show_progress=True)
        all_results.append(results)

        # Analyze results
        summary = analyze_simulation_results(results)
        summary['scenario'] = scenario.name
        summary['n_iterations'] = len(results)
        summary_data.append(summary)

        # Save raw data if requested
        if save_raw:
            raw_file = os.path.join(output_dir, f'{scenario.name}_raw.csv')
            results.to_csv(raw_file, index=False)
            print(f"\nSaved raw data to: {raw_file}")

        # Print summary
        print(f"\nResults for {scenario.name}:")
        print(f"  DI: {summary['di_mean']:.2f} ± {summary['di_sd']:.2f}")
        print(f"  Grades: A={summary['grade_a_pct']:.1f}%, B={summary['grade_b_pct']:.1f}%, C={summary['grade_c_pct']:.1f}%")
        if 'e_value_mean' in summary:
            print(f"  E-value: {summary['e_value_mean']:.2f} ± {summary['e_value_sd']:.2f}")
            print(f"  E-value bias: {summary['e_value_bias']:.2f}, RMSE: {summary['e_value_rmse']:.2f}")
        print(f"  Inflation: {summary['inflation_mean']:.1f}x ± {summary['inflation_sd']:.1f}x")

    # Create summary dataframe
    summary_df = pd.DataFrame(summary_data)

    # Save summary
    summary_file = os.path.join(output_dir, 'simulation_summary.csv')
    summary_df.to_csv(summary_file, index=False)
    print(f"\n{'='*80}")
    print(f"Summary saved to: {summary_file}")
    print(f"{'='*80}\n")

    # Save configuration
    config = {
        'n_iterations': n_iterations,
        'seed': 42,
        'scenarios': [
            {
                'name': s.name,
                'true_rct_hr': s.true_rct_hr,
                'true_obs_hr': s.true_obs_hr,
                'tau_sq': s.tau_sq
            } for s in scenarios
        ],
        'timestamp': pd.Timestamp.now().isoformat()
    }

    config_file = os.path.join(output_dir, 'simulation_config.json')
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    return summary_df


def generate_validation_report(summary_df: pd.DataFrame, output_dir: str = './validation/results'):
    """Generate formatted validation report"""

    report = []
    report.append("="*80)
    report.append("FORENSIC META-ANALYSIS FRAMEWORK: VALIDATION RESULTS")
    report.append("="*80)
    report.append("")
    report.append(f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Iterations per scenario: {int(summary_df['n_iterations'].iloc[0])}")
    report.append("")

    # Table 1: Discordance Index Performance
    report.append("TABLE 1: Discordance Index Performance")
    report.append("-"*80)
    report.append(f"{'Scenario':<20} {'Mean DI':>10} {'SD':>8} {'Grade A%':>10} {'Grade B%':>10} {'Grade C%':>10}")
    report.append("-"*80)

    for _, row in summary_df.iterrows():
        report.append(
            f"{row['scenario']:<20} "
            f"{row['di_mean']:>10.2f} "
            f"{row['di_sd']:>8.2f} "
            f"{row['grade_a_pct']:>10.1f} "
            f"{row['grade_b_pct']:>10.1f} "
            f"{row['grade_c_pct']:>10.1f}"
        )
    report.append("-"*80)
    report.append("")

    # Table 2: E-Value Accuracy
    if 'e_value_mean' in summary_df.columns:
        report.append("TABLE 2: E-Value Calibration")
        report.append("-"*80)
        report.append(f"{'Scenario':<20} {'E-Value':>12} {'Bias':>10} {'RMSE':>10}")
        report.append("-"*80)

        for _, row in summary_df.iterrows():
            if pd.notna(row.get('e_value_mean')):
                report.append(
                    f"{row['scenario']:<20} "
                    f"{row['e_value_mean']:>12.2f} "
                    f"{row.get('e_value_bias', 0):>10.2f} "
                    f"{row.get('e_value_rmse', 0):>10.2f}"
                )
        report.append("-"*80)
        report.append("")

    # Interpretation
    report.append("INTERPRETATION:")
    report.append("-"*80)

    no_bias = summary_df[summary_df['scenario'] == 'No_Bias'].iloc[0]
    report.append(f"1. Type I Error (No Bias scenario):")
    report.append(f"   Grade C assigned: {no_bias['grade_c_pct']:.1f}% (target: <5%)")
    report.append(f"   Status: {'PASS' if no_bias['grade_c_pct'] < 5 else 'FAIL'}")
    report.append("")

    strong_bias = summary_df[summary_df['scenario'] == 'Strong_Bias'].iloc[0]
    report.append(f"2. Sensitivity (Strong Bias scenario):")
    report.append(f"   Grade C assigned: {strong_bias['grade_c_pct']:.1f}% (target: >90%)")
    report.append(f"   Status: {'PASS' if strong_bias['grade_c_pct'] > 90 else 'FAIL'}")
    report.append("")

    report.append("="*80)

    # Save report
    report_text = "\n".join(report)
    print(report_text)

    report_file = os.path.join(output_dir, 'VALIDATION_REPORT.txt')
    with open(report_file, 'w') as f:
        f.write(report_text)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run forensic framework validation simulations')
    parser.add_argument('--iterations', type=int, default=1000, help='Number of iterations per scenario')
    parser.add_argument('--quick', action='store_true', help='Quick test with 100 iterations')
    parser.add_argument('--output', type=str, default='./validation/results', help='Output directory')

    args = parser.parse_args()

    n_iter = 100 if args.quick else args.iterations

    # Run simulations
    summary = run_all_simulations(
        n_iterations=n_iter,
        output_dir=args.output,
        save_raw=True
    )

    # Generate report
    generate_validation_report(summary, args.output)

    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
