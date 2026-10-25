import pytest
import pandas as pd
import numpy as np
from app.data_loader import get_cohort_snapshot
from src.archetypes import select_dynamic_archetypes


def test_archetypes_return_structure_and_distinctness():
    """Verify select_dynamic_archetypes returns expected keys and distinct student IDs."""
    for w in range(4, 13):
        f_df, records = get_cohort_snapshot(w)
        results = select_dynamic_archetypes(w, f_df, records)

        expected_keys = {'decliner', 'strong_irregular', 'data_gap', 'recovering'}
        assert set(results.keys()) == expected_keys

        matched_ids = [v['student_id'] for v in results.values() if v is not None]
        # Ensure no student is duplicated across cards in the same week
        assert len(matched_ids) == len(set(matched_ids)), f"Duplicate student in week {w}: {matched_ids}"


def test_archetypes_zero_lookahead():
    """Ensure dynamic selection at earlier weeks never relies on future data."""
    f_w4, recs_w4 = get_cohort_snapshot(4)
    res_w4 = select_dynamic_archetypes(4, f_w4, recs_w4)

    f_w10, recs_w10 = get_cohort_snapshot(10)
    res_w10 = select_dynamic_archetypes(10, f_w10, recs_w10)

    # Week 4 candidates must be computed strictly from week 4 features
    assert res_w4['data_gap']['badge'] == "Best match for Week 4"
    assert res_w10['data_gap']['badge'] == "Best match for Week 10"


def test_archetypes_deterministic_ranking():
    """Ensure repeatedly running selection on the same week yields identical results."""
    f_df, records = get_cohort_snapshot(8)
    res1 = select_dynamic_archetypes(8, f_df, records)
    res2 = select_dynamic_archetypes(8, f_df, records)

    for k in ['decliner', 'strong_irregular', 'data_gap', 'recovering']:
        if res1[k] is not None:
            assert res1[k]['student_id'] == res2[k]['student_id']
            assert res1[k]['description'] == res2[k]['description']


def test_archetypes_graceful_no_match():
    """Verify graceful handling when features DataFrame is empty or contains no qualifiers."""
    empty_df = pd.DataFrame(columns=['student_id', 'att_trend', 'quiz_trend', 'data_confidence_score'])
    res = select_dynamic_archetypes(6, empty_df, [])
    assert res['decliner'] is None
    assert res['strong_irregular'] is None
    assert res['data_gap'] is None
    assert res['recovering'] is None


def test_home_page_intro_paragraph_removed():
    """Verify that the long SupportLens intro paragraph is removed from Home.py while title/subtitle remain."""
    with open('app/Home.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Title and subtitle must be present
    assert "st.title('🎓 SupportLens')" in content
    assert "st.subheader('Transparent, Human-in-the-Loop Early-Warning Academic Support Dashboard')" in content

    # Long introductory paragraph must NOT be present
    assert "SupportLens enables university course coordinators to identify students who may benefit from proactive" not in content


def test_simplified_card_descriptions():
    """Verify that card descriptions use friendly, plain-English wording without jargon."""
    f_df, records = get_cohort_snapshot(10)
    res = select_dynamic_archetypes(10, f_df, records)

    # Decliner text check
    assert "Attendance and quiz scores have been falling over several weeks" in res['decliner']['description']
    # Strong-but-irregular text check
    assert "The student does well in quizzes but has irregular attendance" in res['strong_irregular']['description']
    # Data gap text check
    assert "Some student records are missing" in res['data_gap']['description']
    # Recovering text check
    assert "The student is showing signs of improvement after earlier difficulties" in res['recovering']['description']

    # Ensure no technical jargon in card descriptions
    for k, v in res.items():
        if v is not None:
            desc = v['description']
            assert "persistence rule" not in desc.lower()
            assert "rule m1" not in desc.lower()
            assert "cross-domain signals" not in desc.lower()
