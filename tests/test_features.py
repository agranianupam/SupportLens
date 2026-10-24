import numpy as np
import pandas as pd
import pytest
from src.features import compute_features, compute_features_for_student, compute_linear_trend

def test_linear_trend_calculation():
    assert compute_linear_trend([50.0, 50.0, 50.0]) == pytest.approx(0.0)
    assert compute_linear_trend([50.0, 55.0, 60.0, 65.0]) == pytest.approx(5.0)
    assert compute_linear_trend([80.0, 76.0, 72.0]) == pytest.approx(-4.0)
    assert compute_linear_trend([80.0, np.nan, 72.0]) == pytest.approx(-4.0)
    assert compute_linear_trend([np.nan, 50.0, np.nan]) == 0.0

def test_no_lookahead_bias():
    records = []
    for w in range(1, 13):
        records.append({'student_id': 'S-TEST', 'week': w, 'attendance_pct': 50.0 if w <= 4 else 100.0, 'assignment_status': 'Submitted' if w % 2 == 0 else 'Not Due', 'quiz_score': 60.0 if w in [2, 3] else 95.0, 'quiz_taken': True if w in [2, 3, 5, 6, 8, 9, 11, 12] else False})
    df = pd.DataFrame(records)
    feat_w4 = compute_features_for_student(df, as_of_week=4)
    feat_w8 = compute_features_for_student(df, as_of_week=8)
    assert feat_w4['att_mean_recent'] == pytest.approx(50.0)
    assert feat_w4['weeks_observed'] == 4
    assert feat_w8['att_mean_recent'] == pytest.approx(100.0)
    assert feat_w8['weeks_observed'] == 8

def test_streaks_and_counts():
    records = [{'student_id': 'S-STREAK', 'week': 1, 'attendance_pct': 80.0, 'assignment_status': 'Not Due', 'quiz_score': None, 'quiz_taken': False}, {'student_id': 'S-STREAK', 'week': 2, 'attendance_pct': 60.0, 'assignment_status': 'Missing', 'quiz_score': 40.0, 'quiz_taken': True}, {'student_id': 'S-STREAK', 'week': 3, 'attendance_pct': 65.0, 'assignment_status': 'Not Due', 'quiz_score': 45.0, 'quiz_taken': True}, {'student_id': 'S-STREAK', 'week': 4, 'attendance_pct': 70.0, 'assignment_status': 'Missing', 'quiz_score': None, 'quiz_taken': False}]
    df = pd.DataFrame(records)
    feat = compute_features_for_student(df, as_of_week=4, att_cutoff=75.0, quiz_cutoff=50.0)
    assert feat['low_att_streak'] == 3
    assert feat['missing_streak'] == 2
    assert feat['missing_count_recent'] == 2
    assert feat['quiz_below_threshold_count'] == 2
