"""
Figure 2: Analytical Workflow for Network Meta-Regression
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import numpy as np

# Set publication style
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['font.size'] = 9
plt.rcParams['axes.linewidth'] = 1.5

fig, ax = plt.subplots(1, 1, figsize=(10, 13))
ax.set_xlim(0, 10)
ax.set_ylim(0, 14)
ax.axis('off')

# Title
ax.text(5, 13.5, 'Network Meta-Regression Analytical Workflow',
        ha='center', va='top', fontsize=14, fontweight='bold')

# Color scheme for different stages
color_prep = '#E8F4F8'
color_assess = '#FFE5CC'
color_model = '#D4E6D4'
color_check = '#FFE5E5'
color_output = '#E6E6FA'

# Track vertical position
y_pos = 12.5

# ============ STEP 1: DATA PREPARATION ============
step1_box = FancyBboxPatch((1, y_pos - 1.2), 8, 1.2,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_prep, linewidth=2)
ax.add_patch(step1_box)
step_circle = Circle((0.5, y_pos - 0.6), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.6, '1', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.3, 'Data Preparation & Exploration', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.6, '• Extract treatment effects and standard errors from studies',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.8, '• Compile study-level covariates (age, severity, year, etc.)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.0, '• Construct treatment network graph • Identify multi-arm trials',
        ha='left', va='top', fontsize=8)

y_pos -= 1.5

# Arrow
arrow = FancyArrowPatch((5, y_pos + 0.3), (5, y_pos),
                       arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow)
y_pos -= 0.3

# ============ STEP 2: MISSING DATA ============
step2_box = FancyBboxPatch((1, y_pos - 1.0), 8, 1.0,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_prep, linewidth=2)
ax.add_patch(step2_box)
step_circle = Circle((0.5, y_pos - 0.5), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.5, '2', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.2, 'Handle Missing Covariates (if applicable)', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.5, '• Assess missingness patterns • Multiple imputation (MICE, M=20)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.75, '• Pool results using Rubin\'s rules',
        ha='left', va='top', fontsize=8)

y_pos -= 1.3

# Arrow
arrow = FancyArrowPatch((5, y_pos + 0.3), (5, y_pos),
                       arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow)
y_pos -= 0.3

# ============ STEP 3: BASELINE NMA ============
step3_box = FancyBboxPatch((1, y_pos - 1.2), 8, 1.2,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_assess, linewidth=2)
ax.add_patch(step3_box)
step_circle = Circle((0.5, y_pos - 0.6), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.6, '3', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.3, 'Baseline Network Meta-Analysis', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.6, '• Fit random-effects NMA (no covariates)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.8, '• Estimate relative treatment effects (dⱼ) and heterogeneity (τ²)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.0, '• Generate treatment rankings (P-scores)',
        ha='left', va='top', fontsize=8)

y_pos -= 1.5

# Arrow
arrow = FancyArrowPatch((5, y_pos + 0.3), (5, y_pos),
                       arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow)
y_pos -= 0.3

# ============ STEP 4: INCONSISTENCY CHECK ============
step4_box = FancyBboxPatch((1, y_pos - 1.4), 8, 1.4,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_check, linewidth=2)
ax.add_patch(step4_box)
step_circle = Circle((0.5, y_pos - 0.7), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.7, '4', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.3, 'Inconsistency Assessment', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.6, '• Node-splitting: Test direct vs. indirect evidence for each comparison',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.8, '• Design-by-treatment interaction: Global inconsistency test',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.0, '• If inconsistency detected: consider down-weighting or bias adjustment',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.25, '• Examine potential sources (clinical/methodological heterogeneity)',
        ha='left', va='top', fontsize=8)

y_pos -= 1.7

# Arrow
arrow = FancyArrowPatch((5, y_pos + 0.3), (5, y_pos),
                       arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow)
y_pos -= 0.3

# ============ STEP 5: COVARIATE SELECTION ============
step5_box = FancyBboxPatch((1, y_pos - 1.2), 8, 1.2,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_model, linewidth=2)
ax.add_patch(step5_box)
step_circle = Circle((0.5, y_pos - 0.6), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.6, '5', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.3, 'Covariate Selection (if multiple candidates)', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.6, '• LASSO regularization with cross-validation',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.8, '• Stability selection via bootstrap (quantify uncertainty)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.0, '• Alternative: theory-driven selection based on clinical knowledge',
        ha='left', va='top', fontsize=8)

y_pos -= 1.5

# Arrow
arrow = FancyArrowPatch((5, y_pos + 0.3), (5, y_pos),
                       arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow)
y_pos -= 0.3

# ============ STEP 6: META-REGRESSION ============
step6_box = FancyBboxPatch((1, y_pos - 1.4), 8, 1.4,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_model, linewidth=2)
ax.add_patch(step6_box)
step_circle = Circle((0.5, y_pos - 0.7), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.7, '6', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.3, 'Network Meta-Regression', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.6, '• Fit model with selected covariates (centered at network average)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.8, '• Include treatment-by-covariate interactions if justified',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.0, '• Bayesian (MCMC) or frequentist (GLS/REML) estimation',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.25, '• Assess model fit and residual heterogeneity',
        ha='left', va='top', fontsize=8)

y_pos -= 1.7

# Arrow
arrow = FancyArrowPatch((5, y_pos + 0.3), (5, y_pos),
                       arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow)
y_pos -= 0.3

# ============ STEP 7: MODEL DIAGNOSTICS ============
step7_box = FancyBboxPatch((1, y_pos - 1.2), 8, 1.2,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_check, linewidth=2)
ax.add_patch(step7_box)
step_circle = Circle((0.5, y_pos - 0.6), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.6, '7', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.3, 'Model Diagnostics & Validation', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.6, '• Convergence: R̂, ESS, trace plots (Bayesian) or likelihood (frequentist)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.8, '• Goodness-of-fit: Residual deviance, leverage plots',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.0, '• Sensitivity: Prior robustness, outlier influence',
        ha='left', va='top', fontsize=8)

y_pos -= 1.5

# Arrow
arrow = FancyArrowPatch((5, y_pos + 0.3), (5, y_pos),
                       arrowstyle='->', mutation_scale=20, linewidth=2, color='black')
ax.add_patch(arrow)
y_pos -= 0.3

# ============ STEP 8: INFERENCE & PREDICTION ============
step8_box = FancyBboxPatch((1, y_pos - 1.4), 8, 1.4,
                           boxstyle="round,pad=0.1",
                           edgecolor='black', facecolor=color_output, linewidth=2)
ax.add_patch(step8_box)
step_circle = Circle((0.5, y_pos - 0.7), 0.25, color='black')
ax.add_patch(step_circle)
ax.text(0.5, y_pos - 0.7, '8', ha='center', va='center', fontsize=10,
        color='white', fontweight='bold')
ax.text(1.5, y_pos - 0.3, 'Inference & Population-Specific Predictions', ha='left', va='top',
        fontsize=11, fontweight='bold')
ax.text(1.5, y_pos - 0.6, '• Estimate covariate effects (β) and treatment interactions (γⱼ)',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 0.8, '• Generate predictions for target populations with specific characteristics',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.0, '• Calculate treatment rankings conditional on covariate values',
        ha='left', va='top', fontsize=8)
ax.text(1.5, y_pos - 1.25, '• Quantify uncertainty (credible/confidence intervals)',
        ha='left', va='top', fontsize=8)

y_pos -= 1.7

# ============ DECISION POINTS ============
# Add decision diamond for inconsistency
diamond_x = 9.5
diamond_y = 7.8
diamond_points = np.array([[diamond_x, diamond_y + 0.3],
                          [diamond_x + 0.3, diamond_y],
                          [diamond_x, diamond_y - 0.3],
                          [diamond_x - 0.3, diamond_y]])
diamond = mpatches.Polygon(diamond_points, closed=True,
                          edgecolor='red', facecolor='#FFE5E5', linewidth=2)
ax.add_patch(diamond)
ax.text(diamond_x, diamond_y, '?', ha='center', va='center',
       fontsize=12, fontweight='bold', color='red')
ax.text(diamond_x + 0.8, diamond_y, 'Inconsistency\ndetected?', ha='left', va='center',
       fontsize=7)

# Add legend
legend_elements = [
    mpatches.Patch(facecolor=color_prep, edgecolor='black', label='Data Preparation'),
    mpatches.Patch(facecolor=color_assess, edgecolor='black', label='Initial Assessment'),
    mpatches.Patch(facecolor=color_check, edgecolor='black', label='Diagnostic Checks'),
    mpatches.Patch(facecolor=color_model, edgecolor='black', label='Modeling'),
    mpatches.Patch(facecolor=color_output, edgecolor='black', label='Final Inference')
]
ax.legend(handles=legend_elements, loc='lower right', fontsize=7, frameon=True, ncol=2)

plt.tight_layout()
plt.savefig('/home/user/idea12/figures/Figure2_Analytical_Workflow.png', dpi=300, bbox_inches='tight')
plt.savefig('/home/user/idea12/figures/Figure2_Analytical_Workflow.pdf', bbox_inches='tight')
print("Figure 2 saved successfully!")
plt.close()
