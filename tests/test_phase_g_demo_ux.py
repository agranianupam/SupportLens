import pytest
import glob
import os
import pandas as pd
from pathlib import Path
from src.review_store import ReviewStore
from app.components.badges import support_level_badge, confidence_badge, agreement_badge, review_status_badge

def test_reset_demo_data_preserves_append_only_audit_log(tmp_path):
    test_db = tmp_path / "test_demo_reset.db"
    store = ReviewStore(db_path=test_db)
    
    # Add flag, review, action, feedback
    flag_data = {
        'student_id': 'S-0084',
        'as_of_week': 10,
        'support_level': 'Suggest Outreach',
        'score': 6,
        'categories': ['Attendance'],
        'explanation': {'summary': 'test'},
    }
    fid = store.save_flag(flag_data)
    store.record_review(
        flag_id=fid,
        student_id='S-0084',
        reviewer_code='STAFF-01',
        decision='Confirmed',
    )
    aid = store.record_action(
        student_id='S-0084',
        reviewer_code='STAFF-01',
        action_type='Study skills consultation',
    )
    store.update_action_status(aid, 'Done', actor_code='STAFF-01')
    store.record_action_feedback(aid, 'Helpful', 'Good student engagement')
    
    # Verify records exist before reset
    hist = store.get_student_history('S-0084')
    assert len(hist['reviews']) == 1
    assert len(hist['actions']) == 1
    
    # Execute demo reset
    store.reset_demo_data(actor_code='STAFF-DEMO')
    
    # Confirm reviews and actions are cleared
    hist_after = store.get_student_history('S-0084')
    assert len(hist_after['reviews']) == 0
    assert len(hist_after['actions']) == 0
    
    # Confirm audit log is NOT deleted, and contains DEMO_RESET event
    logs = store.get_audit_log()
    assert len(logs) >= 2  # flag creation + review + action + reset
    reset_events = [l for l in logs if l['event_type'] == 'DEMO_RESET']
    assert len(reset_events) == 1
    assert reset_events[0]['actor_code'] == 'STAFF-DEMO'


def test_badges_dual_encoding():
    # Support level badge must contain both icon and text label
    for lvl in ['On Track', 'Monitor', 'Suggest Outreach', 'Priority Check-in', 'Insufficient Data']:
        b = support_level_badge(lvl)
        assert lvl in b
        # Check icon presence
        assert any(icon in b for icon in ['🟢', '🟡', '🟠', '🔴', '⚪'])

    # Confidence badge must contain icon and text
    for conf in ['High', 'Medium', 'Low']:
        b = confidence_badge(conf, 0.85)
        assert conf in b
        assert any(icon in b for icon in ['📶', '📳', '⚠️'])

    # Agreement badge must contain icon and text
    b_ag = agreement_badge({'type': 'both_support', 'icon': '🤝', 'badge': 'Both indicate support may help'})
    assert '🤝' in b_ag
    assert 'Both indicate support may help' in b_ag


def test_guardrails_banner_on_all_pages():
    page_files = glob.glob('app/pages/*.py') + ['app/Home.py']
    assert len(page_files) >= 8  # Home + 7 pages
    for pfile in page_files:
        with open(pfile, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'render_guardrails_banner()' in content, f"Page {pfile} is missing render_guardrails_banner()"


def test_demo_archetype_students_exist():
    students_df = pd.read_csv('data/students.csv')
    gt_df = pd.read_csv('data/ground_truth_support_need.csv')
    
    # Check that S-0084, S-0031, S-0063, S-0023 are in the roster
    for sid in ['S-0084', 'S-0031', 'S-0063', 'S-0023']:
        assert sid in students_df['student_id'].values
        assert sid in gt_df['student_id'].values
        
    # Check archetype mappings
    gt_map = gt_df.set_index('student_id')['archetype'].to_dict()
    assert gt_map['S-0084'] == 'gradual_decliner'
    assert gt_map['S-0031'] == 'strong_irregular'
    assert gt_map['S-0023'] == 'recovering'
