import pytest
import pandas as pd
import numpy as np
from src.evaluation import (
    run_multiseed_evaluation,
    run_ablation_study,
    compute_earliness,
)
from src.features import compute_features
from src.data_generator import generate_synthetic_data
from src.data_quality import clean_and_validate_data


def test_multiseed_evaluation_row_counts(tmp_path):
    # Use 2 seeds in the test to keep test fast, or test full 5 seeds
    seeds = [42, 7]
    res = run_multiseed_evaluation(seeds=seeds, as_of_week=10, tmp_base_dir=str(tmp_path))
    detailed_df = res['detailed_df']
    summary_df = res['summary_df']

    # For 5 methods and len(seeds) seeds, each method should have len(seeds) rows
    for method in ['Rule Engine', 'Logistic Regression', 'Shallow Decision Tree',
                   'Baseline: Attendance < 75%', 'Baseline: Quiz < 50%']:
        assert len(detailed_df[detailed_df['Method'] == method]) == len(seeds)

    assert len(summary_df) == 5


def test_ablation_configs():
    # Load dataset
    students_df = pd.read_csv('data/students.csv')
    weekly_df = pd.read_csv('data/weekly_records.csv')
    labels_df = pd.read_csv('data/ground_truth_support_need.csv')

    cleaned_w, _ = clean_and_validate_data(weekly_df, students_df)
    features_df = compute_features(cleaned_w, as_of_week=10)

    ablation_df = run_ablation_study(
        features_df=features_df,
        labels_df=labels_df,
        students_df=students_df,
        weekly_df=cleaned_w,
        as_of_week=10,
    )

    # Exactly 6 configurations
    assert len(ablation_df) == 6
    expected_configs = [
        'Full SupportLens System',
        'Without M1 (High Quiz Mastery)',
        'Without M2 (Upward Trend)',
        'Without Persistence Rule',
        'Without Mitigations & Persistence',
        'Without Compound Rules C1/C2',
    ]
    for exp in expected_configs:
        assert exp in ablation_df['Configuration'].values

    # Check required columns
    for col in ['Precision', 'Recall', 'F1 Score', 'False Positives', 'Alert Burden (%)', 'Impact Summary']:
        assert col in ablation_df.columns
        assert not ablation_df[col].isna().any()


def test_earliness_no_lookahead():
    students_df = pd.read_csv('data/students.csv')
    weekly_df = pd.read_csv('data/weekly_records.csv')
    labels_df = pd.read_csv('data/ground_truth_support_need.csv')

    # Poison future weeks (weeks 9, 10, 11, 12) with corrupted/insufficient records
    poisoned_weekly = weekly_df.copy()
    poisoned_weekly.loc[poisoned_weekly['week'] > 8, 'attendance_pct'] = 0.0
    poisoned_weekly.loc[poisoned_weekly['week'] > 8, 'quiz_score'] = 0.0
    poisoned_weekly.loc[poisoned_weekly['week'] > 8, 'assignment_status'] = 'Missing'

    # Compute earliness as of week 8
    res_clean = compute_earliness(weekly_df, students_df, labels_df, as_of_week=8)
    res_poisoned = compute_earliness(poisoned_weekly, students_df, labels_df, as_of_week=8)

    # Because compute_earliness truncates to week <= as_of_week, future poisoned data MUST NOT affect the result
    assert res_clean['detected_students_count'] == res_poisoned['detected_students_count']
    assert res_clean['avg_first_flag_week'] == res_poisoned['avg_first_flag_week']
    assert res_clean['mean_relative_earliness'] == res_poisoned['mean_relative_earliness']
