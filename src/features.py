from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

def compute_linear_trend(values: List[float]) -> float:
    valid = [(i, val) for i, val in enumerate(values) if val is not None and (not np.isnan(val))]
    if len(valid) < 2:
        return 0.0
    x = np.array([pt[0] for pt in valid], dtype=float)
    y = np.array([pt[1] for pt in valid], dtype=float)
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    var_x = np.sum((x - x_mean) ** 2)
    if var_x == 0:
        return 0.0
    slope = np.sum((x - x_mean) * (y - y_mean)) / var_x
    return float(slope)

def compute_features_for_student(student_records: pd.DataFrame, as_of_week: int, att_cutoff: float=75.0, quiz_cutoff: float=50.0) -> Dict[str, Any]:
    sub_df = student_records[student_records['week'] <= as_of_week].sort_values('week')
    student_id = sub_df['student_id'].iloc[0] if len(sub_df) > 0 else 'UNKNOWN'
    total_weeks = as_of_week
    weeks_observed = len(sub_df)
    att_series = sub_df['attendance_pct'].dropna()
    att_valid_count = len(att_series)
    att_missing_rate = (total_weeks - att_valid_count) / max(1, total_weeks)
    if att_valid_count < 2:
        att_insufficient = True
        att_mean_recent = np.nan
        att_mean_overall = np.nan
        att_trend = np.nan
        att_drop_from_baseline = np.nan
        low_att_streak = 0
    else:
        att_insufficient = False
        recent_att = att_series.iloc[-3:] if len(att_series) >= 3 else att_series
        att_mean_recent = float(recent_att.mean())
        att_mean_overall = float(att_series.mean())
        trend_window = att_series.iloc[-6:] if len(att_series) >= 6 else att_series
        att_trend = float(compute_linear_trend(trend_window.tolist()))
        if len(att_series) >= 4:
            early_att = att_series.iloc[:3].mean()
            att_drop_from_baseline = float(early_att - att_mean_recent)
        else:
            att_drop_from_baseline = 0.0
        streak = 0
        for val in reversed(att_series.tolist()):
            if val < att_cutoff:
                streak += 1
            else:
                break
        low_att_streak = streak
    due_df = sub_df[sub_df['assignment_status'].isin(['Submitted', 'Late', 'Missing'])]
    due_count = len(due_df)
    unknown_assign_count = sub_df['assignment_status'].isna().sum()
    assignment_unknown_rate = unknown_assign_count / max(1, total_weeks)
    if due_count == 0:
        assign_insufficient = True
        missing_count_recent = 0
        late_rate_recent = 0.0
        submission_rate_overall = np.nan
        missing_streak = 0
    else:
        assign_insufficient = False
        recent_due = due_df.iloc[-4:] if len(due_df) >= 4 else due_df
        missing_count_recent = int((recent_due['assignment_status'] == 'Missing').sum())
        late_rate_recent = float((recent_due['assignment_status'] == 'Late').sum() / len(recent_due))
        submitted_or_late = due_df['assignment_status'].isin(['Submitted', 'Late']).sum()
        submission_rate_overall = float(submitted_or_late / due_count)
        m_streak = 0
        for status in reversed(due_df['assignment_status'].tolist()):
            if status == 'Missing':
                m_streak += 1
            else:
                break
        missing_streak = m_streak
    scheduled_quiz_weeks = [w for w in [2, 3, 5, 6, 8, 9, 11, 12] if w <= as_of_week]
    quizzes_scheduled_count = len(scheduled_quiz_weeks)
    quiz_series = sub_df[sub_df['quiz_taken'] == True]['quiz_score'].dropna()
    quizzes_taken_count = len(quiz_series)
    if quizzes_scheduled_count > 0:
        quiz_missing_rate = (quizzes_scheduled_count - quizzes_taken_count) / quizzes_scheduled_count
        quiz_participation_rate = float(quizzes_taken_count / quizzes_scheduled_count)
    else:
        quiz_missing_rate = 0.0
        quiz_participation_rate = 1.0
    if quizzes_taken_count < 2:
        quiz_insufficient = True
        quiz_mean_recent = np.nan
        quiz_mean_overall = np.nan
        quiz_trend = np.nan
        quiz_below_threshold_count = 0
    else:
        quiz_insufficient = False
        recent_quizzes = quiz_series.iloc[-3:] if len(quiz_series) >= 3 else quiz_series
        quiz_mean_recent = float(recent_quizzes.mean())
        quiz_mean_overall = float(quiz_series.mean())
        quiz_trend = float(compute_linear_trend(quiz_series.tolist()))
        quiz_below_threshold_count = int((quiz_series < quiz_cutoff).sum())
    raw_confidence = 1.0 - (0.4 * att_missing_rate + 0.3 * quiz_missing_rate + 0.3 * assignment_unknown_rate)
    data_confidence_score = float(np.clip(raw_confidence, 0.0, 1.0))
    if data_confidence_score >= 0.85:
        data_confidence_level = 'High'
    elif data_confidence_score >= 0.6:
        data_confidence_level = 'Medium'
    else:
        data_confidence_level = 'Low'
    return {'student_id': student_id, 'as_of_week': as_of_week, 'weeks_observed': weeks_observed, 'att_mean_recent': round(att_mean_recent, 2) if not np.isnan(att_mean_recent) else np.nan, 'att_mean_overall': round(att_mean_overall, 2) if not np.isnan(att_mean_overall) else np.nan, 'att_trend': round(att_trend, 2) if not np.isnan(att_trend) else np.nan, 'att_drop_from_baseline': round(att_drop_from_baseline, 2) if not np.isnan(att_drop_from_baseline) else np.nan, 'low_att_streak': low_att_streak, 'att_missing_rate': round(att_missing_rate, 3), 'att_insufficient': att_insufficient, 'missing_count_recent': missing_count_recent, 'late_rate_recent': round(late_rate_recent, 3), 'submission_rate_overall': round(submission_rate_overall, 3) if not np.isnan(submission_rate_overall) else np.nan, 'missing_streak': missing_streak, 'assignment_unknown_rate': round(assignment_unknown_rate, 3), 'assign_insufficient': assign_insufficient, 'quiz_mean_recent': round(quiz_mean_recent, 2) if not np.isnan(quiz_mean_recent) else np.nan, 'quiz_mean_overall': round(quiz_mean_overall, 2) if not np.isnan(quiz_mean_overall) else np.nan, 'quiz_trend': round(quiz_trend, 2) if not np.isnan(quiz_trend) else np.nan, 'quiz_below_threshold_count': quiz_below_threshold_count, 'quiz_participation_rate': round(quiz_participation_rate, 3), 'quiz_missing_rate': round(quiz_missing_rate, 3), 'quiz_insufficient': quiz_insufficient, 'data_confidence_score': round(data_confidence_score, 3), 'data_confidence_level': data_confidence_level}

def compute_features(weekly_df: pd.DataFrame, as_of_week: int=10, att_cutoff: float=75.0, quiz_cutoff: float=50.0) -> pd.DataFrame:
    records = []
    grouped = weekly_df.groupby('student_id', as_index=False)
    for s_id, group in grouped:
        feat = compute_features_for_student(group, as_of_week=as_of_week, att_cutoff=att_cutoff, quiz_cutoff=quiz_cutoff)
        records.append(feat)
    features_df = pd.DataFrame(records)
    return features_df
