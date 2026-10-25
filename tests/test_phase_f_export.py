import pytest
import io
import re
import pandas as pd
from src.export import (
    generate_weekly_summary_csv,
    generate_audit_log_csv,
    generate_review_analytics_csv,
    generate_weekly_support_summary_pdf,
    BANNED_WORDS,
)
from src.review_store import ReviewStore

PROHIBITED_COLUMNS = {'cohort_group', 'study_mode', 'prior_support_flag', 'staff_note', 'action_note', 'reason_note'}

def test_weekly_summary_csv_spec():
    sample_records = [
        {
            'student_id': 'S-0001',
            'as_of_week': 10,
            'support_level': 'Suggest Outreach',
            'display_level': 'Suggest Outreach',
            'score': 6,
            'categories': ['Attendance', 'Submission'],
            'data_confidence': 'High',
            'review_decision': 'Confirmed by Staff',
            'planned_action_status': 'Planned',
            # Hidden metadata that must NOT leak into CSV
            'cohort_group': 'Group A',
            'study_mode': 'Full-time',
            'prior_support_flag': 0,
            'staff_note': 'Secret staff comment',
        },
        {
            'student_id': 'S-0002',
            'as_of_week': 10,
            'support_level': 'On Track',
            'display_level': 'On Track',
            'score': 1,
            'categories': [],
            'data_confidence': 'Medium',
            'review_decision': 'Pending Review',
            'planned_action_status': 'None',
        }
    ]
    csv_str = generate_weekly_summary_csv(sample_records)
    df = pd.read_csv(io.StringIO(csv_str))
    
    expected_cols = [
        'student_id', 'as_of_week', 'support_level', 'categories',
        'score', 'data_confidence', 'review_status', 'planned_action_status'
    ]
    assert list(df.columns) == expected_cols
    
    # Check no prohibited group attributes or staff notes leaked
    for col in df.columns:
        assert col not in PROHIBITED_COLUMNS
        
    # Check no banned punitive words
    csv_lower = csv_str.lower()
    for word in BANNED_WORDS:
        assert word not in csv_lower


def test_audit_log_csv_and_analytics_csv():
    sample_logs = [
        {
            'log_id': 1,
            'timestamp': '2026-10-25T08:00:00Z',
            'actor_code': 'STAFF-01',
            'event_type': 'REVIEW_CONFIRMED',
            'student_id': 'S-0010',
            'flag_id': 101,
            'details_json': '{"decision": "Confirmed"}'
        }
    ]
    audit_csv = generate_audit_log_csv(sample_logs)
    audit_df = pd.read_csv(io.StringIO(audit_csv))
    assert 'log_id' in audit_df.columns
    assert 'actor_code' in audit_df.columns
    assert 'details' in audit_df.columns
    
    analytics_dict = {
        'total_reviews': 5,
        'decision_counts': {'Confirmed': 3, 'Dismissed': 2},
        'decision_pcts': {'Confirmed': 60.0, 'Dismissed': 40.0},
        'reason_counts': {'Data error': 2},
        'per_rule_analytics': [
            {'Rule ID': 'A1', 'Total Reviews': 5, 'Dismissals': 2, 'Dismissal Rate (%)': 40.0}
        ]
    }
    analytics_csv = generate_review_analytics_csv(analytics_dict)
    analytics_df = pd.read_csv(io.StringIO(analytics_csv))
    assert len(analytics_df) >= 3
    assert 'category' in analytics_df.columns
    assert 'metric' in analytics_df.columns


def test_weekly_support_summary_pdf_generation():
    kpis = {
        'total_students': 100,
        'on_track_count': 70,
        'on_track_pct': 70.0,
        'monitor_count': 18,
        'monitor_pct': 18.0,
        'suggest_outreach_count': 8,
        'suggest_outreach_pct': 8.0,
        'priority_checkin_count': 4,
        'priority_checkin_pct': 4.0,
        'insufficient_data_count': 2,
    }
    cohort_records = [
        {
            'student_id': f'S-{i:04d}',
            'display_level': 'Priority Check-in' if i < 4 else ('Suggest Outreach' if i < 12 else 'On Track'),
            'score': 8 if i < 4 else (5 if i < 12 else 1),
            'categories': ['Attendance Concern'] if i < 12 else [],
            'data_confidence': 'High',
            'explanation': {'summary': 'Persistent low attendance over recent snapshots'},
        }
        for i in range(1, 101)
    ]
    pdf_bytes = generate_weekly_support_summary_pdf(
        as_of_week=10,
        kpis=kpis,
        cohort_records=cohort_records,
        review_analytics={'total_reviews': 10, 'decision_pcts': {'Confirmed': 80.0, 'Dismissed': 20.0}},
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b'%PDF-')
    
    # PDF text inspection
    pdf_text = pdf_bytes.decode('latin-1', errors='ignore')
    assert 'Synthetic data. Supports staff; does not make academic decisions.' in pdf_text
    assert 'ETHICAL GUARDRAILS & NON-PUNITIVE PURPOSE' in pdf_text
    for word in BANNED_WORDS:
        assert f' {word} ' not in pdf_text.lower()


def test_export_recorded_in_audit_log(tmp_path):
    test_db = tmp_path / "test_export_audit.db"
    store = ReviewStore(db_path=test_db)
    
    store.record_export(file_type='WEEKLY_SUMMARY_CSV', actor_code='STAFF-02', details={'count': 100})
    logs = store.get_audit_log()
    assert len(logs) == 1
    assert logs[0]['event_type'] == 'EXPORT'
    assert logs[0]['actor_code'] == 'STAFF-02'
    assert 'WEEKLY_SUMMARY_CSV' in logs[0]['details_json']
