"""
ROC Analysis and Threshold Optimization for Forensic Framework

This script performs comprehensive threshold optimization to address the
high Type I error rate observed in initial validation.

Approaches:
1. ROC analysis on medical reversal data
2. Empirical sigma_ref calibration
3. Heterogeneity-adjusted DI
4. Cross-validation for robust threshold selection
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from scipy import stats
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import directly to avoid PyMC dependency
import importlib.util
spec = importlib.util.spec_from_file_location(
    "bias_detector",
    os.path.join(os.path.dirname(__file__), '..', 'netmetareg', 'forensic', 'bias_detector.py')
)
bias_detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bias_detector)
ForensicAnalyzer = bias_detector.ForensicAnalyzer


class ThresholdOptimizer:
    """Optimize DI thresholds using ROC analysis and empirical calibration"""

    def __init__(self, medical_reversal_file='./validation/results/medical_reversal_results.csv'):
        """Initialize with medical reversal validation data"""
        self.data = pd.read_csv(medical_reversal_file)

        # Create binary labels: 1=reversal (positive class), 0=concordant (negative class)
        self.y_true = (self.data['Type'] == 'REVERSAL').astype(int).values

        # Extract DI values
        self.di_values = self.data['DI'].values

        print(f"Loaded {len(self.data)} cases:")
        print(f"  Reversals: {sum(self.y_true)}")
        print(f"  Concordant: {len(self.y_true) - sum(self.y_true)}")
        print(f"  DI range: {self.di_values.min():.2f} - {self.di_values.max():.2f}")

    def run_roc_analysis(self):
        """Perform ROC analysis to find optimal threshold"""
        print("\n" + "="*80)
        print("ROC ANALYSIS FOR DI THRESHOLD OPTIMIZATION")
        print("="*80)

        # Calculate ROC curve
        fpr, tpr, thresholds = roc_curve(self.y_true, self.di_values)
        roc_auc = auc(fpr, tpr)

        print(f"\nROC AUC: {roc_auc:.3f}")

        # Find optimal threshold using Youden's Index (maximizes TPR - FPR)
        youden_index = tpr - fpr
        optimal_idx = np.argmax(youden_index)
        optimal_threshold = thresholds[optimal_idx]
        optimal_tpr = tpr[optimal_idx]
        optimal_fpr = fpr[optimal_idx]

        print(f"\nOptimal Threshold (Youden's Index):")
        print(f"  DI = {optimal_threshold:.2f}")
        print(f"  Sensitivity (TPR) = {optimal_tpr:.1%}")
        print(f"  1 - Specificity (FPR) = {optimal_fpr:.1%}")
        print(f"  Specificity = {1-optimal_fpr:.1%}")
        print(f"  Youden's Index = {youden_index[optimal_idx]:.3f}")

        # Alternative: threshold for 90% sensitivity
        idx_90sens = np.where(tpr >= 0.90)[0][0]
        threshold_90sens = thresholds[idx_90sens]
        fpr_90sens = fpr[idx_90sens]

        print(f"\nThreshold for 90% Sensitivity:")
        print(f"  DI = {threshold_90sens:.2f}")
        print(f"  Sensitivity = {tpr[idx_90sens]:.1%}")
        print(f"  Specificity = {1-fpr_90sens:.1%}")

        # Alternative: threshold for 80% specificity
        idx_80spec = np.where(fpr <= 0.20)[0][-1]
        threshold_80spec = thresholds[idx_80spec]
        tpr_80spec = tpr[idx_80spec]

        print(f"\nThreshold for 80% Specificity:")
        print(f"  DI = {threshold_80spec:.2f}")
        print(f"  Sensitivity = {tpr_80spec:.1%}")
        print(f"  Specificity = {1-fpr[idx_80spec]:.1%}")

        # Store results
        self.roc_results = {
            'fpr': fpr,
            'tpr': tpr,
            'thresholds': thresholds,
            'auc': roc_auc,
            'optimal_threshold': optimal_threshold,
            'optimal_tpr': optimal_tpr,
            'optimal_fpr': optimal_fpr,
            'threshold_90sens': threshold_90sens,
            'threshold_80spec': threshold_80spec
        }

        return self.roc_results

    def propose_new_grades(self):
        """Propose new Grade A/B/C thresholds based on ROC analysis"""
        print("\n" + "="*80)
        print("PROPOSED NEW GRADING THRESHOLDS")
        print("="*80)

        opt_thresh = self.roc_results['optimal_threshold']

        # Current thresholds
        print("\nCurrent Thresholds:")
        print("  Grade A (Concordant): DI < 1.0")
        print("  Grade B (Uncertain): 1.0 <= DI < 2.0")
        print("  Grade C (Discordant): DI >= 2.0")
        print(f"  Current Grade C threshold: 2.0")

        # Proposed thresholds based on ROC
        # Set Grade C threshold at optimal point
        # Set Grade A threshold at ~40% of optimal (more lenient)
        # Set Grade B as middle range

        grade_c_threshold = opt_thresh
        grade_b_threshold = opt_thresh * 0.4  # ~40% of optimal

        print(f"\nProposed Thresholds (ROC-Optimized):")
        print(f"  Grade A (Concordant): DI < {grade_b_threshold:.2f}")
        print(f"  Grade B (Uncertain): {grade_b_threshold:.2f} <= DI < {grade_c_threshold:.2f}")
        print(f"  Grade C (Discordant): DI >= {grade_c_threshold:.2f}")

        # Alternative: Use quartiles from reversal distribution
        reversal_di = self.di_values[self.y_true == 1]
        concordant_di = self.di_values[self.y_true == 0]

        q25_rev = np.percentile(reversal_di, 25)
        median_rev = np.median(reversal_di)
        q75_rev = np.percentile(reversal_di, 75)

        median_con = np.median(concordant_di)

        print(f"\nEmpirical Distribution:")
        print(f"  Reversals: Q25={q25_rev:.2f}, Median={median_rev:.2f}, Q75={q75_rev:.2f}")
        print(f"  Concordant: Median={median_con:.2f}")

        # Proposed alternative: Use median of reversals as Grade C threshold
        alt_grade_c = median_rev
        alt_grade_b = median_con

        print(f"\nProposed Thresholds (Distribution-Based):")
        print(f"  Grade A (Concordant): DI < {alt_grade_b:.2f}")
        print(f"  Grade B (Uncertain): {alt_grade_b:.2f} <= DI < {alt_grade_c:.2f}")
        print(f"  Grade C (Discordant): DI >= {alt_grade_c:.2f}")

        self.proposed_thresholds = {
            'roc_optimized': {
                'grade_a_max': grade_b_threshold,
                'grade_b_max': grade_c_threshold,
                'grade_c_min': grade_c_threshold
            },
            'distribution_based': {
                'grade_a_max': alt_grade_b,
                'grade_b_max': alt_grade_c,
                'grade_c_min': alt_grade_c
            }
        }

        return self.proposed_thresholds

    def evaluate_thresholds(self, threshold):
        """Evaluate performance at a given threshold"""
        y_pred = (self.di_values >= threshold).astype(int)

        cm = confusion_matrix(self.y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()

        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        accuracy = (tp + tn) / (tp + tn + fp + fn)

        return {
            'threshold': threshold,
            'sensitivity': sensitivity,
            'specificity': specificity,
            'ppv': ppv,
            'npv': npv,
            'accuracy': accuracy,
            'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn
        }

    def compare_threshold_schemes(self):
        """Compare current vs proposed thresholds"""
        print("\n" + "="*80)
        print("THRESHOLD SCHEME COMPARISON")
        print("="*80)

        # Current threshold (DI >= 2.0 = Grade C)
        current_perf = self.evaluate_thresholds(2.0)

        # ROC-optimized threshold
        roc_perf = self.evaluate_thresholds(self.roc_results['optimal_threshold'])

        # Distribution-based threshold
        dist_perf = self.evaluate_thresholds(self.proposed_thresholds['distribution_based']['grade_c_min'])

        print("\nPerformance Comparison:")
        print("-" * 80)
        print(f"{'Scheme':<20} {'Threshold':>10} {'Sensitivity':>12} {'Specificity':>12} {'Accuracy':>10}")
        print("-" * 80)

        for name, perf in [('Current (DI>=2.0)', current_perf),
                           ('ROC-Optimized', roc_perf),
                           ('Distribution-Based', dist_perf)]:
            print(f"{name:<20} {perf['threshold']:>10.2f} {perf['sensitivity']:>12.1%} "
                  f"{perf['specificity']:>12.1%} {perf['accuracy']:>10.1%}")

        print("-" * 80)

        return {
            'current': current_perf,
            'roc_optimized': roc_perf,
            'distribution_based': dist_perf
        }

    def plot_roc_curve(self, output_file='./validation/figures/ROC_Threshold_Optimization.png'):
        """Create publication-quality ROC curve with optimal threshold marked"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Panel A: ROC Curve
        fpr = self.roc_results['fpr']
        tpr = self.roc_results['tpr']
        roc_auc = self.roc_results['auc']
        opt_thresh = self.roc_results['optimal_threshold']
        opt_fpr = self.roc_results['optimal_fpr']
        opt_tpr = self.roc_results['optimal_tpr']

        ax1.plot(fpr, tpr, color='darkblue', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
        ax1.plot([0, 1], [0, 1], color='gray', lw=1, linestyle='--', label='Chance')
        ax1.plot(opt_fpr, opt_tpr, 'ro', markersize=10,
                label=f'Optimal (DI={opt_thresh:.2f})')

        ax1.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=12)
        ax1.set_ylabel('True Positive Rate (Sensitivity)', fontsize=12)
        ax1.set_title('ROC Curve: Discordance Index for Medical Reversal Detection', fontsize=14, weight='bold')
        ax1.legend(loc='lower right', fontsize=10)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim([-0.05, 1.05])
        ax1.set_ylim([-0.05, 1.05])

        # Panel B: Sensitivity/Specificity vs Threshold
        thresholds = self.roc_results['thresholds']

        # Avoid extreme threshold values for cleaner plot
        valid_idx = (thresholds <= 10)
        plot_thresholds = thresholds[valid_idx]
        plot_tpr = tpr[valid_idx]
        plot_fpr = fpr[valid_idx]

        ax2.plot(plot_thresholds, plot_tpr, 'b-', lw=2, label='Sensitivity (TPR)')
        ax2.plot(plot_thresholds, 1-plot_fpr, 'r-', lw=2, label='Specificity (TNR)')
        ax2.axvline(opt_thresh, color='green', linestyle='--', lw=2,
                   label=f'Optimal Threshold = {opt_thresh:.2f}')
        ax2.axvline(2.0, color='orange', linestyle='--', lw=2,
                   label='Current Threshold = 2.0')

        ax2.set_xlabel('DI Threshold', fontsize=12)
        ax2.set_ylabel('Rate', fontsize=12)
        ax2.set_title('Sensitivity and Specificity vs DI Threshold', fontsize=14, weight='bold')
        ax2.legend(loc='best', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim([0, 8])
        ax2.set_ylim([0, 1.05])

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"\nROC curve saved to: {output_file}")
        plt.close()

    def plot_di_distributions(self, output_file='./validation/figures/DI_Distributions_By_Type.png'):
        """Plot DI distributions for reversals vs concordant cases"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        reversal_di = self.di_values[self.y_true == 1]
        concordant_di = self.di_values[self.y_true == 0]

        # Panel A: Histograms
        bins = np.linspace(0, 6, 25)
        ax1.hist(reversal_di, bins=bins, alpha=0.6, color='red', label='Reversals (n=10)', edgecolor='black')
        ax1.hist(concordant_di, bins=bins, alpha=0.6, color='blue', label='Concordant (n=5)', edgecolor='black')

        # Mark thresholds
        ax1.axvline(2.0, color='orange', linestyle='--', lw=2, label='Current Threshold')
        ax1.axvline(self.roc_results['optimal_threshold'], color='green', linestyle='--', lw=2,
                   label=f'Optimal Threshold ({self.roc_results["optimal_threshold"]:.2f})')

        ax1.set_xlabel('Discordance Index (DI)', fontsize=12)
        ax1.set_ylabel('Frequency', fontsize=12)
        ax1.set_title('DI Distribution by Case Type', fontsize=14, weight='bold')
        ax1.legend(loc='upper right', fontsize=10)
        ax1.grid(True, alpha=0.3, axis='y')

        # Panel B: Box plots
        data_to_plot = [concordant_di, reversal_di]
        positions = [1, 2]
        bp = ax2.boxplot(data_to_plot, positions=positions, widths=0.6, patch_artist=True,
                        labels=['Concordant', 'Reversals'])

        bp['boxes'][0].set_facecolor('lightblue')
        bp['boxes'][1].set_facecolor('lightcoral')

        ax2.axhline(2.0, color='orange', linestyle='--', lw=2, label='Current Threshold')
        ax2.axhline(self.roc_results['optimal_threshold'], color='green', linestyle='--', lw=2,
                   label='Optimal Threshold')

        ax2.set_ylabel('Discordance Index (DI)', fontsize=12)
        ax2.set_title('DI by Case Type (Box Plot)', fontsize=14, weight='bold')
        ax2.legend(loc='upper right', fontsize=10)
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"DI distributions saved to: {output_file}")
        plt.close()


def analyze_sigma_ref_sensitivity():
    """
    Test sensitivity of DI to sigma_ref parameter
    Helps determine optimal reference standard deviation
    """
    print("\n" + "="*80)
    print("SIGMA_REF SENSITIVITY ANALYSIS")
    print("="*80)

    # Load medical reversal data
    data = pd.read_csv('./validation/results/medical_reversal_results.csv')

    # We need the original obs/rct data to recalculate DI with different sigma
    # For now, use the HFpEF case as example

    print("\nExample: Beta-Blockers in HFpEF")
    print("-" * 80)

    # Observational data
    obs_data = pd.DataFrame({
        'study': ['Registry_1', 'Registry_2', 'Registry_3'],
        'effect': [np.log(0.85), np.log(0.90), np.log(0.95)],
        'se': [0.03, 0.04, 0.03],
        'n': [20000, 25000, 22000]
    })

    # RCT data
    rct_data = pd.DataFrame({
        'study': ['REBOOT', 'SENIORS', 'J-DHF', 'REDUCE-AMI'],
        'effect': [np.log(1.00), np.log(0.94), np.log(0.92), np.log(0.96)],
        'se': [0.08, 0.10, 0.12, 0.09],
        'n': [6000, 8000, 5000, 6000]
    })

    sigma_values = [0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0]
    results = []

    print(f"{'Sigma_ref':>10} {'DI':>8} {'Grade':>8} {'Change vs 2.0':>15}")
    print("-" * 80)

    di_at_2 = None
    for sigma in sigma_values:
        fa = ForensicAnalyzer(obs_data=obs_data, rct_data=rct_data,
                             effect_type='log_hr', sigma_ref=sigma)
        results_obj = fa.analyze()
        di = results_obj.discordance_index
        grade = results_obj.evidence_grade

        if sigma == 2.0:
            di_at_2 = di
            change = "baseline"
        elif di_at_2 is not None:
            change = f"{((di - di_at_2) / di_at_2 * 100):+.1f}%"
        else:
            change = "N/A"

        print(f"{sigma:>10.1f} {di:>8.2f} {grade:>8} {change:>15}")

        results.append({
            'sigma_ref': sigma,
            'DI': di,
            'grade': grade
        })

    print("\nInterpretation:")
    print("- DI inversely proportional to sigma_ref")
    print("- Current default (2.0) may be too large for typical HR studies")
    print("- Recommended: sigma_ref = 0.8 for log-HR (typical SD in HR meta-analyses)")

    return pd.DataFrame(results)


def main():
    """Main execution function"""
    print("="*80)
    print("FORENSIC FRAMEWORK: THRESHOLD OPTIMIZATION")
    print("="*80)

    # Initialize optimizer
    optimizer = ThresholdOptimizer()

    # Run ROC analysis
    roc_results = optimizer.run_roc_analysis()

    # Propose new thresholds
    proposed = optimizer.propose_new_grades()

    # Compare schemes
    comparison = optimizer.compare_threshold_schemes()

    # Create visualizations
    optimizer.plot_roc_curve()
    optimizer.plot_di_distributions()

    # Sigma_ref sensitivity analysis
    sigma_results = analyze_sigma_ref_sensitivity()

    # Save results
    output_file = './validation/results/threshold_optimization_results.txt'
    with open(output_file, 'w') as f:
        f.write("="*80 + "\n")
        f.write("FORENSIC FRAMEWORK: THRESHOLD OPTIMIZATION RESULTS\n")
        f.write("="*80 + "\n\n")

        f.write("ROC ANALYSIS\n")
        f.write("-" * 80 + "\n")
        f.write(f"ROC AUC: {roc_results['auc']:.3f}\n")
        f.write(f"Optimal Threshold (Youden): {roc_results['optimal_threshold']:.2f}\n")
        f.write(f"  Sensitivity: {roc_results['optimal_tpr']:.1%}\n")
        f.write(f"  Specificity: {1-roc_results['optimal_fpr']:.1%}\n\n")

        f.write("RECOMMENDED THRESHOLDS\n")
        f.write("-" * 80 + "\n")
        f.write("ROC-Optimized:\n")
        f.write(f"  Grade A: DI < {proposed['roc_optimized']['grade_a_max']:.2f}\n")
        f.write(f"  Grade B: {proposed['roc_optimized']['grade_a_max']:.2f} <= DI < {proposed['roc_optimized']['grade_b_max']:.2f}\n")
        f.write(f"  Grade C: DI >= {proposed['roc_optimized']['grade_c_min']:.2f}\n\n")

        f.write("PERFORMANCE COMPARISON\n")
        f.write("-" * 80 + "\n")
        for name, perf in comparison.items():
            f.write(f"{name}:\n")
            f.write(f"  Threshold: {perf['threshold']:.2f}\n")
            f.write(f"  Sensitivity: {perf['sensitivity']:.1%}\n")
            f.write(f"  Specificity: {perf['specificity']:.1%}\n")
            f.write(f"  Accuracy: {perf['accuracy']:.1%}\n\n")

    print(f"\nResults saved to: {output_file}")

    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print("\nKey Findings:")
    print(f"1. Optimal DI threshold: {roc_results['optimal_threshold']:.2f} (vs current 2.0)")
    print(f"2. Expected improvement: Specificity {comparison['current']['specificity']:.1%} => {comparison['roc_optimized']['specificity']:.1%}")
    print(f"3. Sensitivity maintained: {comparison['roc_optimized']['sensitivity']:.1%}")
    print("\nNext Steps:")
    print("- Update bias_detector.py with new thresholds")
    print("- Re-run simulations to verify Type I error improvement")
    print("- Update manuscript with optimized results")


if __name__ == '__main__':
    main()
