"""
Dynamic archetype selection engine for SupportLens demo cards.
Ensures zero-lookahead bias by operating strictly on features and snapshot data
as of the selected historical week.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


def select_dynamic_archetypes(
    as_of_week: int,
    features_df: pd.DataFrame,
    cohort_records: list
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Selects the best distinct matching student for each of the four key archetypes:
      1. Gradual Decliner
      2. Strong-but-Irregular
      3. Data-Gap Case
      4. Recovering Student

    Deterministic ranking is used.
    If no student qualifies for an archetype, returns None for that archetype.
    """
    rec_by_id = {r['student_id']: r for r in cohort_records}

    # 1. DATA-GAP CASE CANDIDATES
    # Criteria: Significant missing data or low data confidence.
    dg_candidates = []
    for _, row in features_df.iterrows():
        sid = row['student_id']
        rec = rec_by_id.get(sid, {})
        conf = row.get('data_confidence_score', 1.0)
        is_insuff = (
            rec.get('display_level') == 'Insufficient Data'
            or rec.get('support_level') == 'Insufficient Data'
            or row.get('data_confidence_level') == 'Low'
            or row.get('insufficient_data', False)
        )
        att_miss = row.get('att_missing_rate', 0.0)
        quiz_miss = row.get('quiz_missing_rate', 0.0)
        assign_unknown = row.get('assignment_unknown_rate', 0.0)
        total_miss_rate = (att_miss + quiz_miss + assign_unknown)

        if is_insuff or conf <= 0.80 or total_miss_rate >= 0.20:
            score = (
                (150.0 if is_insuff else 0.0)
                + (1.0 - conf) * 100.0
                + total_miss_rate * 50.0
            )
            dg_candidates.append({
                'student_id': sid,
                'score': score,
                'confidence': conf,
                'is_insuff': is_insuff,
            })
    dg_candidates.sort(key=lambda x: (x['score'], x['student_id']), reverse=True)

    # 2. RECOVERING STUDENT CANDIDATES
    # Criteria: Earlier academic difficulty followed by recent measurable improvement.
    rec_candidates = []
    for _, row in features_df.iterrows():
        sid = row['student_id']
        rec = rec_by_id.get(sid, {})
        has_m2 = any(r.get('id') == 'M2' for r in rec.get('mitigating_rules', []))
        
        at = row['att_trend'] if not np.isnan(row.get('att_trend', np.nan)) else 0.0
        qt = row['quiz_trend'] if not np.isnan(row.get('quiz_trend', np.nan)) else 0.0
        a_overall = row.get('att_mean_overall', 100.0)
        if a_overall is None or np.isnan(a_overall):
            a_overall = 100.0
        a_recent = row.get('att_mean_recent', 0.0)
        if a_recent is None or np.isnan(a_recent):
            a_recent = 0.0
        q_overall = row.get('quiz_mean_overall', 100.0)
        if q_overall is None or np.isnan(q_overall):
            q_overall = 100.0

        # Evidence of earlier difficulty: lower historical attendance or quiz, or notable recent recovery jump
        had_earlier_diff = (
            a_overall < 80.0
            or q_overall < 70.0
            or (a_recent > a_overall + 2.0)
            or any(r.get('id') in ['A1', 'A2', 'A3', 'A4', 'Q1'] for r in rec.get('fired_rules', []))
        )
        has_measurable_gain = (at >= 1.0 or qt >= 1.0 or (a_recent >= a_overall + 3.0))

        if has_m2 or (had_earlier_diff and has_measurable_gain):
            m2_bonus = 150.0 if has_m2 else 0.0
            trend_val = max(0.0, at) * 4.0 + max(0.0, qt) * 4.0
            jump_val = max(0.0, a_recent - a_overall) * 2.0
            score = m2_bonus + trend_val + jump_val
            rec_candidates.append({
                'student_id': sid,
                'score': score,
                'att_trend': at,
                'quiz_trend': qt,
                'has_m2': has_m2,
            })
    rec_candidates.sort(key=lambda x: (x['score'], x['student_id']), reverse=True)

    # 3. STRONG-BUT-IRREGULAR CANDIDATES
    # Criteria: Strong quiz performance but irregular/low attendance or engagement.
    si_candidates = []
    for _, row in features_df.iterrows():
        sid = row['student_id']
        rec = rec_by_id.get(sid, {})
        has_m1 = any(r.get('id') == 'M1' for r in rec.get('mitigating_rules', []))
        
        q_recent = row.get('quiz_mean_recent', 0.0)
        if q_recent is None or np.isnan(q_recent):
            q_recent = 0.0
        q_overall = row.get('quiz_mean_overall', 0.0)
        if q_overall is None or np.isnan(q_overall):
            q_overall = 0.0
        quiz_mastery = max(q_recent, q_overall)

        a_recent = row.get('att_mean_recent', 100.0)
        if a_recent is None or np.isnan(a_recent):
            a_recent = 100.0
        a_overall = row.get('att_mean_overall', 100.0)
        if a_overall is None or np.isnan(a_overall):
            a_overall = 100.0

        miss_recent = row.get('missing_count_recent', 0)
        has_att_concern = (
            a_recent < 75.0
            or a_overall < 75.0
            or any(r.get('id') in ['A1', 'A2', 'A3', 'A4'] for r in rec.get('fired_rules', []))
        )

        if has_m1 or (quiz_mastery >= 75.0 and has_att_concern and miss_recent <= 1):
            m1_bonus = 150.0 if has_m1 else 0.0
            gap = max(0.0, 75.0 - a_recent)
            score = m1_bonus + quiz_mastery + gap * 1.5
            si_candidates.append({
                'student_id': sid,
                'score': score,
                'quiz_mastery': quiz_mastery,
                'att_recent': a_recent,
                'has_m1': has_m1,
            })
    si_candidates.sort(key=lambda x: (x['score'], x['student_id']), reverse=True)

    # 4. GRADUAL DECLINER CANDIDATES
    # Criteria: Strongest sustained decline in attendance and/or quiz performance over several weeks.
    decl_candidates = []
    for _, row in features_df.iterrows():
        sid = row['student_id']
        rec = rec_by_id.get(sid, {})
        
        at = row['att_trend'] if not np.isnan(row.get('att_trend', np.nan)) else 0.0
        qt = row['quiz_trend'] if not np.isnan(row.get('quiz_trend', np.nan)) else 0.0
        streak = row.get('low_att_streak', 0)
        drop = row.get('att_drop_from_baseline', 0.0)
        if drop is None or np.isnan(drop):
            drop = 0.0

        # Check for genuine sustained downward trend
        is_declining = (
            at <= -1.0
            or qt <= -1.0
            or (at < 0 and qt < 0)
            or (drop >= 12.0 and at < 0)
        )

        if is_declining:
            both_neg = 50.0 if (at < -0.5 and qt < -0.5) else 0.0
            slope_magnitude = - (min(0.0, at) + min(0.0, qt))
            score = both_neg + slope_magnitude * 3.0 + drop * 0.5 + streak * 2.0
            decl_candidates.append({
                'student_id': sid,
                'score': score,
                'att_trend': at,
                'quiz_trend': qt,
                'drop': drop,
            })
    decl_candidates.sort(key=lambda x: (x['score'], x['student_id']), reverse=True)

    # Deterministically select distinct students across all 4 archetypes
    chosen = set()
    result = {}

    # 1. Data-Gap Case
    dg_match = next((c for c in dg_candidates if c['student_id'] not in chosen), None)
    if dg_match:
        chosen.add(dg_match['student_id'])
        result['data_gap'] = {
            'student_id': dg_match['student_id'],
            'title': 'Data-Gap Case',
            'description': 'Some student records are missing. SupportLens avoids making assumptions and recommends checking the data first.',
            'badge': f'Best match for Week {as_of_week}',
            'inspect_label': f"🔎 Inspect {dg_match['student_id']}",
        }
    else:
        result['data_gap'] = None

    # 2. Recovering Student
    rec_match = next((c for c in rec_candidates if c['student_id'] not in chosen), None)
    if rec_match:
        chosen.add(rec_match['student_id'])
        result['recovering'] = {
            'student_id': rec_match['student_id'],
            'title': 'Recovering Student',
            'description': 'The student is showing signs of improvement after earlier difficulties. SupportLens takes this positive progress into account.',
            'badge': f'Best match for Week {as_of_week}',
            'inspect_label': f"🔎 Inspect {rec_match['student_id']}",
        }
    else:
        result['recovering'] = None

    # 3. Strong-but-Irregular
    si_match = next((c for c in si_candidates if c['student_id'] not in chosen), None)
    if si_match:
        chosen.add(si_match['student_id'])
        result['strong_irregular'] = {
            'student_id': si_match['student_id'],
            'title': 'Strong-but-Irregular',
            'description': 'The student does well in quizzes but has irregular attendance or engagement. Strong performance helps prevent unnecessary alerts.',
            'badge': f'Best match for Week {as_of_week}',
            'inspect_label': f"🔎 Inspect {si_match['student_id']}",
        }
    else:
        result['strong_irregular'] = None

    # 4. Gradual Decliner
    decl_match = next((c for c in decl_candidates if c['student_id'] not in chosen), None)
    if decl_match:
        chosen.add(decl_match['student_id'])
        result['decliner'] = {
            'student_id': decl_match['student_id'],
            'title': 'Gradual Decliner',
            'description': 'Attendance and quiz scores have been falling over several weeks. SupportLens suggests checking in to see if the student needs help.',
            'badge': f'Best match for Week {as_of_week}',
            'inspect_label': f"🔎 Inspect {decl_match['student_id']}",
        }
    else:
        result['decliner'] = None

    return result
