import pytest
from pathlib import Path
from src.review_store import ReviewStore

@pytest.fixture
def store(tmp_path):
    test_db = tmp_path / 'test_supportlens.db'
    return ReviewStore(db_path=test_db)

def test_save_flag_and_persistence(store):
    flag_data = {'student_id': 'S-0042', 'as_of_week': 8, 'support_level': 'Suggest Outreach', 'score': 6, 'categories': ['Attendance Concern', 'Submission Concern'], 'explanation': {'summary': 'Attendance dropped recently'}}
    flag_id = store.save_flag(flag_data)
    assert flag_id > 0
    logs = store.get_audit_log(student_id='S-0042')
    assert len(logs) >= 1
    assert logs[0]['event_type'] == 'FLAG_EVALUATED'

def test_confirm_review_flow(store):
    flag_data = {'student_id': 'S-0010', 'as_of_week': 6, 'support_level': 'Priority Check-in', 'score': 8, 'categories': ['Attendance Concern']}
    flag_id = store.save_flag(flag_data)
    rev_id = store.record_review(flag_id=flag_id, student_id='S-0010', reviewer_code='STAFF-01', decision='Confirmed')
    assert rev_id > 0
    status = store.get_effective_student_status('S-0010', 'Priority Check-in', as_of_week=6)
    assert status['is_reviewed'] is True
    assert status['review_decision'] == 'Confirmed by Staff'
    assert status['display_level'] == 'Priority Check-in'

def test_correction_requires_reason(store):
    flag_data = {'student_id': 'S-0020', 'as_of_week': 6, 'support_level': 'Priority Check-in', 'score': 8, 'categories': ['Attendance Concern']}
    flag_id = store.save_flag(flag_data)
    with pytest.raises(ValueError, match='Both a reason code and an explanation note'):
        store.record_review(flag_id=flag_id, student_id='S-0020', reviewer_code='STAFF-02', decision='Corrected', corrected_level='Monitor', reason_code='', reason_note='')
    rev_id = store.record_review(flag_id=flag_id, student_id='S-0020', reviewer_code='STAFF-02', decision='Corrected', corrected_level='Monitor', reason_code='Known circumstance', reason_note='Student had approved medical leave during week 5.')
    assert rev_id > 0
    status = store.get_effective_student_status('S-0020', 'Priority Check-in', as_of_week=6)
    assert status['override_applied'] is True
    assert status['display_level'] == 'Monitor'

def test_dismiss_false_positive_flow(store):
    flag_data = {'student_id': 'S-0030', 'as_of_week': 8, 'support_level': 'Suggest Outreach', 'score': 5, 'categories': ['Attendance Concern']}
    flag_id = store.save_flag(flag_data)
    store.record_review(flag_id=flag_id, student_id='S-0030', reviewer_code='STAFF-01', decision='Dismissed', reason_code='Strong performance elsewhere', reason_note='Exemplary quiz scores; working full time job.')
    status = store.get_effective_student_status('S-0030', 'Suggest Outreach', as_of_week=8)
    assert status['display_level'] == 'On Track'
    assert 'Dismissed' in status['review_decision']

def test_record_action_flow(store):
    action_id = store.record_action(student_id='S-0040', action_type='Friendly check-in email about course pacing', reviewer_code='STAFF-03', action_note='Sent gentle invitation to discuss week 6 lecture concepts.', planned_date='2026-11-01', status='Planned')
    assert action_id > 0
    store.update_action_status(action_id, 'Done', actor_code='STAFF-03')
    hist = store.get_student_history('S-0040')
    assert len(hist['actions']) == 1
    assert hist['actions'][0]['status'] == 'Done'
