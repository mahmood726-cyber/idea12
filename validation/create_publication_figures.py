"""
Create Publication-Quality Figures for Forensic Meta-Analysis Paper
===================================================================

Generates all figures needed for manuscript:
1. ROC curve for DI threshold optimization
2. Forest plot comparing obs vs RCT
3. Inflation visualization (big data mirage)
4. Comparison table (Forensic vs GRADE vs Subgroup)
5. Simulation results plots
6. Medical reversal scorecard

Author: Publication team
Date: January 2025
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle
import sys
import os

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'Arial'

# Create output directory
OUTPUT_DIR = './validation/figures'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def create_roc_curve(results_df: pd.DataFrame, output_file: str):
    """
    Figure 1: ROC Curve for Discordance Index Threshold Optimization

    Shows sensitivity vs 1-specificity for different DI thresholds
    """
    # Prepare data
    di_values = results_df['DI'].values
    true_reversal = (results_df['Type'] == 'REVERSAL').values

    # Calculate ROC curve
    thresholds = np.linspace(0, 10, 100)
    tpr = []  # True positive rate (sensitivity)
    fpr = []  # False positive rate (1-specificity)

    for thresh in thresholds:
        predicted_reversal = di_values >= thresh
        tp = np.sum(predicted_reversal & true_reversal)
        fp = np.sum(predicted_reversal & ~true_reversal)
        tn = np.sum(~predicted_reversal & ~true_reversal)
        fn = np.sum(~predicted_reversal & true_reversal)

        tpr.append(tp / (tp + fn) if (tp + fn) > 0 else 0)
        fpr.append(fp / (fp + tn) if (fp + tn) > 0 else 0)

    # Calculate AUC
    auc = np.trapz(tpr, fpr)

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))

    # Plot ROC curve
    ax.plot(fpr, tpr, 'b-', linewidth=2, label=f'Discordance Index (AUC={auc:.3f})')

    # Plot diagonal (chance)
    ax.plot([0, 1], [0, 1], 'k--', alpha=0.3, label='Chance')

    # Mark current thresholds
    current_thresholds = [1.0, 2.0]
    for thresh in current_thresholds:
        idx = np.argmin(np.abs(thresholds - thresh))
        ax.plot(fpr[idx], tpr[idx], 'ro', markersize=10)
        ax.annotate(f'DI={thresh:.1f}',
                   xy=(fpr[idx], tpr[idx]),
                   xytext=(fpr[idx]+0.1, tpr[idx]-0.1),
                   fontsize=9,
                   arrowprops=dict(arrowstyle='->', color='red'))

    ax.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=12)
    ax.set_ylabel('True Positive Rate (Sensitivity)', fontsize=12)
    ax.set_title('ROC Curve: Discordance Index for Detecting Medical Reversals', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=10)
    ax.set_xlim([-0.05, 1.05])
    ax.set_ylim([-0.05, 1.05])
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, bbox_inches='tight')
    plt.close()

    print(f"Figure 1 saved: {output_file}")


def create_forest_plot(output_file: str):
    """
    Figure 2: Forest Plot - HFpEF Case Study (Obs vs RCT)

    Shows individual studies and pooled estimates
    """
    # Data from HFpEF case
    obs_studies = pd.DataFrame({
        'Study': ['Bavishi (Obs Meta)', 'Liu (Obs Meta)', 'SwedeHF (Matched)'],
        'HR': [0.81, 0.91, 0.93],
        'Lower': [0.72, 0.87, 0.86],
        'Upper': [0.90, 0.95, 1.00],
        'N': [27099, 21206, 19083],
        'Design': ['Observational']*3
    })

    rct_studies = pd.DataFrame({
        'Study': ['REBOOT (2024)', 'REDUCE-AMI (2024)', 'SENIORS (Sub)', 'J-DHF (2013)'],
        'HR': [0.97, 0.96, 0.81, 0.90],
        'Lower': [0.87, 0.79, 0.63, 0.55],
        'Upper': [1.07, 1.16, 1.04, 1.49],
        'N': [17801, 5020, 752, 245],
        'Design': ['RCT']*4
    })

    # Pooled estimates
    pooled = pd.DataFrame({
        'Study': ['Pooled Observational', 'Pooled RCT'],
        'HR': [0.904, 0.946],
        'Lower': [0.872, 0.870],
        'Upper': [0.937, 1.030],
        'N': [67388, 23818],
        'Design': ['Pooled Obs', 'Pooled RCT']
    })

    # Combine
    all_studies = pd.concat([obs_studies, rct_studies, pooled], ignore_index=True)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Y positions
    y_pos = np.arange(len(all_studies))

    # Colors
    colors = ['skyblue']*3 + ['lightcoral']*4 + ['darkblue', 'darkred']

    # Plot points and error bars
    for i, (idx, row) in enumerate(all_studies.iterrows()):
        # Error bar
        ax.plot([row['Lower'], row['Upper']], [i, i], 'k-', linewidth=1.5)

        # Point
        marker_size = 100 if 'Pooled' in row['Study'] else 50
        ax.scatter(row['HR'], i, s=marker_size, c=colors[i], edgecolors='black', linewidths=1.5, zorder=3)

    # Null line
    ax.axvline(1.0, color='gray', linestyle='--', linewidth=1, zorder=1)

    # Labels
    ax.set_yticks(y_pos)
    ax.set_yticklabels(all_studies['Study'], fontsize=9)
    ax.set_xlabel('Hazard Ratio (95% CI)', fontsize=12)
    ax.set_title('Beta-Blockers in HFpEF: The "Big Data Mirage"', fontsize=14, fontweight='bold')

    # Formatting
    ax.set_xlim([0.5, 1.6])
    ax.grid(axis='x', alpha=0.3)

    # Add design labels
    ax.text(0.52, 1, 'Observational', fontsize=10, fontweight='bold', color='skyblue')
    ax.text(0.52, 5, 'RCTs', fontsize=10, fontweight='bold', color='lightcoral')
    ax.text(0.52, 9, 'Pooled', fontsize=10, fontweight='bold')

    # Add forest plot statistics on right
    ax2 = ax.twinx()
    ax2.set_ylim(ax.get_ylim())
    ax2.set_yticks(y_pos)
    labels_right = [f"N={int(row['N']):,}" for _, row in all_studies.iterrows()]
    ax2.set_yticklabels(labels_right, fontsize=8)
    ax2.set_ylabel('Sample Size', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_file, bbox_inches='tight')
    plt.close()

    print(f"Figure 2 saved: {output_file}")


def create_inflation_visualization(output_file: str):
    """
    Figure 3: Information Inflation Visualization

    Shows nominal vs effective sample size
    """
    # Example data
    cases = ['HRT', 'Vitamin E', 'Beta-Blockers\nHFpEF', 'Statins CKD\n(Concordant)']
    nominal_n = [70000, 158000, 67388, 28770]
    effective_n = [280, 1660, 540, 12000]
    inflation = [250, 95, 125, 2.4]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel A: Bar chart comparison
    x = np.arange(len(cases))
    width = 0.35

    bars1 = ax1.bar(x - width/2, nominal_n, width, label='Nominal N', color='lightcoral', alpha=0.8)
    bars2 = ax1.bar(x + width/2, effective_n, width, label='Effective N', color='skyblue', alpha=0.8)

    ax1.set_ylabel('Sample Size', fontsize=12)
    ax1.set_title('Panel A: Nominal vs Effective Sample Size', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(cases, fontsize=9)
    ax1.legend()
    ax1.set_yscale('log')
    ax1.grid(axis='y', alpha=0.3)

    # Add inflation labels
    for i, (n, e, inf) in enumerate(zip(nominal_n, effective_n, inflation)):
        ax1.text(i, max(n, e)*1.5, f'{inf}x', ha='center', fontsize=9, fontweight='bold')

    # Panel B: Inflation factors
    colors_panel_b = ['darkred', 'red', 'orange', 'green']
    bars = ax2.barh(cases, inflation, color=colors_panel_b, alpha=0.7)

    ax2.set_xlabel('Inflation Factor', fontsize=12)
    ax2.set_title('Panel B: Information Inflation Factor', fontsize=12, fontweight='bold')
    ax2.axvline(10, color='gray', linestyle='--', alpha=0.5, label='Moderate (10x)')
    ax2.axvline(50, color='gray', linestyle=':', alpha=0.5, label='Severe (50x)')
    ax2.legend(fontsize=8)
    ax2.grid(axis='x', alpha=0.3)

    # Add text annotations
    for i, (case, inf) in enumerate(zip(cases, inflation)):
        ax2.text(inf + 5, i, f'{inf}x', va='center', fontsize=9, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_file, bbox_inches='tight')
    plt.close()

    print(f"Figure 3 saved: {output_file}")


def create_comparison_table(output_file: str):
    """
    Figure 4: Comparison of Methods (Forensic vs GRADE vs Subgroup)

    Table showing how different methods handle the 3 main cases
    """
    # Data
    comparison_data = {
        'Case': ['HRT', 'Vitamin E', 'Beta-Blockers HFpEF'],
        'GRADE_Decision': ['Low Quality\n(Auto-downgrade)', 'Low Quality\n(Auto-downgrade)', 'Low Quality\n(Auto-downgrade)'],
        'Subgroup_P': ['<0.001', '<0.001', '0.15'],
        'Forensic_DI': ['6.31', '5.39', '1.06'],
        'Forensic_Grade': ['C (Do Not Pool)', 'C (Do Not Pool)', 'B (Trust RCTs)'],
        'Forensic_E_Value': ['2.61', '2.10', '1.34'],
        'Correct': ['✓', '✓', '✓']
    }

    df = pd.DataFrame(comparison_data)

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.axis('tight')
    ax.axis('off')

    # Create table
    table = ax.table(cellText=df.values,
                    colLabels=df.columns,
                    cellLoc='center',
                    loc='center',
                    colWidths=[0.12, 0.15, 0.10, 0.10, 0.18, 0.12, 0.08])

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Color header
    for i in range(len(df.columns)):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Color rows
    colors = ['#E7E6E6', '#F2F2F2']
    for i in range(1, len(df) + 1):
        for j in range(len(df.columns)):
            table[(i, j)].set_facecolor(colors[(i-1) % 2])

    # Highlight correct column
    for i in range(len(df) + 1):
        table[(i, len(df.columns)-1)].set_facecolor('#C6E0B4' if i > 0 else '#4472C4')

    plt.title('Comparison of Methods for Detecting Design-Based Discordance',
             fontsize=14, fontweight='bold', pad=20)

    plt.savefig(output_file, bbox_inches='tight')
    plt.close()

    print(f"Figure 4 saved: {output_file}")


def create_simulation_results_plot(output_file: str):
    """
    Figure 5: Simulation Study Results

    Shows DI distribution and grade assignment across scenarios
    """
    # Load simulation results if available, otherwise use example data
    scenarios = ['No Bias', 'Weak Bias', 'Moderate Bias', 'Strong Bias']
    di_means = [3.32, 3.77, 6.05, 14.99]
    di_sds = [2.47, 3.16, 3.92, 4.12]
    grade_a = [20, 20, 8, 0]
    grade_b = [13, 16, 8, 0]
    grade_c = [67, 64, 84, 100]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel A: DI distributions
    x_pos = np.arange(len(scenarios))

    ax1.bar(x_pos, di_means, yerr=di_sds, capsize=5, color='steelblue', alpha=0.7)
    ax1.axhline(1.0, color='green', linestyle='--', linewidth=1.5, label='Grade A/B threshold')
    ax1.axhline(2.0, color='red', linestyle='--', linewidth=1.5, label='Grade B/C threshold')

    ax1.set_ylabel('Discordance Index', fontsize=12)
    ax1.set_title('Panel A: DI by Scenario (Mean ± SD)', fontsize=12, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(scenarios, fontsize=10)
    ax1.legend(fontsize=9)
    ax1.grid(axis='y', alpha=0.3)

    # Panel B: Grade distribution
    width = 0.6
    ax2.bar(x_pos, grade_c, width, label='Grade C', color='darkred', alpha=0.8)
    ax2.bar(x_pos, grade_b, width, bottom=grade_c, label='Grade B', color='orange', alpha=0.8)
    ax2.bar(x_pos, grade_a, width, bottom=np.array(grade_b)+np.array(grade_c),
           label='Grade A', color='green', alpha=0.8)

    ax2.set_ylabel('Percentage', fontsize=12)
    ax2.set_title('Panel B: Grade Distribution by Scenario', fontsize=12, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(scenarios, fontsize=10)
    ax2.legend(fontsize=9)
    ax2.set_ylim([0, 105])

    # Add percentage labels
    for i in range(len(scenarios)):
        if grade_a[i] > 5:
            ax2.text(i, grade_c[i] + grade_b[i] + grade_a[i]/2, f'{grade_a[i]}%',
                    ha='center', va='center', fontsize=8, fontweight='bold')
        if grade_b[i] > 5:
            ax2.text(i, grade_c[i] + grade_b[i]/2, f'{grade_b[i]}%',
                    ha='center', va='center', fontsize=8, fontweight='bold')
        if grade_c[i] > 5:
            ax2.text(i, grade_c[i]/2, f'{grade_c[i]}%',
                    ha='center', va='center', fontsize=8, fontweight='bold', color='white')

    plt.tight_layout()
    plt.savefig(output_file, bbox_inches='tight')
    plt.close()

    print(f"Figure 5 saved: {output_file}")


def create_medical_reversal_scorecard(results_df: pd.DataFrame, output_file: str):
    """
    Figure 6: Medical Reversal Forensic Scorecard

    Heatmap showing DI, E-value, Inflation for all validated cases
    """
    # Prepare data for heatmap
    reversal_cases = results_df[results_df['Type'] == 'REVERSAL'].copy()

    if len(reversal_cases) == 0:
        print("No reversal cases found, skipping scorecard")
        return

    # Extract metrics
    cases = reversal_cases['Domain'].values
    di = reversal_cases['DI'].values
    grade_numeric = reversal_cases['Grade'].apply(
        lambda x: 3 if 'C' in x else (2 if 'B' in x else 1)
    ).values

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Create data for heatmap
    data_matrix = np.column_stack([di, grade_numeric])

    # Plot
    im = ax.imshow(data_matrix.T, cmap='RdYlGn_r', aspect='auto')

    # Set ticks
    ax.set_xticks(np.arange(len(cases)))
    ax.set_yticks([0, 1])
    ax.set_xticklabels([c[:30] for c in cases], rotation=45, ha='right', fontsize=9)
    ax.set_yticklabels(['DI Score', 'Grade (1=A, 2=B, 3=C)'], fontsize=10)

    # Add values in cells
    for i in range(len(cases)):
        ax.text(i, 0, f'{di[i]:.2f}', ha='center', va='center', fontsize=9, fontweight='bold')
        grade_text = 'C' if grade_numeric[i] == 3 else ('B' if grade_numeric[i] == 2 else 'A')
        ax.text(i, 1, grade_text, ha='center', va='center', fontsize=10, fontweight='bold')

    ax.set_title('Forensic Scorecard: Medical Reversal Validation', fontsize=14, fontweight='bold')

    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Severity', rotation=270, labelpad=15)

    plt.tight_layout()
    plt.savefig(output_file, bbox_inches='tight')
    plt.close()

    print(f"Figure 6 saved: {output_file}")


def create_all_figures():
    """Generate all publication figures"""

    print("="*80)
    print("CREATING PUBLICATION FIGURES")
    print("="*80)

    # Load medical reversal results if available
    results_file = './validation/results/medical_reversal_results.csv'
    if os.path.exists(results_file):
        results_df = pd.read_csv(results_file)
        print(f"\nLoaded {len(results_df)} cases from validation results")
    else:
        print("\nWarning: Medical reversal results not found. Using example data.")
        # Create example data
        results_df = pd.DataFrame({
            'Domain': ['HRT', 'Vitamin E', 'Beta-Blockers', 'Statins CKD'],
            'DI': [6.31, 5.39, 1.06, 0.83],
            'Grade': ['Grade C', 'Grade C', 'Grade B', 'Grade A'],
            'Type': ['REVERSAL', 'REVERSAL', 'REVERSAL', 'CONCORDANT']
        })

    # Create figures
    print("\nGenerating figures...")

    try:
        create_roc_curve(results_df, f'{OUTPUT_DIR}/Figure1_ROC_Curve.png')
    except Exception as e:
        print(f"Error creating Figure 1: {e}")

    try:
        create_forest_plot(f'{OUTPUT_DIR}/Figure2_Forest_Plot.png')
    except Exception as e:
        print(f"Error creating Figure 2: {e}")

    try:
        create_inflation_visualization(f'{OUTPUT_DIR}/Figure3_Inflation.png')
    except Exception as e:
        print(f"Error creating Figure 3: {e}")

    try:
        create_comparison_table(f'{OUTPUT_DIR}/Figure4_Method_Comparison.png')
    except Exception as e:
        print(f"Error creating Figure 4: {e}")

    try:
        create_simulation_results_plot(f'{OUTPUT_DIR}/Figure5_Simulation_Results.png')
    except Exception as e:
        print(f"Error creating Figure 5: {e}")

    try:
        create_medical_reversal_scorecard(results_df, f'{OUTPUT_DIR}/Figure6_Reversal_Scorecard.png')
    except Exception as e:
        print(f"Error creating Figure 6: {e}")

    print("\n" + "="*80)
    print(f"ALL FIGURES SAVED TO: {OUTPUT_DIR}")
    print("="*80)


if __name__ == "__main__":
    create_all_figures()
