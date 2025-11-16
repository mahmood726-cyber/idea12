"""
Figure 2: Forest Plot - Treatment Effects vs BMS
Publication-quality forest plot showing network meta-analysis results
"""

import matplotlib.pyplot as plt
import numpy as np

def create_forest_plot(output_path='figure2_forest_plot', dpi=300):
    """
    Create forest plot for coronary stents NMA results

    Treatments: BMS (ref), DES, BAS, CS
    Outcome: Log odds ratio for MACE at 1 year
    """

    # Results from cardiovascular example
    treatments = ['DES', 'BAS', 'CS']
    log_or = [-0.385, -0.210, 0.125]
    se = [0.092, 0.145, 0.168]

    # Calculate OR and 95% CI
    or_values = [np.exp(log_or[i]) for i in range(len(treatments))]
    ci_lower = [np.exp(log_or[i] - 1.96*se[i]) for i in range(len(treatments))]
    ci_upper = [np.exp(log_or[i] + 1.96*se[i]) for i in range(len(treatments))]

    # P-values
    p_values = ['<0.001', '0.148', '0.457']

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Y positions for treatments
    y_pos = np.arange(len(treatments))

    # Plot reference line at OR = 1.0
    ax.axvline(x=1.0, color='black', linestyle='--', linewidth=1.5, alpha=0.7,
              label='No effect (OR=1.0)')

    # Plot confidence intervals
    for i in range(len(treatments)):
        ax.plot([ci_lower[i], ci_upper[i]], [y_pos[i], y_pos[i]],
               'k-', linewidth=2, zorder=1)

        # Color points based on significance
        color = 'darkred' if p_values[i] == '<0.001' else 'darkblue'
        marker = 'D'  # Diamond shape

        ax.plot(or_values[i], y_pos[i], marker=marker, markersize=12,
               color=color, markeredgecolor='black', markeredgewidth=1.5,
               zorder=2)

    # Set y-axis
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f'{t}' for t in treatments], fontsize=12, fontweight='bold')
    ax.set_ylim(-0.5, len(treatments) - 0.5)

    # Set x-axis (log scale)
    ax.set_xscale('log')
    ax.set_xlim(0.4, 2.0)
    ax.set_xticks([0.5, 0.6, 0.7, 0.8, 1.0, 1.2, 1.5, 2.0])
    ax.set_xticklabels(['0.5', '0.6', '0.7', '0.8', '1.0', '1.2', '1.5', '2.0'])
    ax.set_xlabel('Odds Ratio (95% CI)', fontsize=13, fontweight='bold')

    # Add shading for beneficial effect
    ax.axvspan(0.4, 1.0, alpha=0.1, color='green', label='Favors treatment')
    ax.axvspan(1.0, 2.0, alpha=0.1, color='red', label='Favors BMS')

    # Add title
    ax.set_title('Treatment Effects vs Bare Metal Stent (BMS)\n' +
                'Network Meta-Analysis of MACE at 1 Year',
                fontsize=14, fontweight='bold', pad=20)

    # Create text table on the right
    table_x = 2.2

    # Column headers
    ax.text(table_x, len(treatments)-0.5, 'OR', ha='center', va='center',
           fontsize=11, fontweight='bold')
    ax.text(table_x + 0.3, len(treatments)-0.5, '95% CI', ha='center', va='center',
           fontsize=11, fontweight='bold')
    ax.text(table_x + 0.7, len(treatments)-0.5, 'P-value', ha='center', va='center',
           fontsize=11, fontweight='bold')

    # Add values
    for i in range(len(treatments)):
        # OR
        ax.text(table_x, y_pos[i], f'{or_values[i]:.2f}', ha='center', va='center',
               fontsize=10)
        # CI
        ci_text = f'[{ci_lower[i]:.2f}, {ci_upper[i]:.2f}]'
        ax.text(table_x + 0.3, y_pos[i], ci_text, ha='center', va='center',
               fontsize=9)
        # P-value
        ax.text(table_x + 0.7, y_pos[i], p_values[i], ha='center', va='center',
               fontsize=10, fontweight='bold' if p_values[i] == '<0.001' else 'normal')

    # Add interpretation note
    interp = ('DES: 32% reduction in MACE (OR=0.68, p<0.001) - SIGNIFICANT\n' +
             'BAS: 19% reduction (OR=0.81, p=0.148) - Not significant\n' +
             'CS: 13% increase (OR=1.13, p=0.457) - Not significant')

    ax.text(0.5, -1.2, interp, ha='left', va='top', fontsize=9,
           style='italic', bbox=dict(boxstyle='round,pad=0.5',
           facecolor='lightyellow', alpha=0.8))

    # Legend
    ax.legend(loc='lower right', fontsize=9, framealpha=0.9)

    # Grid
    ax.grid(True, axis='x', alpha=0.3, linestyle=':')
    ax.set_axisbelow(True)

    # Adjust layout
    plt.tight_layout()

    # Save in multiple formats
    plt.savefig(f'{output_path}.png', dpi=dpi, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    plt.savefig(f'{output_path}.eps', format='eps', bbox_inches='tight')

    print(f"✓ Figure 2 saved: {output_path}.{{png,pdf,eps}}")
    print(f"  Resolution: {dpi} dpi")
    print(f"  Treatments: DES shows significant benefit (OR=0.68)")

    return fig

if __name__ == '__main__':
    fig = create_forest_plot()
    plt.show()
