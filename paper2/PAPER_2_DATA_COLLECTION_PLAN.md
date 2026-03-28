# Paper #2: Data Collection Plan
## Machine Learning to Predict Bias in 501 Cochrane Reviews

**Start Date**: November 20, 2025
**Target**: Collect 100-501 Cochrane reviews with obs+RCT comparisons
**Timeline**: 2-3 months (pilot) / 6-12 months (full dataset)

---

## OBJECTIVE

Build machine learning model to predict medical reversals by:
1. **Training**: Use 25 validated cases from Paper #1
2. **Application**: Apply to 501 Cochrane reviews
3. **Output**: Risk score (0-100%) for each review
4. **Impact**: Identify which current guidelines may be wrong

---

## DATA REQUIREMENTS

### For Each Cochrane Review:

**Minimal Requirements**:
- Includes BOTH observational studies AND RCTs
- Compares same intervention for same outcome
- Sufficient data to calculate effect estimates

**Features to Extract** (20-25 total):

**Core Forensic Metrics** (calculated):
1. Discordance Index (DI)
2. E-value (point estimate)
3. Inflation Factor
4. Effect size obs (HR/OR/RR)
5. Effect size RCT
6. 95% CI width (obs)
7. 95% CI width (RCT)
8. Sample size obs
9. Sample size RCT
10. I² heterogeneity (obs)
11. I² heterogeneity (RCT)

**Study Characteristics** (extracted):
12. Domain (cardiology, oncology, etc.)
13. Outcome type (mortality, morbidity, QoL)
14. Intervention type (drug, surgery, lifestyle)
15. Publication year (most recent)
16. Geographic region (predominant)
17. Funding source (industry vs public)
18. Number of obs studies
19. Number of RCTs
20. Follow-up duration

**Derived Features** (calculated):
21. DI/E-value ratio
22. Effective sample size ratio
23. Precision mismatch (CI width ratio)
24. Effect direction agreement (binary)
25. Magnitude ratio (obs effect / RCT effect)

---

## DATA SOURCES

### Primary Source: Cochrane Database of Systematic Reviews

**Access Options**:

**Option 1: Institutional Subscription** (BEST)
- Most universities have Cochrane Library access
- Full text access to all reviews
- Exportable data

**Option 2: Cochrane Central Register of Controlled Trials (CENTRAL)**
- Free access: https://www.cochranelibrary.com/central
- Search for reviews comparing study designs

**Option 3: PubMed/MEDLINE**
- Free access
- Search: "Cochrane[ta] AND (observational OR cohort) AND randomized"
- May miss some reviews

**Option 4: Web Scraping Cochrane Abstracts**
- Last resort if no institutional access
- Many abstracts publicly available
- May be incomplete data

---

## PILOT: 100 REVIEWS (UNFUNDED)

### Selection Strategy:

**Stratified Random Sampling by Domain**:
1. Cardiology: 20 reviews
2. Oncology: 15 reviews
3. Endocrine/Diabetes: 10 reviews
4. Neurology: 10 reviews
5. Respiratory: 10 reviews
6. Gastroenterology: 5 reviews
7. Nephrology: 5 reviews
8. Infectious Disease: 5 reviews
9. Rheumatology: 5 reviews
10. Other domains: 15 reviews

**Inclusion Criteria**:
- Published in last 10 years (2014-2024)
- Includes ≥1 observational study
- Includes ≥1 RCT
- Quantitative synthesis (meta-analysis, not just narrative)
- Sufficient data to extract effect estimates

**Exclusion Criteria**:
- No quantitative synthesis
- Only network meta-analysis (indirect comparisons)
- Insufficient data reported
- Non-English

---

## DATA EXTRACTION WORKFLOW

### Step 1: Identify Eligible Reviews (Week 1-2)

**Search Strategy**:
```
Cochrane Database Search:
"(observational OR cohort OR case-control OR registry) AND (randomized OR RCT OR trial)"
Filters:
- Publication date: 2014-2024
- Review type: Intervention reviews
- Has meta-analysis
```

**Expected Yield**: 500-1000 reviews → screen to 100-501 eligible

---

### Step 2: Screen Abstracts (Week 2-3)

**Screening Form**:
```
Review ID: ________________
Title: ____________________
Domain: ___________________

Includes observational studies? [Y/N]
Includes RCTs? [Y/N]
Compares same intervention/outcome? [Y/N]
Quantitative synthesis available? [Y/N]

Eligible: [Y/N]
```

**Tool**: Excel or Google Sheets
**Time**: ~2-3 minutes per abstract
**Total**: 100 reviews × 3 min = 5 hours

---

### Step 3: Extract Data from Full Text (Week 3-8)

**For Each Eligible Review**:

**A. Basic Information**:
- Review ID
- Authors
- Publication year
- Domain
- Intervention
- Outcome
- Cochrane registration number

**B. Observational Evidence**:
- Number of studies
- Total sample size
- Pooled effect estimate (HR/OR/RR)
- 95% CI
- I² heterogeneity
- Study designs (cohort, case-control, etc.)

**C. RCT Evidence**:
- Number of studies
- Total sample size
- Pooled effect estimate
- 95% CI
- I² heterogeneity

**D. Study Characteristics**:
- Geographic region
- Funding sources
- Publication years
- Follow-up duration
- Outcome type

**Tool**: Structured Excel template
**Time**: ~30-45 minutes per review
**Total**: 100 reviews × 40 min = 67 hours (~2 weeks full-time)

---

### Step 4: Calculate Forensic Metrics (Week 9)

**Use bias_detector.py from Paper #1**:

```python
import pandas as pd
import numpy as np
from netmetareg.forensic.bias_detector import ForensicAnalyzer

# For each review
obs_data = pd.DataFrame({
    'study': [f'Obs_Meta_Review_{review_id}'],
    'effect': [np.log(obs_effect)],
    'se': [(np.log(obs_ci_upper) - np.log(obs_ci_lower)) / (2 * 1.96)],
    'n': [obs_sample_size]
})

rct_data = pd.DataFrame({
    'study': [f'RCT_Meta_Review_{review_id}'],
    'effect': [np.log(rct_effect)],
    'se': [(np.log(rct_ci_upper) - np.log(rct_ci_lower)) / (2 * 1.96)],
    'n': [rct_sample_size]
})

analyzer = ForensicAnalyzer(obs_data, rct_data, effect_type='log_hr')
results = analyzer.analyze()

# Store results
forensic_metrics[review_id] = {
    'DI': results.discordance_index,
    'E_value': results.e_value_point,
    'Inflation': results.inflation_factor,
    'Grade': results.evidence_grade
}
```

**Output**: CSV file with all features for 100 reviews

---

## ML MODEL DEVELOPMENT (Week 10-12)

### Training Dataset:
- **N=25** from Paper #1 (10 reversals, 15 concordant)
- All 20-25 features calculated
- Ground truth labels: Reversal (1) vs Concordant (0)

### Algorithms to Test:

**1. Logistic Regression** (baseline)
```python
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut

model = LogisticRegression(penalty='l2', C=1.0)
loo = LeaveOneOut()
scores = cross_val_score(model, X, y, cv=loo, scoring='roc_auc')
print(f"LOO-CV AUC: {scores.mean():.3f}")
```

**2. Random Forest** (primary)
```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=5,
    min_samples_split=3,
    random_state=42
)
```

**3. XGBoost** (gradient boosting)
```python
import xgboost as xgb

model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=3,
    learning_rate=0.1,
    random_state=42
)
```

### Cross-Validation:
- Leave-one-out (LOOCV) for N=25
- 5-fold stratified CV
- Report mean ± SD ROC AUC

### Feature Importance:
- Permutation importance
- SHAP values
- Feature correlation matrix

---

## APPLICATION TO 100 REVIEWS (Week 13)

### For Each Review:
1. Calculate all 25 features
2. Apply trained model
3. Generate risk score (0-100%)
4. Flag high-risk (>70% probability)

### Expected Output:

**Predicted High-Risk Reviews**: ~10-15 out of 100 (10-15%)

**Examples**:
- "Statins for primary prevention in low-risk adults: 85% reversal probability"
- "Prostate cancer screening >70 years: 78% reversal probability"
- "Antidepressants for mild depression: 72% reversal probability"

---

## DELIVERABLES

### Month 3 (Pilot Complete):
1. **Dataset**: 100 Cochrane reviews × 25 features
2. **ML Model**: Trained Random Forest with performance metrics
3. **Predictions**: Risk scores for 100 reviews
4. **Analysis**: Top 20 high-risk reviews identified
5. **Report**: Pilot findings document

### Month 12 (Full Dataset):
1. **Dataset**: 501 Cochrane reviews × 25 features
2. **ML Model**: Final optimized model
3. **Predictions**: Risk scores for all 501 reviews
4. **Manuscript**: Paper #2 ready for Lancet/JAMA
5. **Impact**: Identify 50+ guidelines at risk

---

## RESOURCE REQUIREMENTS

### Personnel:
- **Lead analyst** (you): 25% FTE, 3 months (pilot)
- **Research assistant**: 100% FTE, 2 months (data extraction)
  - Alternative: Student intern (lower cost)
  - Alternative: Outsource to Upwork/Fiverr (~$2000)

### Software:
- Python (pandas, scikit-learn, XGBoost) - FREE
- Excel or Google Sheets - FREE
- Cochrane Library access - Check university subscription

### Budget (Pilot):
- **Personnel**: $0 (you) + $8000 (RA, 2 months) OR $2000 (outsourced)
- **Software**: $0
- **Access**: $0 (if institutional subscription)
- **Total**: $2,000-8,000 for pilot

---

## TIMELINE SUMMARY

### Pilot (100 Reviews, 3 Months):
- **Month 1**: Identify and screen reviews (5-10 hours)
- **Month 2**: Extract data (67 hours, outsourceable)
- **Month 3**: Calculate metrics, train ML, analyze (40 hours)

### Full Dataset (501 Reviews, 6-12 Months):
- **Months 1-2**: Screen all reviews
- **Months 3-8**: Extract data (300+ hours, need RA)
- **Months 9-10**: ML development and validation
- **Months 11-12**: Manuscript preparation

---

## FUNDING STRATEGY

### Unfunded Pilot (100 Reviews):
- Do yourself: 112 hours total (~3 weeks full-time)
- Or outsource data extraction: $2000
- Use pilot results for grant application

### Grant Application (After Pilot):
**NIH R21** ($275,000):
- Use pilot as preliminary data
- Cite Paper #1 (accepted/published)
- Request funding for 501 reviews + 2 years

**PCORI** ($500K-1M):
- Patient-centered angle (prevents harm from biased evidence)
- Larger budget for comprehensive analysis
- Higher likelihood with pilot data

---

## SUCCESS CRITERIA

### Pilot Success:
- ✓ 100 reviews extracted with ≥90% complete data
- ✓ ML model achieves ROC AUC >0.85
- ✓ Identify 10-15 high-risk reviews
- ✓ Results compelling enough for grant

### Full Study Success:
- ✓ 501 reviews analyzed
- ✓ ML model ROC AUC >0.90
- ✓ 50+ high-risk reviews identified
- ✓ Manuscript accepted in Lancet/JAMA
- ✓ Media coverage and clinical impact

---

## NEXT IMMEDIATE STEPS

### This Week:
1. ✅ Submit Paper #1 to Research Synthesis Methods
2. Check Cochrane Library institutional access
3. Develop search strategy
4. Create Excel extraction template

### Next Week:
1. Run Cochrane search
2. Screen first 20 abstracts
3. Extract first 5 reviews (test workflow)
4. Refine extraction process

### Month 1:
1. Complete screening (identify 100 eligible)
2. Begin data extraction
3. Parallel: Write grant application outline

---

## DECISION POINT

**Option A: Start Pilot Now (Unfunded)**
- Pros: Immediate progress, pilot for grant, low cost
- Cons: Time-intensive (112 hours), slow without RA
- Timeline: 3 months to pilot results

**Option B: Wait for Grant Funding**
- Pros: Professional RA, faster execution, larger dataset
- Cons: 6-9 month delay for funding, no pilot data
- Timeline: 12-18 months to full results

**RECOMMENDATION**: **Option A + B Hybrid**
1. Start pilot now with first 20-30 reviews (low-hanging fruit)
2. Use pilot data to write grant (1-2 months)
3. Submit grant while continuing pilot
4. If funded: Scale up to 501 reviews
5. If not funded: Publish pilot (100 reviews) in BMJ

---

**Status**: Plan complete. Ready to begin Cochrane review identification.

**Next Action**: Check Cochrane Library access and run initial search.

---

*Plan Created: November 20, 2025*
*Target: 100 reviews (pilot) in 3 months*
*Full dataset (501 reviews) in 12 months*
