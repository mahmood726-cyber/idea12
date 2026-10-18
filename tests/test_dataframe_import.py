"""Data transport fixtures: no real trial identifiers or clinical findings."""
import numpy as np
import pandas as pd
import pytest

from netmetareg.core.data_structure import NMAData


def contrast_frame():
    return pd.DataFrame({"study": ["fixture-one", "fixture-two"],
        "treatment_1": ["A", "A"], "treatment_2": ["B", "B"],
        "effect": [0.2, 0.3], "se": [0.1, 0.2], "covariate": [1, 2]})


def read(frame, **kwargs):
    return NMAData.from_dataframe(frame, effect_col="effect", se_col="se", **kwargs)


def test_multiple_contrasts_are_not_silently_truncated():
    frame = contrast_frame()
    frame["study"] = "fixture-one"
    with pytest.raises(ValueError, match="one row per study"):
        read(frame)


@pytest.mark.parametrize("missing", [None, np.nan, "", "  "])
def test_missing_study_identifier_is_not_dropped(missing):
    frame = contrast_frame()
    frame.loc[1, "study"] = missing
    with pytest.raises(ValueError, match="study"):
        read(frame)


@pytest.mark.parametrize("column", ["study", "treatment_1", "treatment_2", "effect", "se", "covariate"])
def test_requested_columns_are_required(column):
    with pytest.raises(ValueError, match="column"):
        read(contrast_frame().drop(columns=column), covariate_cols=["covariate"])


def test_duplicate_column_labels_are_rejected():
    frame = contrast_frame()
    frame = pd.concat([frame, frame[["se"]]], axis=1)
    with pytest.raises(ValueError, match="column"):
        read(frame)


def test_valid_contrasts_keep_every_row_without_modifying_source():
    frame = contrast_frame()
    before = frame.copy(deep=True)
    data = read(frame, covariate_cols=["covariate"])
    assert [s.study_id for s in data.studies] == frame.study.tolist()
    assert [s.effects[0] for s in data.studies] == frame.effect.tolist()
    assert [s.covariates["covariate"] for s in data.studies] == [1, 2]
    pd.testing.assert_frame_equal(frame, before)


def test_arm_format_requires_explicit_effect_column():
    frame = pd.DataFrame({"study": ["fixture", "fixture"], "treatment": ["A", "B"], "se": [0, 0.1]})
    with pytest.raises(ValueError, match="effect"):
        read(frame, format="arm")


def test_multiarm_covariate_cannot_be_silently_taken_from_first_row():
    frame = pd.DataFrame({"study": ["fixture"] * 3, "treatment": ["A", "B", "C"],
        "effect": [0, 0.2, 0.3], "se": [0, 0.1, 0.2], "covariate": [1, 2, 1]})
    with pytest.raises(ValueError, match="covariate"):
        read(frame, format="arm", covariate_cols=["covariate"])


def test_valid_multiarm_import_keeps_all_comparisons():
    frame = pd.DataFrame({"study": ["fixture"] * 3, "treatment": ["A", "B", "C"],
        "effect": [0, 0.2, 0.3], "se": [0, 0.1, 0.2], "covariate": [1] * 3})
    study = read(frame, format="arm", covariate_cols=["covariate"]).studies[0]
    assert study.treatments == ["A", "B", "C"]
    np.testing.assert_array_equal(study.effects, [0.2, 0.3])
    np.testing.assert_array_equal(study.se, [0.1, 0.2])


def test_unused_study_categories_do_not_create_empty_studies():
    frame = contrast_frame()
    frame["study"] = pd.Categorical(frame.study, categories=["fixture-one", "fixture-two", "unused"])
    assert read(frame).n_studies == 2


def test_identifiers_cannot_collide_after_string_conversion():
    frame = contrast_frame()
    frame["study"] = [1, "1"]
    with pytest.raises(ValueError, match="Distinct study identifiers"):
        read(frame)
