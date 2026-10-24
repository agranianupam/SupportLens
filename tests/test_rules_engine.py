import numpy as np
import pytest
from src.rules_engine import RulesEngine

@pytest.fixture
def engine():
    return RulesEngine()

def test_on_track_student(engine):
    features = {'student_id': 'S-STEADY', 'as_of_week': 10, 'att_mean_recent': 92.0, 'att_drop_from_baseline': 0.0, 'low_att_streak': 0, 'att_insufficient': False, 'missing_count_recent': 0, 'missing_streak': 0, 'late_rate_recent': 0.0, 'submission_rate_overall': 1.0, 'assign_insufficient': False, 'quiz_mean_recent': 85.0, 'quiz_trend': 0.5, 'quiz_below_threshold_count': 0, 'quiz_participation_rate': 1.0, 'quiz_insufficient': False, 'data_confidence_level': 'High', 'data_confidence_score': 1.0}
    res = engine.evaluate_student(features)
    assert res['support_level'] == 'On Track'
    assert res['score'] == 0
    assert len(res['fired_rules']) == 0

def test_chronic_low_student(engine):
    features = {'student_id': 'S-CHRONIC', 'as_of_week': 10, 'att_mean_recent': 52.0, 'att_drop_from_baseline': 0.0, 'low_att_streak': 4, 'att_insufficient': False, 'missing_count_recent': 2, 'missing_streak': 2, 'late_rate_recent': 0.25, 'submission_rate_overall': 0.5, 'assign_insufficient': False, 'quiz_mean_recent': 42.0, 'quiz_trend': -1.0, 'quiz_below_threshold_count': 3, 'quiz_participation_rate': 0.5, 'quiz_insufficient': False, 'data_confidence_level': 'High', 'data_confidence_score': 0.95}
    res = engine.evaluate_student(features)
    assert res['support_level'] == 'Priority Check-in'
    assert res['score'] >= 8
    assert 'Attendance Concern' in res['categories']
    assert 'Submission Concern' in res['categories']
    assert 'Assessment Concern' in res['categories']
    assert 'Engagement Drop (Compound)' in res['categories']

def test_mitigating_rule_m1(engine):
    features = {'student_id': 'S-STRONG-IRREGULAR', 'as_of_week': 10, 'att_mean_recent': 65.0, 'att_drop_from_baseline': 0.0, 'low_att_streak': 1, 'att_insufficient': False, 'missing_count_recent': 0, 'missing_streak': 0, 'late_rate_recent': 0.0, 'submission_rate_overall': 1.0, 'assign_insufficient': False, 'quiz_mean_recent': 88.0, 'quiz_trend': 0.2, 'quiz_below_threshold_count': 0, 'quiz_participation_rate': 1.0, 'quiz_insufficient': False, 'data_confidence_level': 'High', 'data_confidence_score': 0.95}
    res = engine.evaluate_student(features)
    assert res['score'] == 0
    assert res['support_level'] == 'On Track'
    assert any((r['id'] == 'M1' for r in res['mitigating_rules']))

def test_data_confidence_cap_m3(engine):
    features = {'student_id': 'S-LOW-CONF', 'as_of_week': 10, 'att_mean_recent': 55.0, 'att_drop_from_baseline': 0.0, 'low_att_streak': 0, 'att_insufficient': False, 'missing_count_recent': 2, 'missing_streak': 0, 'late_rate_recent': 0.0, 'submission_rate_overall': 0.7, 'assign_insufficient': False, 'quiz_mean_recent': 70.0, 'quiz_trend': 0.0, 'quiz_below_threshold_count': 0, 'quiz_participation_rate': 1.0, 'quiz_insufficient': False, 'data_confidence_level': 'Low', 'data_confidence_score': 0.45}
    res = engine.evaluate_student(features)
    assert res['support_level'] == 'Monitor'
    assert res['needs_manual_check'] is True
    assert any((r['id'] == 'M3' for r in res['mitigating_rules']))

def test_persistence_rule(engine):
    features = {'student_id': 'S-DIP', 'as_of_week': 10, 'att_mean_recent': 58.0, 'att_drop_from_baseline': 10.0, 'low_att_streak': 1, 'att_insufficient': False, 'missing_count_recent': 2, 'missing_streak': 1, 'late_rate_recent': 0.0, 'submission_rate_overall': 0.8, 'assign_insufficient': False, 'quiz_mean_recent': 72.0, 'quiz_trend': 0.0, 'quiz_below_threshold_count': 0, 'quiz_participation_rate': 1.0, 'quiz_insufficient': False, 'data_confidence_level': 'High', 'data_confidence_score': 0.95}
    historical_scores = [1, 1]
    res = engine.evaluate_student(features, historical_scores=historical_scores)
    assert res['support_level'] == 'Monitor'
    assert res['persistence_applied'] is True

def test_what_if_custom_thresholds(engine):
    features = {'student_id': 'S-TEST-TH', 'as_of_week': 10, 'att_mean_recent': 72.0, 'att_drop_from_baseline': 0.0, 'low_att_streak': 0, 'att_insufficient': False, 'missing_count_recent': 0, 'missing_streak': 0, 'late_rate_recent': 0.0, 'submission_rate_overall': 1.0, 'assign_insufficient': False, 'quiz_mean_recent': 80.0, 'quiz_trend': 0.0, 'quiz_below_threshold_count': 0, 'quiz_participation_rate': 1.0, 'quiz_insufficient': False, 'data_confidence_level': 'High', 'data_confidence_score': 1.0}
    res_default = engine.evaluate_student(features)
    assert any((r['id'] == 'A1' for r in res_default['fired_rules']))
    custom_th = {'attendance': {'low_att_cutoff': 70.0}}
    res_custom = engine.evaluate_student(features, custom_thresholds=custom_th)
    assert not any((r['id'] == 'A1' for r in res_custom['fired_rules']))
