from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
ALLOWED_ASSIGNMENT_STATUSES = {'Submitted', 'Late', 'Missing', 'Not Due'}

def clean_and_validate_data(weekly_df: pd.DataFrame, students_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    df = weekly_df.copy()
    initial_rows = len(df)
    duplicate_mask = df.duplicated(subset=['student_id', 'week'], keep='first')
    duplicate_count = int(duplicate_mask.sum())
    df = df[~duplicate_mask].copy()
    roster_ids = set(students_df['student_id'])
    weekly_student_ids = set(df['student_id'])
    missing_students = roster_ids - weekly_student_ids
    unknown_students = weekly_student_ids - roster_ids
    invalid_att_mask = (df['attendance_pct'] < 0) | (df['attendance_pct'] > 100)
    invalid_att_count = int(invalid_att_mask.sum())
    df.loc[invalid_att_mask, 'attendance_pct'] = np.nan
    invalid_quiz_mask = (df['quiz_score'] < 0) | (df['quiz_score'] > 100)
    invalid_quiz_count = int(invalid_quiz_mask.sum())
    df.loc[invalid_quiz_mask, 'quiz_score'] = np.nan
    invalid_assign_mask = df['assignment_status'].notna() & ~df['assignment_status'].isin(ALLOWED_ASSIGNMENT_STATUSES)
    invalid_assign_count = int(invalid_assign_mask.sum())
    df.loc[invalid_assign_mask, 'assignment_status'] = np.nan
    missing_att_count = int(df['attendance_pct'].isna().sum())
    missing_quiz_count = int(((df['quiz_taken'] == True) & df['quiz_score'].isna()).sum())
    missing_assign_count = int(df['assignment_status'].isna().sum())
    weeks_per_student = df.groupby('student_id')['week'].nunique()
    incomplete_weeks_students = int((weeks_per_student < 12).sum())
    total_cells = len(df) * 4
    total_missing_cells = missing_att_count + missing_quiz_count + missing_assign_count
    overall_completeness = round((1.0 - total_missing_cells / total_cells) * 100.0, 2)
    report = {'initial_rows': initial_rows, 'clean_rows': len(df), 'duplicates_removed': duplicate_count, 'invalid_attendance_corrected': invalid_att_count, 'invalid_quiz_corrected': invalid_quiz_count, 'invalid_assignment_status_corrected': invalid_assign_count, 'missing_attendance_values': missing_att_count, 'missing_quiz_scores': missing_quiz_count, 'missing_assignment_statuses': missing_assign_count, 'total_roster_students': len(students_df), 'students_with_incomplete_weeks': incomplete_weeks_students, 'overall_data_completeness_pct': overall_completeness, 'unmatched_students': list(missing_students | unknown_students)}
    return (df, report)
