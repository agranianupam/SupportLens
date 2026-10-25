import pytest
import sqlite3
import glob
import re
from pathlib import Path
from src.review_store import ReviewStore
from src.explain import BANNED_WORDS, ACTION_TEMPLATES, generate_explanation

def test_audit_log_immutable_trigger(tmp_path):
    test_db = tmp_path / "test_immutable_audit.db"
    store = ReviewStore(db_path=test_db)
    
    # Insert an audit log event
    store.log_audit_event(
        actor_code="STAFF-01",
        event_type="TEST_EVENT",
        student_id="S-0001",
        flag_id=1,
        details={"note": "Test append"}
    )
    
    # Open direct raw connection and attempt UPDATE on audit_log
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    with pytest.raises(sqlite3.IntegrityError, match="audit_log is strictly append-only; UPDATE is prohibited"):
        cursor.execute("UPDATE audit_log SET actor_code='HACKED' WHERE student_id='S-0001'")
        
    with pytest.raises(sqlite3.IntegrityError, match="audit_log is strictly append-only; DELETE is prohibited"):
        cursor.execute("DELETE FROM audit_log WHERE student_id='S-0001'")
        
    conn.close()


def test_no_update_or_delete_on_audit_log_in_codebase():
    py_files = glob.glob('src/**/*.py', recursive=True) + glob.glob('app/**/*.py', recursive=True)
    for pfile in py_files:
        with open(pfile, 'r', encoding='utf-8') as f:
            content = f.read().upper()
            assert "UPDATE AUDIT_LOG" not in content, f"Disallowed UPDATE on audit_log in {pfile}"
            assert "DELETE FROM AUDIT_LOG" not in content, f"Disallowed DELETE on audit_log in {pfile}"


def test_no_banned_punitive_words_in_action_templates_and_explanations():
    for cat, actions in ACTION_TEMPLATES.items():
        for act in actions:
            act_lower = act.lower()
            for banned in BANNED_WORDS:
                assert f" {banned} " not in f" {act_lower} ", f"Banned word '{banned}' found in action template: '{act}'"

    # Test generated explanations for multiple levels
    for lvl in ['On Track', 'Monitor', 'Suggest Outreach', 'Priority Check-in', 'Insufficient Data']:
        dummy_flag = {
            'support_level': lvl,
            'categories': ['Attendance Concern', 'Submission Concern'],
            'fired_rules': [{'id': 'A1', 'description': 'Attendance dropped below 75%'}],
            'mitigating_rules': [{'id': 'M1'}],
            'data_confidence': 'High',
        }
        dummy_feat = {'quiz_mean_recent': 82.0, 'submission_rate_overall': 0.90, 'att_mean_recent': 72.0}
        expl = generate_explanation(dummy_flag, dummy_feat)
        for field in ['summary', 'strengths', 'persistence']:
            text = expl.get(field, '').lower()
            for banned in BANNED_WORDS:
                assert f" {banned} " not in f" {text} ", f"Banned word '{banned}' in {field}"


def test_no_real_identifiers_in_data_and_code():
    # Regex for emails and phone numbers
    email_regex = re.compile(r'[a-zA-Z0-9_.+-]+@(?!example\.com)[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
    phone_regex = re.compile(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}')
    
    # Check data files
    data_files = glob.glob('data/*.csv')
    for dfile in data_files:
        with open(dfile, 'r', encoding='utf-8') as f:
            content = f.read()
            # Email check
            emails = email_regex.findall(content)
            assert len(emails) == 0, f"Found real-looking email in {dfile}: {emails}"
            # All student IDs must follow S-XXXX format
            s_ids = re.findall(r'S-\d{4}', content)
            assert len(s_ids) > 0, f"No S-XXXX IDs found in {dfile}"


def test_reviewer_code_anonymization_enforced(tmp_path):
    test_db = tmp_path / "test_staff_anon.db"
    store = ReviewStore(db_path=test_db)
    
    flag_id = store.save_flag({
        'student_id': 'S-0001',
        'as_of_week': 10,
        'support_level': 'Suggest Outreach',
        'score': 6,
        'categories': ['Attendance'],
        'explanation': {'summary': 'test'},
    })
    
    # Valid anonymised code passes
    rev_id = store.record_review(
        flag_id=flag_id,
        student_id='S-0001',
        reviewer_code='STAFF-02',
        decision='Confirmed',
    )
    assert rev_id > 0
    
    # Non-anonymised free-text staff name fails
    with pytest.raises(ValueError, match="must be an anonymised staff identifier"):
        store.record_review(
            flag_id=flag_id,
            student_id='S-0001',
            reviewer_code='Dr. Jane Doe',
            decision='Confirmed',
        )
        
    with pytest.raises(ValueError, match="must be an anonymised staff identifier"):
        store.record_action(
            student_id='S-0001',
            action_type='Academic check-in',
            reviewer_code='Prof. John Smith',
        )
