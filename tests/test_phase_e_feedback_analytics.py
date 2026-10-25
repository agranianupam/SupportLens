import pytest
from pathlib import Path
from src.review_store import ReviewStore


def test_review_analytics_empty(tmp_path):
    test_db = tmp_path / "test_reviews_empty.db"
    store = ReviewStore(db_path=test_db)
    analytics = store.get_review_analytics()
    assert analytics["total_reviews"] == 0
    assert analytics["per_rule_analytics"] == []
    assert analytics["suggested_rule_reviews"] == []
    assert analytics["data_quality_notice"] is None


def test_review_analytics_with_dismissals_and_threshold_suggestion(tmp_path):
    test_db = tmp_path / "test_reviews_dismissals.db"
    store = ReviewStore(db_path=test_db)
    
    # Log 10 flags with fired rules
    for i in range(10):
        sid = f"S-{i:04d}"
        flag_data = {
            "student_id": sid,
            "as_of_week": 10,
            "support_level": "Suggest Outreach",
            "score": 5,
            "categories": ["Attendance"],
            "explanation": {"summary": "test"},
            "fired_rules": ["A1", "A3"],
        }
        fid = store.save_flag(flag_data)
        
        # Dismiss 4 of them due to 'Data error' for rule A1, 6 confirmed
        if i < 4:
            store.record_review(
                flag_id=fid,
                student_id=sid,
                reviewer_code="STAFF-01",
                decision="Dismissed",
                reason_code="Data error",
                reason_note="Attendance sync issue"
            )
        else:
            store.record_review(
                flag_id=fid,
                student_id=sid,
                reviewer_code="STAFF-01",
                decision="Confirmed",
                reason_code=None,
                reason_note=None
            )
    
    analytics = store.get_review_analytics(dismissal_rate_threshold=0.30, min_reviews_threshold=5)
    assert analytics["total_reviews"] == 10
    assert analytics["decision_counts"]["Dismissed"] == 4
    assert analytics["decision_counts"]["Confirmed"] == 6
    assert analytics["decision_pcts"]["Dismissed"] == 40.0
    assert analytics["decision_pcts"]["Confirmed"] == 60.0
    assert analytics["reason_counts"]["Data error"] == 4
    
    # Rule A1 was reviewed 10 times, dismissed 4 times (40% > 30% threshold, >= 5 min reviews)
    assert len(analytics["suggested_rule_reviews"]) > 0
    assert any("Rule A1" in s and "40%" in s for s in analytics["suggested_rule_reviews"])
    
    # Data error notice should be present since 4 >= 3
    assert analytics["data_quality_notice"] is not None
    assert "Data error" in analytics["data_quality_notice"]


def test_cohort_action_effectiveness_empty_and_min_count(tmp_path):
    test_db = tmp_path / "test_actions_eff.db"
    store = ReviewStore(db_path=test_db)
    
    # Test empty state
    eff_empty = store.get_cohort_action_effectiveness()
    assert eff_empty["is_empty"] is True
    assert eff_empty["total_actions"] == 0
    assert eff_empty["breakdown_by_type"] == []
    
    # Create 2 actions with 'Academic check-in' and rate them (less than min 3)
    aid1 = store.record_action(student_id="S-0001", reviewer_code="STAFF-01", action_type="Academic check-in", action_note="Weekly touchpoint")
    aid2 = store.record_action(student_id="S-0002", reviewer_code="STAFF-01", action_type="Academic check-in", action_note="Weekly touchpoint")
    store.update_action_status(aid1, "Done", actor_code="STAFF-01")
    store.update_action_status(aid2, "Done", actor_code="STAFF-01")
    store.record_action_feedback(aid1, "Helpful", "Improved study habits")
    store.record_action_feedback(aid2, "Partially helpful", "Attended session")
    
    # Min 3 count rule should hide category breakdown
    eff = store.get_cohort_action_effectiveness(min_ratings_per_type=3)
    assert eff["is_empty"] is False
    assert eff["total_actions"] == 2
    assert eff["completed_count"] == 2
    assert eff["completed_pct"] == 100.0
    assert eff["helpful_count"] == 1
    assert eff["partially_helpful_count"] == 1
    assert eff["breakdown_by_type"] == []  # hidden because count is 2 < 3
    
    # Add a 3rd rating for 'Academic check-in'
    aid3 = store.record_action(student_id="S-0003", reviewer_code="STAFF-01", action_type="Academic check-in", action_note="Weekly touchpoint")
    store.update_action_status(aid3, "Done", actor_code="STAFF-01")
    store.record_action_feedback(aid3, "Helpful", "Great response")
    
    eff3 = store.get_cohort_action_effectiveness(min_ratings_per_type=3)
    assert len(eff3["breakdown_by_type"]) == 1
    b_entry = eff3["breakdown_by_type"][0]
    assert b_entry["Action Type"] == "Academic check-in"
    assert b_entry["Helpful"] == 2
    assert b_entry["Partially helpful"] == 1
    assert b_entry["Total Rated"] == 3
