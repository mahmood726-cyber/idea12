"""
Figure 3: Schematic Illustration of LASSO Covariate Selection Process
Publication-quality two-panel figure illustrating the LASSO selection methodology

NOTE: This figure shows a STYLIZED ILLUSTRATION of the LASSO selection process
based on the final selected covariates and coefficients from the analysis.
Actual LASSO paths show more variability and irregular CV curves.
For implementation details, see Supplementary Material Appendix D.
"""

import matplotlib.pyplot as plt
import numpy as np

def create_lasso_figure(output_path='figure3_lasso_paths', dpi=300):
    """
    Create LASSO coefficient paths and CV error plot

    Covariates: age, diabetes_pct, stemi_pct
    Selected λ* = 0.042 (all three covariates selected)
    """

    # Simulate LASSO path (realistic values)
    n_lambda = 50
    lambda_vals = np.logspace(-3, 1, n_lambda)
    log_lambda = np.log(lambda_vals)

    # Coefficient paths (simulated but realistic)
    # Age: β = 0.028 (final)
    # Diabetes: β = 0.015 (final)
    # STEMI: β = -0.008 (final)

    age_coef = 0.032 * np.exp(-lambda_vals * 10)  # Shrinks from 0.032 to ~0
    diabetes_coef = 0.018 * np.exp(-lambda_vals * 12)  # Shrinks from 0.018
    stemi_coef = -0.012 * np.exp(-lambda_vals * 15)  # Shrinks from -0.012

    # Add realistic curve shapes
    age_coef = np.where(lambda_vals < 0.1, 0.028 + (lambda_vals * 0.04), age_coef)
    diabetes_coef = np.where(lambda_vals < 0.1, 0.015 + (lambda_vals * 0.03), diabetes_coef)
    stemi_coef = np.where(lambda_vals < 0.1, -0.008 - (lambda_vals * 0.04), stemi_coef)

    # CV error curve (U-shaped)
    cv_error = 0.045 + 0.01 * (log_lambda - np.log(0.042))**2
    cv_se = 0.005 + 0.001 * np.abs(log_lambda - np.log(0.042))

    # Selected lambda
    lambda_star = 0.042
    lambda_star_idx = np.argmin(np.abs(lambda_vals - lambda_star))

    # Create figure with two panels
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Coefficient Paths
    ax1.plot(log_lambda, age_coef, 'b-', linewidth=2.5, label='Age')
    ax1.plot(log_lambda, diabetes_coef, 'r-', linewidth=2.5, label='Diabetes %')
    ax1.plot(log_lambda, stemi_coef, 'g-', linewidth=2.5, label='STEMI %')

    # Mark selected lambda
    ax1.axvline(x=np.log(lambda_star), color='black', linestyle='--',
               linewidth=2, alpha=0.7, label=f'Selected λ* = {lambda_star}')

    # Add points at selected lambda
    ax1.plot(np.log(lambda_star), 0.028, 'bo', markersize=10, markeredgecolor='black')
    ax1.plot(np.log(lambda_star), 0.015, 'ro', markersize=10, markeredgecolor='black')
    ax1.plot(np.log(lambda_star), -0.008, 'go', markersize=10, markeredgecolor='black')

    # Formatting panel 1
    ax1.set_xlabel('log(λ)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Coefficient Value', fontsize=12, fontweight='bold')
    ax1.set_title('(A) LASSO Coefficient Paths', fontsize=13, fontweight='bold', loc='left')
    ax1.axhline(y=0, color='gray', linestyle=':', alpha=0.5)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right', fontsize=10, framealpha=0.9)

    # Add annotations for final values
    ax1.annotate('β = 0.028\n(p=0.022)', xy=(np.log(lambda_star), 0.028),
                xytext=(np.log(lambda_star)+1, 0.035),
                arrowprops=dict(arrowstyle='->', color='blue', lw=1.5),
                fontsize=9, color='blue', fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7))

    # Panel 2: Cross-Validation Error
    ax2.plot(log_lambda, cv_error, 'k-', linewidth=2.5, label='CV Error')
    ax2.fill_between(log_lambda, cv_error - cv_se, cv_error + cv_se,
                     alpha=0.2, color='gray', label='± 1 SE')

    # Mark selected lambda (minimum CV error)
    ax2.axvline(x=np.log(lambda_star), color='red', linestyle='--',
               linewidth=2, alpha=0.7, label=f'Selected λ* = {lambda_star}')
    ax2.plot(np.log(lambda_star), cv_error[lambda_star_idx], 'ro',
            markersize=12, markeredgecolor='black', markeredgewidth=2,
            label='Minimum CV Error', zorder=5)

    # Formatting panel 2
    ax2.set_xlabel('log(λ)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('10-Fold CV Mean Squared Error', fontsize=12, fontweight='bold')
    ax2.set_title('(B) Cross-Validation Error', fontsize=13, fontweight='bold', loc='left')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right', fontsize=10, framealpha=0.9)

    # Add text box with selection results
    results_text = ('Selection Results:\n' +
                   '• All 3 covariates selected at λ* = 0.042\n' +
                   '• Age: β = 0.028 (p = 0.022) ✓\n' +
                   '• Diabetes: β = 0.015 (p = 0.061)\n' +
                   '• STEMI: β = -0.008 (p = 0.189)')
    ax2.text(0.05, 0.95, results_text, transform=ax2.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))

    # Overall title
    fig.suptitle('Schematic Illustration: LASSO Covariate Selection Process\n' +
                '(Stylized representation based on final selected model)',
                fontsize=14, fontweight='bold', y=0.98)

    # Add disclaimer note at bottom
    disclaimer = ('NOTE: This is a stylized illustration for pedagogical purposes. Actual LASSO paths and CV curves\n' +
                 'show more variability. Final coefficients: Age β=0.028 (p=0.022), Diabetes β=0.015, STEMI β=-0.008.')
    fig.text(0.5, 0.01, disclaimer, ha='center', fontsize=8, style='italic',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='wheat', alpha=0.7))

    # Adjust layout
    plt.tight_layout(rect=[0, 0.04, 1, 0.96])

    # Save in multiple formats
    plt.savefig(f'{output_path}.png', dpi=dpi, bbox_inches='tight')
    plt.savefig(f'{output_path}.pdf', bbox_inches='tight')
    plt.savefig(f'{output_path}.eps', format='eps', bbox_inches='tight')

    print(f"✓ Figure 3 (SCHEMATIC) saved: {output_path}.{{png,pdf,eps}}")
    print(f"  Resolution: {dpi} dpi")
    print(f"  Type: Stylized illustration (not actual LASSO output)")
    print(f"  Shows: λ*=0.042 with 3 covariates selected (final model results)")

    return fig

if __name__ == '__main__':
    fig = create_lasso_figure()
    plt.show()
