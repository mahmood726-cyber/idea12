"""
Data structures for network meta-analysis.

This module defines the core data structures for storing and manipulating
network meta-analysis data, including study-level information, treatment
comparisons, and covariates.
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Union, Tuple
from dataclasses import dataclass, field


@dataclass
class Study:
    """Represents a single study in the network meta-analysis.

    Attributes:
        study_id: Unique identifier for the study
        treatments: List of treatment arms in the study
        effects: Treatment effects (e.g., log odds ratios, mean differences)
        se: Standard errors of treatment effects
        n: Sample sizes for each arm
        covariates: Study-level covariates (e.g., mean age, % female)
        design: Study design type (e.g., 'RCT', 'observational')
        baseline_risk: Baseline risk in control arm (if applicable)
    """
    study_id: str
    treatments: List[str]
    effects: Optional[np.ndarray] = None
    se: Optional[np.ndarray] = None
    n: Optional[np.ndarray] = None
    covariates: Dict[str, float] = field(default_factory=dict)
    design: str = 'RCT'
    baseline_risk: Optional[float] = None

    def __post_init__(self):
        """Validate data consistency."""
        n_arms = len(self.treatments)
        if self.effects is not None and len(self.effects) != n_arms - 1:
            raise ValueError(f"Number of effects ({len(self.effects)}) should be n_arms - 1 ({n_arms - 1})")
        if self.se is not None and len(self.se) != n_arms - 1:
            raise ValueError(f"Number of SEs ({len(self.se)}) should be n_arms - 1 ({n_arms - 1})")
        if self.n is not None and len(self.n) != n_arms:
            raise ValueError(f"Number of sample sizes ({len(self.n)}) should match n_arms ({n_arms})")

    @property
    def n_arms(self) -> int:
        """Number of treatment arms."""
        return len(self.treatments)

    @property
    def is_two_arm(self) -> bool:
        """Whether this is a two-arm study."""
        return self.n_arms == 2

    @property
    def is_multi_arm(self) -> bool:
        """Whether this is a multi-arm study."""
        return self.n_arms > 2


class NMAData:
    """Container for network meta-analysis data.

    This class handles data preparation, validation, and transformation
    for network meta-analysis and meta-regression.

    Attributes:
        studies: List of Study objects
        treatments: Unique treatments in the network
        covariates: Names of study-level covariates
        reference_treatment: Reference treatment for comparisons
    """

    def __init__(self,
                 studies: Optional[List[Study]] = None,
                 reference_treatment: Optional[str] = None):
        """Initialize NMAData.

        Args:
            studies: List of Study objects
            reference_treatment: Reference treatment (defaults to first treatment)
        """
        self.studies = studies or []
        self._reference_treatment = reference_treatment
        self._treatments = None
        self._covariate_names = None

    @property
    def n_studies(self) -> int:
        """Number of studies."""
        return len(self.studies)

    @property
    def treatments(self) -> List[str]:
        """Unique treatments in the network."""
        if self._treatments is None:
            treatment_set = set()
            for study in self.studies:
                treatment_set.update(study.treatments)
            self._treatments = sorted(list(treatment_set))
        return self._treatments

    @property
    def n_treatments(self) -> int:
        """Number of unique treatments."""
        return len(self.treatments)

    @property
    def reference_treatment(self) -> str:
        """Reference treatment for comparisons."""
        if self._reference_treatment is None:
            self._reference_treatment = self.treatments[0]
        return self._reference_treatment

    @reference_treatment.setter
    def reference_treatment(self, value: str):
        """Set reference treatment."""
        if value not in self.treatments:
            raise ValueError(f"Reference treatment '{value}' not in network")
        self._reference_treatment = value

    @property
    def covariate_names(self) -> List[str]:
        """Names of study-level covariates."""
        if self._covariate_names is None:
            cov_set = set()
            for study in self.studies:
                cov_set.update(study.covariates.keys())
            self._covariate_names = sorted(list(cov_set))
        return self._covariate_names

    @property
    def n_covariates(self) -> int:
        """Number of covariates."""
        return len(self.covariate_names)

    def add_study(self, study: Study):
        """Add a study to the dataset.

        Args:
            study: Study object to add
        """
        self.studies.append(study)
        # Reset cached properties
        self._treatments = None
        self._covariate_names = None

    @classmethod
    def from_dataframe(cls,
                      df: pd.DataFrame,
                      study_col: str = 'study',
                      treatment_col: str = 'treatment',
                      effect_col: Optional[str] = None,
                      se_col: Optional[str] = None,
                      n_col: Optional[str] = None,
                      covariate_cols: Optional[List[str]] = None,
                      format: str = 'contrast') -> 'NMAData':
        """Create NMAData from a pandas DataFrame.

        Args:
            df: Input dataframe
            study_col: Column name for study identifier
            treatment_col: Column name for treatment
            effect_col: Column name for effect size
            se_col: Column name for standard error
            n_col: Column name for sample size
            covariate_cols: List of covariate column names
            format: Data format ('contrast' or 'arm')

        Returns:
            NMAData object
        """
        if format not in ['contrast', 'arm']:
            raise ValueError("format must be 'contrast' or 'arm'")

        covariate_cols = covariate_cols or []
        studies = []

        for study_id, group in df.groupby(study_col):
            if format == 'contrast':
                # Contrast-based format: one row per study with treatment comparison
                row = group.iloc[0]
                treatments = [row[treatment_col + '_1'], row[treatment_col + '_2']]
                effects = np.array([row[effect_col]]) if effect_col else None
                se = np.array([row[se_col]]) if se_col else None
                n = np.array([row[n_col + '_1'], row[n_col + '_2']]) if n_col else None
            else:
                # Arm-based format: one row per treatment arm
                treatments = group[treatment_col].tolist()
                if effect_col and effect_col in group.columns:
                    effects = group[effect_col].values[1:]  # Relative to first arm
                else:
                    effects = None
                se = group[se_col].values[1:] if se_col else None
                n = group[n_col].values if n_col else None

            # Extract covariates
            covariates = {}
            for cov in covariate_cols:
                if cov in group.columns:
                    covariates[cov] = float(group[cov].iloc[0])

            study = Study(
                study_id=str(study_id),
                treatments=treatments,
                effects=effects,
                se=se,
                n=n,
                covariates=covariates
            )
            studies.append(study)

        return cls(studies=studies)

    def to_dataframe(self, format: str = 'long') -> pd.DataFrame:
        """Convert to pandas DataFrame.

        Args:
            format: Output format ('long', 'wide', or 'contrast')

        Returns:
            DataFrame representation
        """
        if format == 'long':
            # Long format: one row per study-treatment pair
            rows = []
            for study in self.studies:
                for i, treatment in enumerate(study.treatments):
                    row = {
                        'study': study.study_id,
                        'treatment': treatment,
                        'arm': i + 1,
                        'n_arms': study.n_arms,
                    }
                    if study.n is not None:
                        row['n'] = study.n[i]
                    if i > 0 and study.effects is not None:
                        row['effect'] = study.effects[i - 1]
                        if study.se is not None:
                            row['se'] = study.se[i - 1]
                    row.update(study.covariates)
                    rows.append(row)
            return pd.DataFrame(rows)

        elif format == 'contrast':
            # Contrast format: one row per study (for 2-arm) or comparison (multi-arm)
            rows = []
            for study in self.studies:
                base_row = {'study': study.study_id}
                base_row.update(study.covariates)

                if study.is_two_arm:
                    row = base_row.copy()
                    row['treatment_1'] = study.treatments[0]
                    row['treatment_2'] = study.treatments[1]
                    if study.effects is not None:
                        row['effect'] = study.effects[0]
                    if study.se is not None:
                        row['se'] = study.se[0]
                    if study.n is not None:
                        row['n_1'] = study.n[0]
                        row['n_2'] = study.n[1]
                    rows.append(row)
                else:
                    # Multi-arm: create rows for each comparison to baseline
                    for i in range(1, study.n_arms):
                        row = base_row.copy()
                        row['treatment_1'] = study.treatments[0]
                        row['treatment_2'] = study.treatments[i]
                        if study.effects is not None:
                            row['effect'] = study.effects[i - 1]
                        if study.se is not None:
                            row['se'] = study.se[i - 1]
                        if study.n is not None:
                            row['n_1'] = study.n[0]
                            row['n_2'] = study.n[i]
                        rows.append(row)
            return pd.DataFrame(rows)

        else:
            raise ValueError(f"Unknown format: {format}")

    def get_covariate_matrix(self,
                            center: bool = True,
                            scale: bool = False) -> Tuple[np.ndarray, Dict]:
        """Get covariate matrix for all studies.

        Args:
            center: Whether to center covariates at network mean
            scale: Whether to standardize covariates

        Returns:
            Tuple of (covariate matrix, centering/scaling parameters)
        """
        n = self.n_studies
        p = self.n_covariates
        X = np.zeros((n, p))

        for i, study in enumerate(self.studies):
            for j, cov_name in enumerate(self.covariate_names):
                if cov_name in study.covariates:
                    X[i, j] = study.covariates[cov_name]
                else:
                    X[i, j] = np.nan

        params = {}
        if center or scale:
            means = np.nanmean(X, axis=0)
            params['means'] = means
            if center:
                X = X - means

        if scale:
            stds = np.nanstd(X, axis=0)
            stds[stds == 0] = 1  # Avoid division by zero
            params['stds'] = stds
            X = X / stds

        return X, params

    def get_treatment_matrix(self) -> np.ndarray:
        """Get design matrix for treatments.

        Returns:
            Treatment indicator matrix (n_comparisons × n_treatments)
        """
        comparisons = []
        for study in self.studies:
            if study.is_two_arm:
                comparisons.append((study.treatments[0], study.treatments[1]))
            else:
                # Multi-arm: all comparisons to first arm
                for i in range(1, study.n_arms):
                    comparisons.append((study.treatments[0], study.treatments[i]))

        n_comp = len(comparisons)
        n_trt = self.n_treatments
        X = np.zeros((n_comp, n_trt))

        treatment_idx = {t: i for i, t in enumerate(self.treatments)}

        for i, (t1, t2) in enumerate(comparisons):
            X[i, treatment_idx[t1]] = -1
            X[i, treatment_idx[t2]] = 1

        return X

    def validate(self) -> List[str]:
        """Validate data quality and completeness.

        Returns:
            List of validation warnings/errors
        """
        warnings = []

        # Check for missing treatments
        if self.n_treatments < 3:
            warnings.append(f"Network has only {self.n_treatments} treatments. "
                          "Network meta-analysis requires at least 3.")

        # Check for missing data
        for study in self.studies:
            if study.effects is None:
                warnings.append(f"Study {study.study_id} missing effect sizes")
            if study.se is None:
                warnings.append(f"Study {study.study_id} missing standard errors")

        # Check for disconnected network (to be implemented in TreatmentNetwork)

        # Check covariate completeness
        for cov_name in self.covariate_names:
            n_missing = sum(1 for s in self.studies if cov_name not in s.covariates)
            if n_missing > 0:
                pct = 100 * n_missing / self.n_studies
                warnings.append(f"Covariate '{cov_name}' missing in {n_missing} "
                              f"studies ({pct:.1f}%)")

        return warnings

    def summary(self) -> pd.DataFrame:
        """Generate summary statistics.

        Returns:
            DataFrame with summary information
        """
        summary_data = {
            'n_studies': self.n_studies,
            'n_treatments': self.n_treatments,
            'n_covariates': self.n_covariates,
            'n_two_arm': sum(1 for s in self.studies if s.is_two_arm),
            'n_multi_arm': sum(1 for s in self.studies if s.is_multi_arm),
        }

        # Add covariate summaries
        X, _ = self.get_covariate_matrix(center=False, scale=False)
        for i, cov_name in enumerate(self.covariate_names):
            cov_values = X[:, i]
            valid_values = cov_values[~np.isnan(cov_values)]
            if len(valid_values) > 0:
                summary_data[f'{cov_name}_mean'] = np.mean(valid_values)
                summary_data[f'{cov_name}_sd'] = np.std(valid_values)
                summary_data[f'{cov_name}_min'] = np.min(valid_values)
                summary_data[f'{cov_name}_max'] = np.max(valid_values)

        return pd.DataFrame([summary_data])
