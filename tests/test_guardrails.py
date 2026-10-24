import pytest
from src.explain import BANNED_WORDS, verify_text_safety, generate_explanation, ACTION_TEMPLATES
from src.ml_model import PROHIBITED_COLUMNS, FEATURE_COLUMNS
from src.review_store import PROHIBITED_DECISIONS, VALID_DECISIONS

def test_banned_words_detection():
    safe_text = 'This student may benefit from supportive academic follow-up.'
    verify_text_safety(safe_text)
    punitive_samples = ['This failing student should receive a penalty.', 'The student is lazy and at fault.', 'Recommend disciplinary probation.']
    for text in punitive_samples:
        with pytest.raises(ValueError, match='CRITICAL GUARDRAIL VIOLATION'):
            verify_text_safety(text)

def test_no_group_attributes_in_ml_features():
    prohibited_group_attrs = {'cohort_group', 'study_mode', 'prior_support_flag'}
    for attr in prohibited_group_attrs:
        assert attr not in FEATURE_COLUMNS
        assert attr in PROHIBITED_COLUMNS

def test_action_templates_are_purely_supportive():
    for category, actions in ACTION_TEMPLATES.items():
        for act in actions:
            verify_text_safety(act)
            assert not any((p in act.lower() for p in ['punish', 'penal', 'fail', 'drop', 'misconduct']))

def test_review_store_prohibits_punitive_decisions():
    for prohibited in PROHIBITED_DECISIONS:
        assert prohibited not in VALID_DECISIONS

def test_explanation_generation_guardrails():
    test_cases = [{'support_level': 'On Track', 'categories': [], 'fired_rules': [], 'mitigating_rules': []}, {'support_level': 'Monitor', 'categories': ['Attendance Concern'], 'fired_rules': [{'description': 'Attendance below 75%'}], 'mitigating_rules': []}, {'support_level': 'Suggest Outreach', 'categories': ['Attendance Concern', 'Submission Concern'], 'fired_rules': [{'description': 'Attendance below 75%'}], 'mitigating_rules': []}, {'support_level': 'Priority Check-in', 'categories': ['Engagement Drop (Compound)'], 'fired_rules': [{'description': 'Attendance dropped 25 pts'}], 'mitigating_rules': []}, {'support_level': 'Insufficient Data', 'categories': ['Insufficient Data'], 'fired_rules': [], 'mitigating_rules': []}]
    for tc in test_cases:
        res = generate_explanation(tc)
        assert len(res['summary']) > 0
        assert len(res['strengths']) > 0
        assert isinstance(res['suggested_actions'], list)
