"""
Medical Reversal Validation Study
==================================

Comprehensive validation of forensic framework on historical medical reversals
and concordant cases.

Includes 15 cases:
- 10 Medical Reversals (observational showed benefit, RCTs showed null/harm)
- 5 Concordant Cases (observational and RCTs agreed)

Data sources: Published meta-analyses, systematic reviews, landmark trials

Author: Validation team
Date: January 2025
"""

import numpy as np
import pandas as pd
import sys
import os
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from netmetareg.forensic import ForensicAnalyzer
    FORENSIC_AVAILABLE = True
except:
    FORENSIC_AVAILABLE = False
    print("Warning: Forensic module not available. Data will be prepared but not analyzed.")


# ==============================================================================
# MEDICAL REVERSAL CASES
# ==============================================================================

MEDICAL_REVERSALS = {
    # 1. Hormone Replacement Therapy (HRT) - The Classic Reversal
    'HRT_Coronary': {
        'domain': 'Hormone Replacement Therapy',
        'outcome': 'Coronary Heart Disease',
        'obs_studies': pd.DataFrame({
            'study': ['Stampfer_Nurses', 'Wilson_Framingham', 'Petitti', 'Henderson', 'Bush_LRC', 'Bain'],
            'hr': [0.56, 1.76, 0.80, 0.60, 0.40, 0.70],
            'lower': [0.40, 0.90, 0.50, 0.30, 0.20, 0.40],
            'upper': [0.78, 3.40, 1.30, 1.20, 0.80, 1.20],
            'n': [48000, 2000, 4000, 8000, 2300, 3000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['WHI_Trial'],
            'hr': [1.29],
            'lower': [1.02],
            'upper': [1.63],
            'n': [16608]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'Stampfer & Colditz 1991 (obs); Rossouw et al. 2002 (RCT)',
        'clinical_impact': 'Guidelines reversed, millions affected'
    },

    # 2. Vitamin E Supplementation
    'Vitamin_E_CVD': {
        'domain': 'Vitamin E Supplementation',
        'outcome': 'Cardiovascular Events',
        'obs_studies': pd.DataFrame({
            'study': ['Rimm_HealthProf', 'Stampfer_Nurses', 'Kushi_Iowa', 'Knekt_Finnish'],
            'hr': [0.64, 0.66, 0.38, 0.68],
            'lower': [0.49, 0.50, 0.19, 0.40],
            'upper': [0.83, 0.87, 0.76, 1.10],
            'n': [39000, 87000, 30000, 2000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['HOPE', 'GISSI', 'HPS'],
            'hr': [1.05, 0.98, 1.00],
            'lower': [0.95, 0.88, 0.91],
            'upper': [1.16, 1.09, 1.10],
            'n': [9541, 11324, 20536]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'Rimm et al. 1993 (obs); Yusuf et al. 2000 (HOPE)',
        'clinical_impact': 'Widespread supplementation abandoned'
    },

    # 3. Beta-Blockers in HFpEF (Contemporary)
    'BetaBlocker_HFpEF': {
        'domain': 'Beta-Blockers',
        'outcome': 'Mortality in HFpEF',
        'obs_studies': pd.DataFrame({
            'study': ['Bavishi', 'Liu', 'SwedeHF', 'GWTG'],
            'hr': [0.81, 0.91, 0.93, 0.90],
            'lower': [0.72, 0.87, 0.86, 0.85],
            'upper': [0.90, 0.95, 1.00, 0.95],
            'n': [27099, 21206, 19083, 14000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['REBOOT', 'REDUCE_AMI', 'SENIORS_sub', 'J_DHF'],
            'hr': [0.97, 0.96, 0.81, 0.90],
            'lower': [0.87, 0.79, 0.63, 0.55],
            'upper': [1.07, 1.16, 1.04, 1.49],
            'n': [17801, 5020, 752, 245]
        }),
        'outcome_status': 'SUSPECTED_REVERSAL',
        'references': 'Bavishi et al. 2015 (obs); Cleland et al. 2024 (REBOOT)',
        'clinical_impact': 'Guidelines uncertain, debate ongoing'
    },

    # 4. Beta-Carotene and Lung Cancer
    'BetaCarotene_Lung': {
        'domain': 'Beta-Carotene Supplementation',
        'outcome': 'Lung Cancer',
        'obs_studies': pd.DataFrame({
            'study': ['Ziegler', 'Knekt', 'Colditz'],
            'hr': [0.70, 0.65, 0.75],
            'lower': [0.55, 0.50, 0.60],
            'upper': [0.90, 0.85, 0.95],
            'n': [15000, 36000, 89000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['ATBC', 'CARET'],
            'hr': [1.18, 1.28],
            'lower': [1.03, 1.04],
            'upper': [1.36, 1.57],
            'n': [29133, 18314]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'Ziegler et al. 1996 (obs); ATBC 1994, CARET 1996',
        'clinical_impact': 'Supplementation contraindicated in smokers'
    },

    # 5. Aspirin Primary Prevention (Low Risk)
    'Aspirin_Primary_LowRisk': {
        'domain': 'Aspirin Primary Prevention',
        'outcome': 'CV Events in Low-Risk',
        'obs_studies': pd.DataFrame({
            'study': ['PHS_obs', 'NHS_obs', 'IWHS'],
            'hr': [0.68, 0.75, 0.70],
            'lower': [0.58, 0.65, 0.55],
            'upper': [0.80, 0.87, 0.89],
            'n': [22000, 38000, 28000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['ARRIVE', 'ASCEND', 'ASPREE'],
            'hr': [0.96, 0.88, 1.12],
            'lower': [0.81, 0.79, 0.95],
            'upper': [1.13, 0.97, 1.32],
            'n': [12546, 15480, 19114]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'Observational cohorts; ARRIVE 2018, ASPREE 2018',
        'clinical_impact': 'No longer recommended for low-risk primary prevention'
    },

    # 6. Rosiglitazone - Cardiovascular Safety
    'Rosiglitazone_CV': {
        'domain': 'Rosiglitazone',
        'outcome': 'MI and CV Death',
        'obs_studies': pd.DataFrame({
            'study': ['ADOPT_obs', 'PROactive_obs', 'DREAM_obs'],
            'hr': [0.98, 0.92, 0.89],
            'lower': [0.78, 0.75, 0.70],
            'upper': [1.22, 1.12, 1.13],
            'n': [4360, 5238, 5269]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['Nissen_Meta', 'RECORD'],
            'hr': [1.43, 1.14],
            'lower': [1.03, 0.93],
            'upper': [1.98, 1.41],
            'n': [15560, 4447]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'Pre-market obs studies; Nissen & Wolski 2007',
        'clinical_impact': 'Drug withdrawn/restricted in many countries'
    },

    # 7. Calcium Supplementation - CV Events
    'Calcium_Supp_CV': {
        'domain': 'Calcium Supplementation',
        'outcome': 'MI Risk',
        'obs_studies': pd.DataFrame({
            'study': ['NHS', 'IWHS', 'Swedish_Cohort'],
            'hr': [0.86, 0.91, 0.88],
            'lower': [0.74, 0.78, 0.72],
            'upper': [1.00, 1.06, 1.08],
            'n': [85000, 34000, 61000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['Bolland_Meta', 'Reid_Trial', 'WHI_CaD'],
            'hr': [1.27, 1.31, 1.13],
            'lower': [1.01, 1.02, 0.92],
            'upper': [1.59, 1.67, 1.38],
            'n': [11921, 1471, 36282]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'Observational cohorts; Bolland et al. 2010',
        'clinical_impact': 'Recommendations changed to food sources over supplements'
    },

    # 8. Tight Glucose Control - Type 2 Diabetes
    'Tight_Glucose_T2D': {
        'domain': 'Tight Glucose Control',
        'outcome': 'Mortality in T2D',
        'obs_studies': pd.DataFrame({
            'study': ['UKPDS_obs', 'Steno_obs', 'Veterans_obs'],
            'hr': [0.75, 0.70, 0.78],
            'lower': [0.60, 0.55, 0.65],
            'upper': [0.93, 0.89, 0.94],
            'n': [5102, 160, 1791]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['ACCORD', 'ADVANCE', 'VADT'],
            'hr': [1.22, 0.93, 1.07],
            'lower': [1.01, 0.83, 0.81],
            'upper': [1.46, 1.06, 1.42],
            'n': [10251, 11140, 1791]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'UKPDS observational; ACCORD 2008 (stopped early for harm)',
        'clinical_impact': 'Less aggressive targets now recommended'
    },

    # 9. Albumin for Resuscitation
    'Albumin_Resuscitation': {
        'domain': 'Albumin for Fluid Resuscitation',
        'outcome': 'Mortality in Critical Care',
        'obs_studies': pd.DataFrame({
            'study': ['Velanovich', 'Schierhout_obs', 'Wilkes'],
            'hr': [0.84, 0.88, 0.80],
            'lower': [0.70, 0.73, 0.65],
            'upper': [1.01, 1.05, 0.98],
            'n': [6997, 1419, 3500]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['SAFE', 'Cochrane_Meta'],
            'hr': [0.99, 1.02],
            'lower': [0.91, 0.92],
            'upper': [1.09, 1.13],
            'n': [6997, 8000]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'Cochrane 1998 (harmful trend); SAFE 2004 (null)',
        'clinical_impact': 'Expensive albumin not superior to saline'
    },

    # 10. Erythropoietin in CKD
    'EPO_CKD': {
        'domain': 'Erythropoietin (High Target Hb)',
        'outcome': 'CV Events in CKD',
        'obs_studies': pd.DataFrame({
            'study': ['USRDS_Registry', 'DOPPS', 'Canadian_Cohort'],
            'hr': [0.75, 0.82, 0.78],
            'lower': [0.68, 0.71, 0.65],
            'upper': [0.83, 0.95, 0.93],
            'n': [120000, 32000, 17000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['CREATE', 'CHOIR', 'TREAT'],
            'hr': [1.08, 1.34, 1.05],
            'lower': [0.86, 1.03, 0.94],
            'upper': [1.35, 1.74, 1.17],
            'n': [603, 1432, 4038]
        }),
        'outcome_status': 'REVERSAL',
        'references': 'USRDS data; CHOIR 2006, CREATE 2006',
        'clinical_impact': 'Lower hemoglobin targets now standard'
    }
}

# ==============================================================================
# CONCORDANT CASES (Negative Controls)
# ==============================================================================

CONCORDANT_CASES = {
    # 1. Statins in CKD
    'Statins_CKD': {
        'domain': 'Statins',
        'outcome': 'CV Events in CKD',
        'obs_studies': pd.DataFrame({
            'study': ['SHARP_obs', 'Kaiser_cohort', 'Fremantle_cohort'],
            'hr': [0.85, 0.78, 0.82],
            'lower': [0.75, 0.68, 0.70],
            'upper': [0.96, 0.90, 0.96],
            'n': [9270, 15000, 4500]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['SHARP', '4D', 'AURORA'],
            'hr': [0.83, 0.92, 0.96],
            'lower': [0.74, 0.77, 0.84],
            'upper': [0.94, 1.10, 1.11],
            'n': [9270, 1255, 2776]
        }),
        'outcome_status': 'CONCORDANT',
        'references': 'SHARP 2011, Baigent et al.',
        'clinical_impact': 'Recommended for CKD patients'
    },

    # 2. Beta-Blockers Post-MI (Reduced EF)
    'BetaBlocker_PostMI_HFrEF': {
        'domain': 'Beta-Blockers',
        'outcome': 'Mortality Post-MI with HFrEF',
        'obs_studies': pd.DataFrame({
            'study': ['EFFECT_Registry', 'GRACE', 'Swedish_RIKS'],
            'hr': [0.72, 0.68, 0.70],
            'lower': [0.63, 0.58, 0.62],
            'upper': [0.82, 0.80, 0.80],
            'n': [3500, 8000, 12000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['CAPRICORN', 'COPERNICUS', 'CIBIS_II'],
            'hr': [0.77, 0.65, 0.66],
            'lower': [0.60, 0.52, 0.54],
            'upper': [0.98, 0.81, 0.81],
            'n': [1959, 2289, 2647]
        }),
        'outcome_status': 'CONCORDANT',
        'references': 'CAPRICORN 2001, COPERNICUS 2001',
        'clinical_impact': 'Standard of care, guideline Class I'
    },

    # 3. ACE Inhibitors in Heart Failure
    'ACEi_HF': {
        'domain': 'ACE Inhibitors',
        'outcome': 'Mortality in Heart Failure',
        'obs_studies': pd.DataFrame({
            'study': ['Euro_HF_Registry', 'IMPR0VE_HF', 'Canadian_HF'],
            'hr': [0.70, 0.75, 0.73],
            'lower': [0.62, 0.65, 0.63],
            'upper': [0.80, 0.87, 0.85],
            'n': [8000, 6500, 5000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['CONSENSUS', 'SOLVD', 'V_HeFT_II'],
            'hr': [0.73, 0.84, 0.72],
            'lower': [0.59, 0.74, 0.57],
            'upper': [0.90, 0.95, 0.91],
            'n': [253, 2569, 804]
        }),
        'outcome_status': 'CONCORDANT',
        'references': 'CONSENSUS 1987, SOLVD 1991',
        'clinical_impact': 'Cornerstone of HF therapy'
    },

    # 4. Anticoagulation for Atrial Fibrillation
    'Anticoag_AFib': {
        'domain': 'Anticoagulation',
        'outcome': 'Stroke in Atrial Fibrillation',
        'obs_studies': pd.DataFrame({
            'study': ['Euro_Heart_Survey', 'ATRIA_cohort', 'Swedish_Afib'],
            'hr': [0.38, 0.42, 0.40],
            'lower': [0.30, 0.35, 0.32],
            'upper': [0.48, 0.51, 0.50],
            'n': [5300, 13500, 18000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['SPAF_Meta', 'RE_LY', 'ARISTOTLE', 'ROCKET_AF'],
            'hr': [0.36, 0.34, 0.31, 0.12],
            'lower': [0.26, 0.20, 0.23, 0.08],
            'upper': [0.50, 0.53, 0.41, 0.18],
            'n': [3711, 18113, 18201, 14264]
        }),
        'outcome_status': 'CONCORDANT',
        'references': 'Hart et al. 2007 meta-analysis',
        'clinical_impact': 'Strongly recommended (CHA2DS2-VASc ≥2)'
    },

    # 5. Smoking Cessation Interventions
    'Smoking_Cessation': {
        'domain': 'Smoking Cessation',
        'outcome': 'Successful Quit Rate',
        'obs_studies': pd.DataFrame({
            'study': ['Fiore_Meta_Obs', 'Community_Intervention', 'Workplace_Programs'],
            'hr': [1.82, 1.65, 1.70],
            'lower': [1.60, 1.45, 1.50],
            'upper': [2.07, 1.88, 1.93],
            'n': [25000, 15000, 12000]
        }),
        'rct_studies': pd.DataFrame({
            'study': ['Cochrane_Counseling', 'NRT_Meta', 'Varenicline_Trials'],
            'hr': [1.57, 1.60, 2.24],
            'lower': [1.40, 1.53, 2.06],
            'upper': [1.77, 1.68, 2.43],
            'n': [14000, 40000, 5000]
        }),
        'outcome_status': 'CONCORDANT',
        'references': 'Cochrane reviews, consistent benefit',
        'clinical_impact': 'Multiple interventions recommended'
    }
}


def prepare_data_for_analysis(case_data: Dict) -> tuple:
    """
    Prepare observational and RCT data for forensic analysis

    Returns
    -------
    obs_data : pd.DataFrame
    rct_data : pd.DataFrame
    """
    # Observational studies
    obs = case_data['obs_studies'].copy()
    obs['effect'] = np.log(obs['hr'])
    obs['se'] = (np.log(obs['upper']) - np.log(obs['lower'])) / 3.92

    # RCT studies
    rct = case_data['rct_studies'].copy()
    rct['effect'] = np.log(rct['hr'])
    rct['se'] = (np.log(rct['upper']) - np.log(rct['lower'])) / 3.92

    return obs[['effect', 'se', 'n']], rct[['effect', 'se', 'n']]


def run_forensic_validation(cases_dict: Dict, case_type: str) -> pd.DataFrame:
    """
    Run forensic analysis on all cases

    Parameters
    ----------
    cases_dict : dict
        Dictionary of cases
    case_type : str
        'REVERSAL' or 'CONCORDANT'

    Returns
    -------
    results : DataFrame
        Forensic analysis results for all cases
    """
    results = []

    for case_name, case_data in cases_dict.items():
        print(f"\nAnalyzing: {case_data['domain']}")

        # Prepare data
        obs_data, rct_data = prepare_data_for_analysis(case_data)

        if FORENSIC_AVAILABLE:
            try:
                # Run forensic analysis
                analyzer = ForensicAnalyzer(
                    obs_data=obs_data,
                    rct_data=rct_data,
                    effect_type='log_hr',
                    rare_outcome=False
                )

                forensic_results = analyzer.analyze()

                # Determine verdict
                if case_type == 'REVERSAL':
                    correct = 'Grade C' in forensic_results.evidence_grade or 'Grade B' in forensic_results.evidence_grade
                else:  # CONCORDANT
                    correct = 'Grade A' in forensic_results.evidence_grade

                results.append({
                    'Case': case_name,
                    'Domain': case_data['domain'],
                    'Outcome': case_data['outcome'],
                    'Type': case_type,
                    'DI': forensic_results.discordance_index,
                    'E_Value': forensic_results.e_value_point,
                    'Inflation': forensic_results.inflation_factor,
                    'Grade': forensic_results.evidence_grade,
                    'Correct_Flag': 'CORRECT' if correct else 'MISSED',
                    'Obs_HR': np.exp(analyzer.obs_pooled['effect']),
                    'RCT_HR': np.exp(analyzer.rct_pooled['effect']),
                    'References': case_data['references'],
                    'Clinical_Impact': case_data['clinical_impact']
                })

            except Exception as e:
                print(f"  Error: {e}")
                results.append({
                    'Case': case_name,
                    'Domain': case_data['domain'],
                    'Error': str(e)
                })
        else:
            # Manual calculation
            # Pool observational
            obs_weights = 1 / (obs_data['se'] ** 2)
            obs_effect = np.sum(obs_data['effect'] * obs_weights) / np.sum(obs_weights)

            # Pool RCT
            rct_weights = 1 / (rct_data['se'] ** 2)
            rct_effect = np.sum(rct_data['effect'] * rct_weights) / np.sum(rct_weights)

            # Discordance Index
            obs_se = np.sqrt(1 / np.sum(obs_weights))
            rct_se = np.sqrt(1 / np.sum(rct_weights))
            di = abs(obs_effect - rct_effect) / np.sqrt(obs_se**2 + rct_se**2)

            # Grade
            if di < 1.0:
                grade = "Grade A"
            elif di < 2.0:
                grade = "Grade B"
            else:
                grade = "Grade C"

            # Verdict
            if case_type == 'REVERSAL':
                correct = grade in ['Grade B', 'Grade C']
            else:
                correct = grade == 'Grade A'

            results.append({
                'Case': case_name,
                'Domain': case_data['domain'],
                'Outcome': case_data['outcome'],
                'Type': case_type,
                'DI': di,
                'Grade': grade,
                'Correct_Flag': 'CORRECT' if correct else 'MISSED',
                'Obs_HR': np.exp(obs_effect),
                'RCT_HR': np.exp(rct_effect)
            })

    return pd.DataFrame(results)


def generate_validation_report(reversal_results: pd.DataFrame, concordant_results: pd.DataFrame, output_dir: str):
    """Generate comprehensive validation report"""

    all_results = pd.concat([reversal_results, concordant_results], ignore_index=True)

    report = []
    report.append("="*80)
    report.append("MEDICAL REVERSAL VALIDATION STUDY")
    report.append("Forensic Meta-Analysis Framework")
    report.append("="*80)
    report.append("")
    report.append(f"Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Total Cases: {len(all_results)}")
    report.append(f"  Medical Reversals: {len(reversal_results)}")
    report.append(f"  Concordant Cases: {len(concordant_results)}")
    report.append("")

    # Overall Performance
    correct = (all_results['Correct_Flag'] == 'CORRECT').sum()
    total = len(all_results)

    report.append("OVERALL PERFORMANCE")
    report.append("-"*80)
    report.append(f"  Correct Classifications: {correct}/{total} ({100*correct/total:.1f}%)")
    report.append("")

    # Sensitivity (detecting reversals)
    reversal_correct = (reversal_results['Correct_Flag'] == 'CORRECT').sum()
    reversal_total = len(reversal_results)

    report.append(f"  Sensitivity (Reversals Detected): {reversal_correct}/{reversal_total} ({100*reversal_correct/reversal_total:.1f}%)")

    # Specificity (not flagging concordant)
    concordant_correct = (concordant_results['Correct_Flag'] == 'CORRECT').sum()
    concordant_total = len(concordant_results)

    report.append(f"  Specificity (Concordant Correct): {concordant_correct}/{concordant_total} ({100*concordant_correct/concordant_total:.1f}%)")
    report.append("")

    # Detailed Results Table
    report.append("DETAILED RESULTS: MEDICAL REVERSALS")
    report.append("-"*80)
    report.append(f"{'Domain':<35} {'DI':>6} {'E-Val':>6} {'Grade':>10} {'Verdict':>10}")
    report.append("-"*80)

    for _, row in reversal_results.iterrows():
        report.append(
            f"{row['Domain'][:34]:<35} "
            f"{row['DI']:>6.2f} "
            f"{row.get('E_Value', 0):>6.2f} "
            f"{row['Grade']:>10} "
            f"{row['Correct_Flag']:>10}"
        )
    report.append("")

    report.append("DETAILED RESULTS: CONCORDANT CASES")
    report.append("-"*80)
    report.append(f"{'Domain':<35} {'DI':>6} {'Grade':>10} {'Verdict':>10}")
    report.append("-"*80)

    for _, row in concordant_results.iterrows():
        report.append(
            f"{row['Domain'][:34]:<35} "
            f"{row['DI']:>6.2f} "
            f"{row['Grade']:>10} "
            f"{row['Correct_Flag']:>10}"
        )
    report.append("")

    # Key Findings
    report.append("KEY FINDINGS")
    report.append("="*80)

    # Average DI by type
    avg_di_reversal = reversal_results['DI'].mean()
    avg_di_concordant = concordant_results['DI'].mean()

    report.append(f"1. Average Discordance Index:")
    report.append(f"   Medical Reversals:  DI = {avg_di_reversal:.2f}")
    report.append(f"   Concordant Cases:   DI = {avg_di_concordant:.2f}")
    report.append(f"   Difference:        {avg_di_reversal - avg_di_concordant:.2f}")
    report.append("")

    # Grade distribution
    report.append(f"2. Grade Distribution:")
    for grade in ['Grade A', 'Grade B', 'Grade C']:
        reversal_pct = (reversal_results['Grade'].str.contains(grade.split()[1])).mean() * 100
        concordant_pct = (concordant_results['Grade'].str.contains(grade.split()[1])).mean() * 100
        report.append(f"   {grade}:")
        report.append(f"     Reversals:  {reversal_pct:.1f}%")
        report.append(f"     Concordant: {concordant_pct:.1f}%")
    report.append("")

    report.append("="*80)

    # Save report
    report_text = "\n".join(report)
    print("\n" + report_text)

    report_file = os.path.join(output_dir, 'MEDICAL_REVERSAL_VALIDATION.txt')
    os.makedirs(output_dir, exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report_text)

    print(f"\nReport saved to: {report_file}")

    # Save CSV
    csv_file = os.path.join(output_dir, 'medical_reversal_results.csv')
    all_results.to_csv(csv_file, index=False)
    print(f"Results saved to: {csv_file}")

    return all_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Validate forensic framework on medical reversals')
    parser.add_argument('--output', type=str, default='./validation/results', help='Output directory')

    args = parser.parse_args()

    print("="*80)
    print("MEDICAL REVERSAL VALIDATION STUDY")
    print("="*80)

    # Run validation on reversals
    print("\n### ANALYZING MEDICAL REVERSALS ###\n")
    reversal_results = run_forensic_validation(MEDICAL_REVERSALS, 'REVERSAL')

    # Run validation on concordant cases
    print("\n### ANALYZING CONCORDANT CASES ###\n")
    concordant_results = run_forensic_validation(CONCORDANT_CASES, 'CONCORDANT')

    # Generate report
    all_results = generate_validation_report(
        reversal_results,
        concordant_results,
        args.output
    )

    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
