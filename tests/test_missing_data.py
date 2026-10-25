import numpy as np
import pandas as pd
import pytest
from src.features import compute_features_for_student

def test_missing_is_never_zero():
    records = [{'student_id': 'S-MISS', 'week': 1, 'attendance_pct': 90.0, 'assignment_status': 'Not Due', 'quiz_score': None, 'quiz_taken': False}, {'student_id': 'S-MISS', 'week': 2, 'attendance_pct': np.nan, 'assignment_status': 'Submitted', 'quiz_score': 80.0, 'quiz_taken': True}, {'student_id': 'S-MISS', 'week': 3, 'attendance_pct': 90.0, 'assignment_status': 'Not Due', 'quiz_score': 80.0, 'quiz_taken': True}]
    df = pd.DataFrame(records)
    feat = compute_features_for_student(df, as_of_week=3)
    assert feat['att_mean_recent'] == pytest.approx(90.0)
    assert feat['att_mean_overall'] == pytest.approx(90.0)
    assert feat['att_missing_rate'] == pytest.approx(1 / 3, abs=0.01)

def test_insufficient_data_flag():
    records = [{'student_id': 'S-SPARSE', 'week': 1, 'attendance_pct': np.nan, 'assignment_status': 'Not Due', 'quiz_score': None, 'quiz_taken': False}, {'student_id': 'S-SPARSE', 'week': 2, 'attendance_pct': 80.0, 'assignment_status': 'Not Due', 'quiz_score': None, 'quiz_taken': False}, {'student_id': 'S-SPARSE', 'week': 3, 'attendance_pct': np.nan, 'assignment_status': 'Not Due', 'quiz_score': None, 'quiz_taken': False}]
    df = pd.DataFrame(records)
    feat = compute_features_for_student(df, as_of_week=3)
    assert feat['att_insufficient'] is True
    assert np.isnan(feat['att_mean_recent'])
    assert np.isnan(feat['att_trend'])
    assert feat['data_confidence_level'] in ['Medium', 'Low']

def test_data_confidence_formula():
    records = [{'student_id': 'S-PERFECT', 'week': 1, 'attendance_pct': 95.0, 'assignment_status': 'Not Due', 'quiz_score': None, 'quiz_taken': False}, {'student_id': 'S-PERFECT', 'week': 2, 'attendance_pct': 95.0, 'assignment_status': 'Submitted', 'quiz_score': 85.0, 'quiz_taken': True}, {'student_id': 'S-PERFECT', 'week': 3, 'attendance_pct': 95.0, 'assignment_status': 'Not Due', 'quiz_score': 85.0, 'quiz_taken': True}, {'student_id': 'S-PERFECT', 'week': 4, 'attendance_pct': 95.0, 'assignment_status': 'Submitted', 'quiz_score': None, 'quiz_taken': False}]
    df = pd.DataFrame(records)
    feat = compute_features_for_student(df, as_of_week=4)
    assert feat['data_confidence_score'] == pytest.approx(1.0)
    assert feat['data_confidence_level'] == 'High'


def test_all_attendance_missing_is_insufficient_data_not_priority_checkin():
    from src.rules_engine import RulesEngine
    # Student with 100% missing attendance across all weeks
    records = [
        {'student_id': 'S-NO-ATT', 'week': 1, 'attendance_pct': np.nan, 'assignment_status': 'Not Due', 'quiz_score': None, 'quiz_taken': False},
        {'student_id': 'S-NO-ATT', 'week': 2, 'attendance_pct': np.nan, 'assignment_status': 'Submitted', 'quiz_score': 80.0, 'quiz_taken': True},
        {'student_id': 'S-NO-ATT', 'week': 3, 'attendance_pct': np.nan, 'assignment_status': 'Not Due', 'quiz_score': 80.0, 'quiz_taken': True},
        {'student_id': 'S-NO-ATT', 'week': 4, 'attendance_pct': np.nan, 'assignment_status': 'Submitted', 'quiz_score': 80.0, 'quiz_taken': True},
    ]
    df = pd.DataFrame(records)
    feat = compute_features_for_student(df, as_of_week=4)
    engine = RulesEngine()
    result = engine.evaluate_student(feat)

    assert result['support_level'] == 'Insufficient Data'
    assert result['support_level'] != 'Priority Check-in'
    assert result['needs_manual_check'] is True

