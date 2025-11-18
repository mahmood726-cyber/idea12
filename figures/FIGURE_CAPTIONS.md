# Figure Captions for Synthesis Document

## Figure 1: Conceptual Framework for Network Meta-Regression with Inconsistency Modeling

**Caption:**
Conceptual framework showing the key components of the network meta-regression approach. The framework integrates input data (study-level effects, treatment network structure, and covariates) with core NMA methods (both Bayesian and frequentist implementations), novel methodological extensions (LASSO selection, hierarchical centering, multiple imputation, and inconsistency adjustment), and inconsistency detection approaches (node-splitting and design-by-treatment interaction). These components feed into the network meta-regression model, which produces relative treatment effects, treatment rankings, covariate effects, population-specific predictions, and inconsistency assessments. Color coding indicates different methodological categories: data input (blue), established methods (light blue), novel contributions (orange), diagnostic checks (red), and outputs (purple).

**File formats:**
- `Figure1_Conceptual_Framework.png` (high-resolution, 300 DPI)
- `Figure1_Conceptual_Framework.pdf` (vector format for publication)

---

## Figure 2: Analytical Workflow for Network Meta-Regression

**Caption:**
Step-by-step analytical workflow for conducting network meta-regression analysis. The workflow begins with data preparation and exploration (Step 1), proceeds through handling missing covariates via multiple imputation (Step 2), baseline network meta-analysis without covariates (Step 3), and comprehensive inconsistency assessment using node-splitting and design-by-treatment interaction methods (Step 4). If inconsistency is detected, analysts can apply down-weighting or bias adjustment. The workflow continues with automated covariate selection using LASSO regularization (Step 5), fitting the network meta-regression model with hierarchical centering (Step 6), model diagnostics including convergence assessment and goodness-of-fit (Step 7), and culminates in inference and population-specific predictions (Step 8). Color coding distinguishes different stages: data preparation (blue), initial assessment (orange), diagnostic checks (red), modeling (green), and final inference (purple).

**File formats:**
- `Figure2_Analytical_Workflow.png` (high-resolution, 300 DPI)
- `Figure2_Analytical_Workflow.pdf` (vector format for publication)

---

## Usage Notes

Both figures are provided in:
1. **PNG format** (300 DPI) - suitable for presentations, web display, and initial manuscript submission
2. **PDF format** (vector) - recommended for final publication submission to ensure highest quality

The figures are designed to be publication-ready for journals such as *Research Synthesis Methods*, *Statistics in Medicine*, or similar methodological journals.

## Regenerating Figures

To regenerate the figures, run:
```bash
python figures/generate_figure1.py
python figures/generate_figure2.py
```

Requirements:
- matplotlib >= 3.4.0
- numpy >= 1.21.0
