"""
Figure 1: Conceptual Framework for Network Meta-Regression with Inconsistency Modeling
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

# Set publication style
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.linewidth'] = 1.5

fig, ax = plt.subplots(1, 1, figsize=(12, 8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')

# Color scheme
color_data = '#E8F4F8'
color_core = '#B3D9E6'
color_novel = '#FFE5CC'
color_output = '#D4E6D4'

# Title
ax.text(5, 9.5, 'Network Meta-Regression Framework with Inconsistency Modeling',
        ha='center', va='top', fontsize=14, fontweight='bold')

# ============ DATA LAYER ============
data_box = FancyBboxPatch((0.5, 7.5), 2.5, 1.3,
                          boxstyle="round,pad=0.1",
                          edgecolor='black', facecolor=color_data, linewidth=2)
ax.add_patch(data_box)
ax.text(1.75, 8.5, 'Input Data', ha='center', va='top', fontsize=11, fontweight='bold')
ax.text(1.75, 8.2, '• Study-level effects (y, SE)', ha='left', va='top', fontsize=8)
ax.text(1.75, 7.95, '• Treatment network structure', ha='left', va='top', fontsize=8)
ax.text(1.75, 7.7, '• Study-level covariates (X)', ha='left', va='top', fontsize=8)

# ============ CORE NMA METHODS ============
core_y = 5.0
core_box = FancyBboxPatch((0.3, core_y), 3, 2.0,
                          boxstyle="round,pad=0.1",
                          edgecolor='black', facecolor=color_core, linewidth=2)
ax.add_patch(core_box)
ax.text(1.8, core_y + 1.85, 'Core NMA Methods', ha='center', va='top', fontsize=11, fontweight='bold')

# Sub-boxes for core methods
ax.text(0.5, core_y + 1.5, 'Bayesian NMA', ha='left', va='top', fontsize=9, fontweight='bold')
ax.text(0.5, core_y + 1.25, '  • MCMC (NUTS)', ha='left', va='top', fontsize=7)
ax.text(0.5, core_y + 1.05, '  • Weakly informative priors', ha='left', va='top', fontsize=7)
ax.text(0.5, core_y + 0.85, '  • Full posterior distributions', ha='left', va='top', fontsize=7)

ax.text(0.5, core_y + 0.5, 'Frequentist NMA', ha='left', va='top', fontsize=9, fontweight='bold')
ax.text(0.5, core_y + 0.25, '  • GLS/REML estimation', ha='left', va='top', fontsize=7)
ax.text(0.5, core_y + 0.05, '  • Likelihood-based inference', ha='left', va='top', fontsize=7)

# ============ NOVEL EXTENSIONS ============
novel_x = 3.8
novel_y = 5.0
novel_box = FancyBboxPatch((novel_x, novel_y), 2.8, 2.0,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_novel, linewidth=2)
ax.add_patch(novel_box)
ax.text(novel_x + 1.4, novel_y + 1.85, 'Novel Extensions', ha='center', va='top',
        fontsize=11, fontweight='bold')

extensions = [
    ('LASSO Selection', novel_y + 1.5),
    ('Hierarchical Centering', novel_y + 1.1),
    ('Multiple Imputation', novel_y + 0.7),
    ('Inconsistency Adjustment', novel_y + 0.3)
]

for ext, y_pos in extensions:
    ax.text(novel_x + 0.2, y_pos, f'• {ext}', ha='left', va='top', fontsize=8)

# ============ INCONSISTENCY DETECTION ============
incons_x = 7.0
incons_y = 5.0
incons_box = FancyBboxPatch((incons_x, incons_y), 2.7, 2.0,
                            boxstyle="round,pad=0.1",
                            edgecolor='black', facecolor='#FFE5E5', linewidth=2)
ax.add_patch(incons_box)
ax.text(incons_x + 1.35, incons_y + 1.85, 'Inconsistency Detection', ha='center', va='top',
        fontsize=11, fontweight='bold')

ax.text(incons_x + 0.2, incons_y + 1.5, 'Node-Splitting', ha='left', va='top',
        fontsize=9, fontweight='bold')
ax.text(incons_x + 0.2, incons_y + 1.25, '  • Direct vs indirect', ha='left', va='top', fontsize=7)
ax.text(incons_x + 0.2, incons_y + 1.05, '  • Comparison-specific', ha='left', va='top', fontsize=7)

ax.text(incons_x + 0.2, incons_y + 0.7, 'Design-by-Treatment', ha='left', va='top',
        fontsize=9, fontweight='bold')
ax.text(incons_x + 0.2, incons_y + 0.45, '  • Global test', ha='left', va='top', fontsize=7)
ax.text(incons_x + 0.2, incons_y + 0.25, '  • Design effects', ha='left', va='top', fontsize=7)

# ============ META-REGRESSION ============
metareg_y = 3.0
metareg_box = FancyBboxPatch((2.0, metareg_y), 6, 1.3,
                             boxstyle="round,pad=0.1",
                             edgecolor='black', facecolor='#E6E6FA', linewidth=2)
ax.add_patch(metareg_box)
ax.text(5.0, metareg_y + 1.15, 'Network Meta-Regression', ha='center', va='top',
        fontsize=11, fontweight='bold')
ax.text(5.0, metareg_y + 0.8,
        'δᵢⱼₖ ~ N(dⱼₖ + Xᵢᵀ(β + γⱼ - γₖ), τ²)',
        ha='center', va='top', fontsize=9, style='italic')
ax.text(5.0, metareg_y + 0.4,
        'Main effects (β) + Treatment interactions (γⱼ) + Hierarchical centering',
        ha='center', va='top', fontsize=7)

# ============ OUTPUTS ============
output_y = 0.8
outputs = [
    ('Relative Treatment\nEffects (dⱼ)', 1.0),
    ('Treatment Rankings\n(P-scores/SUCRA)', 2.8),
    ('Covariate Effects\n(β, γⱼ)', 4.6),
    ('Population-Specific\nPredictions', 6.4),
    ('Inconsistency\nAssessment', 8.2)
]

for label, x_pos in outputs:
    output_box = FancyBboxPatch((x_pos - 0.6, output_y), 1.2, 0.6,
                                boxstyle="round,pad=0.05",
                                edgecolor='black', facecolor=color_output, linewidth=1.5)
    ax.add_patch(output_box)
    ax.text(x_pos, output_y + 0.3, label, ha='center', va='center', fontsize=7)

# ============ ARROWS ============
# Data to core methods
arrow1 = FancyArrowPatch((1.75, 7.5), (1.75, 7.0),
                        arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow1)

# Core to meta-regression
arrow2 = FancyArrowPatch((1.8, 5.0), (3.5, 4.3),
                        arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow2)

# Novel extensions to meta-regression
arrow3 = FancyArrowPatch((5.2, 5.0), (5.2, 4.3),
                        arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow3)

# Inconsistency to meta-regression
arrow4 = FancyArrowPatch((8.3, 5.0), (6.5, 4.3),
                        arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow4)

# Meta-regression to outputs
arrow5 = FancyArrowPatch((5.0, 3.0), (5.0, 1.4),
                        arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow5)

# Add legend for method types
legend_elements = [
    mpatches.Patch(facecolor=color_data, edgecolor='black', label='Data Input'),
    mpatches.Patch(facecolor=color_core, edgecolor='black', label='Established Methods'),
    mpatches.Patch(facecolor=color_novel, edgecolor='black', label='Novel Contributions'),
    mpatches.Patch(facecolor=color_output, edgecolor='black', label='Outputs')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=8, frameon=True)

plt.tight_layout()
plt.savefig('/home/user/idea12/figures/Figure1_Conceptual_Framework.png', dpi=300, bbox_inches='tight')
plt.savefig('/home/user/idea12/figures/Figure1_Conceptual_Framework.pdf', bbox_inches='tight')
print("Figure 1 saved successfully!")
plt.close()
