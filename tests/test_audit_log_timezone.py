import datetime
import io
import pandas as pd
import pytest
from zoneinfo import ZoneInfo
from src.review_store import ReviewStore, format_to_ist, parse_to_ist, KOLKATA_TZ
from src.export import generate_audit_log_csv
from src.fairness import audit_subgroup_fairness
from app.data_loader import load_raw_data, get_cohort_snapshot

def test_students_all_full_time():
    """Verify students roster has only Full-time students and no part-time students."""
    students_df, _, _, _ = load_raw_data()
    assert (students_df['study_mode'] == 'Full-time').all()
    assert 'Part-time' not in students_df['study_mode'].values

def test_timezone_conversion_and_safe_idempotency():
    """Verify UTC, naive, and already-IST timestamps convert to Asia/Kolkata without double conversion."""
    utc_str = "2026-10-25T06:30:00+00:00"
    ist_result = format_to_ist(utc_str)
    # 06:30 UTC + 5:30 = 12:00 IST
    assert "2026-10-25 12:00:00 IST" in ist_result

    # Already IST string with offset
    ist_str = "2026-10-25T12:00:00+05:30"
    assert format_to_ist(ist_str) == "2026-10-25 12:00:00 IST"

    # Already formatted IST string should not shift further
    already_formatted = "2026-10-25 12:00:00 IST"
    assert format_to_ist(already_formatted) == "2026-10-25 12:00:00 IST"

def test_audit_log_chronological_ordering_and_tie_breaking(tmp_path):
    """Verify audit log sorts by true physical timestamp descending, with log_id descending tie-breaker."""
    db_file = tmp_path / "test_audit_order.db"
    store = ReviewStore(db_path=db_file)

    # Insert events with known physical timestamps
    with store._get_connection() as conn:
        cursor = conn.cursor()
        # Older event: 05:00 UTC
        cursor.execute(
            "INSERT INTO audit_log (timestamp, actor_code, event_type, student_id, flag_id, details_json) VALUES (?, ?, ?, ?, ?, ?)",
            ("2026-10-25T05:00:00+00:00", "STAFF-01", "EVENT_OLD", "S-0001", None, "{}")
        )
        # Newer event in UTC: 07:00 UTC (equiv to 12:30 IST)
        cursor.execute(
            "INSERT INTO audit_log (timestamp, actor_code, event_type, student_id, flag_id, details_json) VALUES (?, ?, ?, ?, ?, ?)",
            ("2026-10-25T07:00:00+00:00", "STAFF-01", "EVENT_NEW", "S-0002", None, "{}")
        )
        # Event with identical timestamp: 07:00 UTC, but higher log_id
        cursor.execute(
            "INSERT INTO audit_log (timestamp, actor_code, event_type, student_id, flag_id, details_json) VALUES (?, ?, ?, ?, ?, ?)",
            ("2026-10-25T07:00:00+00:00", "STAFF-01", "EVENT_TIE_BREAKER", "S-0003", None, "{}")
        )
        conn.commit()

    logs = store.get_audit_log(limit=10)
    assert len(logs) == 3
    # Newest events should be first
    assert logs[0]['event_type'] == "EVENT_TIE_BREAKER"
    assert logs[1]['event_type'] == "EVENT_NEW"
    assert logs[2]['event_type'] == "EVENT_OLD"

def test_audit_log_csv_export():
    """Verify audit log CSV export labels timezone and formats timestamps in IST."""
    sample_logs = [
        {
            'log_id': 1,
            'timestamp': '2026-10-25T06:30:00+00:00',
            'actor_code': 'STAFF-01',
            'event_type': 'FLAG_EVALUATED',
            'student_id': 'S-0010',
            'flag_id': 1,
            'details_json': '{"decision": "Confirmed"}'
        }
    ]
    csv_str = generate_audit_log_csv(sample_logs)
    df = pd.read_csv(io.StringIO(csv_str))
    assert 'log_id' in df.columns
    assert 'timestamp' in df.columns
    assert 'timezone' in df.columns
    assert df['timezone'].iloc[0] == 'IST (Asia/Kolkata)'
    assert df['timestamp'].iloc[0] == '2026-10-25 12:00:00 IST'

def test_subgroup_fairness_on_sections_and_prior_support():
    """Verify fairness auditing works seamlessly across cohort_group and prior_support_flag."""
    features_df, cohort_records = get_cohort_snapshot(10)
    students_df, _, ground_truth, _ = load_raw_data()

    res_section = audit_subgroup_fairness(features_df, students_df, ground_truth, cohort_records, attribute_col='cohort_group')
    assert 'demographic_parity_gap_pct' in res_section
    assert set(res_section['subgroups'].keys()) == {'Section A', 'Section B', 'Section C'}

    res_prior = audit_subgroup_fairness(features_df, students_df, ground_truth, cohort_records, attribute_col='prior_support_flag')
    assert 'demographic_parity_gap_pct' in res_prior
