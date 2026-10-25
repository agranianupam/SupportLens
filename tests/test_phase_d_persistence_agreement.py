import pytest
import numpy as np
from src.rules_engine import RulesEngine
from src.ml_model import compute_agreement


def test_persistence_single_week_dip_capped_at_monitor():
    engine = RulesEngine()
    features = {
        'student_id': 'S-SINGLE-DIP',
        'as_of_week': 10,
        'att_mean_recent': 55.0,
        'att_drop_from_baseline': 8.0,
        'low_att_streak': 1,
        'att_insufficient': False,
        'missing_count_recent': 2,
        'missing_streak': 1,
        'late_rate_recent': 0.0,
        'submission_rate_overall': 0.8,
        'assign_insufficient': False,
        'quiz_mean_recent': 70.0,
        'quiz_trend': 0.0,
        'quiz_below_threshold_count': 0,
        'quiz_participation_rate': 1.0,
        'quiz_insufficient': False,
        'data_confidence_level': 'High',
        'data_confidence_score': 0.95,
    }
    # Prior two snapshots had low concern scores [1, 2]
    res = engine.evaluate_student(features, historical_scores=[1, 2])
    assert res['persistence_applied'] is True
    assert res['support_level'] == 'Monitor'
    assert 'Watching: single-week signal' in res['persistence_note']


def test_persistence_two_of_three_weeks_escalates():
    engine = RulesEngine()
    features = {
        'student_id': 'S-PERSISTENT-NEED',
        'as_of_week': 10,
        'att_mean_recent': 58.0,
        'att_drop_from_baseline': 12.0,
        'low_att_streak': 3,
        'att_insufficient': False,
        'missing_count_recent': 2,
        'missing_streak': 2,
        'late_rate_recent': 0.0,
        'submission_rate_overall': 0.6,
        'assign_insufficient': False,
        'quiz_mean_recent': 45.0,
        'quiz_trend': -2.0,
        'quiz_below_threshold_count': 2,
        'quiz_participation_rate': 0.8,
        'quiz_insufficient': False,
        'data_confidence_level': 'High',
        'data_confidence_score': 0.95,
    }
    # Prior snapshots had high concern: [6, 7]
    res = engine.evaluate_student(features, historical_scores=[6, 7])
    assert res['persistence_applied'] is False
    assert res['support_level'] in ['Suggest Outreach', 'Priority Check-in']
    assert 'Concern confirmed' in res['persistence_note']


def test_persistence_c2_sudden_change_bypasses():
    engine = RulesEngine()
    features = {
        'student_id': 'S-SUDDEN-C2',
        'as_of_week': 8,
        'att_mean_recent': 55.0,
        'att_drop_from_baseline': 28.0,  # >= sudden_drop_cutoff (25.0)
        'low_att_streak': 1,
        'att_insufficient': False,
        'missing_count_recent': 2,       # >= 2 missing
        'missing_streak': 1,
        'late_rate_recent': 0.0,
        'submission_rate_overall': 0.7,
        'assign_insufficient': False,
        'quiz_mean_recent': 65.0,
        'quiz_trend': 0.0,
        'quiz_below_threshold_count': 0,
        'quiz_participation_rate': 1.0,
        'quiz_insufficient': False,
        'data_confidence_level': 'High',
        'data_confidence_score': 0.95,
    }
    # Prior snapshots were completely on track [0, 0]
    res = engine.evaluate_student(features, historical_scores=[0, 0])
    # Sudden change C2 must fire and bypass persistence
    assert any(r['id'] == 'C2' for r in res['fired_rules'])
    assert res['persistence_applied'] is False
    assert res['support_level'] in ['Suggest Outreach', 'Priority Check-in']


def test_agreement_categories():
    # Both indicate support
    ag1 = compute_agreement('Suggest Outreach', ml_flag_or_prob=0.85)
    assert ag1['badge'] == 'Both indicate support may help'
    assert ag1['type'] == 'both_support'

    # Rules only
    ag2 = compute_agreement('Priority Check-in', ml_flag_or_prob=0.25)
    assert ag2['badge'] == 'Rules only: review for possible false positive'
    assert ag2['type'] == 'rules_only'

    # ML only
    ag3 = compute_agreement('On Track', ml_flag_or_prob=0.75)
    assert ag3['badge'] == 'ML only: review for possible missed signal'
    assert ag3['type'] == 'ml_only'

    # Both on track
    ag4 = compute_agreement('Monitor', ml_flag_or_prob=0.15)
    assert ag4['badge'] == 'Both on track'
    assert ag4['type'] == 'both_ontrack'
