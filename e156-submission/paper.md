Mahmood Ahmad
Tahir Heart Institute
mahmood.ahmad2@nhs.net

Network Meta-Regression with Forensic Bias Detection for Observational-RCT Discordance

Can a quantitative forensic framework detect design-based bias in network meta-analysis when observational and randomized evidence disagree about treatment effects? We assembled fifteen medical reversal cases with known outcomes alongside concordant controls, implementing netmetareg with modules for network meta-analysis, meta-regression, node-splitting, and LASSO selection. The forensic module computes three metrics: a Discordance Index quantifying observational-versus-RCT disagreement magnitude, E-values measuring confounding vulnerability, and inflation ratios assessing precision discrepancies between designs. ROC analysis of the Discordance Index across fifteen reversal and control cases yielded an area under the curve of 0.900 with optimized thresholds achieving 100 percent sensitivity for detecting confirmed reversals. Threshold recalibration using the Youden criterion and balanced operating points confirmed stable classification across alternative boundary configurations. Forensic bias metrics integrated into network meta-regression provide an evidence-based early warning system for unreliable observational signals before costly confirmatory trials. The limitation of retrospective validation is that prospective prediction on emerging discordances remains untested beyond the illustrative case.

Outside Notes

Type: methods
Primary estimand: Discordance Index ROC AUC
App: netmetareg v0.1.0
Data: 15 medical reversal cases + concordant controls
Code: https://github.com/mahmood726-cyber/idea12
Version: 0.1.0
Validation: DRAFT

References

1. Carlisle JB. Data fabrication and other reasons for non-random sampling in 5087 randomised, controlled trials in anaesthetic and general medical journals. Anaesthesia. 2017;72(8):944-952.
2. Brown NJL, Heathers JAJ. The GRIM test: a simple technique detects numerous anomalies in the reporting of results in psychology. Soc Psychol Personal Sci. 2017;8(4):363-369.
3. Borenstein M, Hedges LV, Higgins JPT, Rothstein HR. Introduction to Meta-Analysis. 2nd ed. Wiley; 2021.
