import argparse
import os
from pathlib import Path
import numpy as np
import pandas as pd
ARCHETYPES = {'steady_performer': {'count': 50, 'att_mean': 93.0, 'att_std': 3.0, 'quiz_mean': 82.0, 'quiz_std': 5.0, 'assign_probs': [0.93, 0.05, 0.02], 'trend_att': 0.0, 'trend_quiz': 0.0}, 'average_variable': {'count': 20, 'att_mean': 82.0, 'att_std': 6.0, 'quiz_mean': 68.0, 'quiz_std': 8.0, 'assign_probs': [0.75, 0.18, 0.07], 'trend_att': -0.4, 'trend_quiz': -0.3}, 'gradual_decliner': {'count': 10, 'att_mean': 85.0, 'att_std': 5.0, 'quiz_mean': 75.0, 'quiz_std': 6.0, 'assign_probs': [0.55, 0.2, 0.25], 'decline_start': 4, 'decline_rate_att': -4.0, 'decline_rate_quiz': -3.5}, 'chronic_low': {'count': 8, 'att_mean': 52.0, 'att_std': 8.0, 'quiz_mean': 45.0, 'quiz_std': 8.0, 'assign_probs': [0.35, 0.25, 0.4], 'trend_att': -0.5, 'trend_quiz': -0.5}, 'sudden_dropper': {'count': 5, 'att_mean': 88.0, 'att_std': 4.0, 'quiz_mean': 78.0, 'quiz_std': 6.0, 'assign_probs': [0.85, 0.1, 0.05], 'drop_week': 8, 'collapsed_att': 40.0, 'collapsed_quiz': 40.0, 'collapsed_assign_probs': [0.15, 0.15, 0.7]}, 'strong_irregular': {'count': 4, 'att_mean': 60.0, 'att_std': 7.0, 'quiz_mean': 88.0, 'quiz_std': 4.0, 'assign_probs': [0.9, 0.08, 0.02], 'trend_att': 0.0, 'trend_quiz': 0.2}, 'recovering': {'count': 3, 'att_mean': 58.0, 'att_std': 6.0, 'quiz_mean': 52.0, 'quiz_std': 7.0, 'assign_probs': [0.6, 0.25, 0.15], 'recovery_start': 5, 'recovery_rate_att': 4.5, 'recovery_rate_quiz': 4.0, 'improved_assign_probs': [0.9, 0.08, 0.02]}}

def generate_synthetic_data(seed: int=42, output_dir: str='data'):
    np.random.seed(seed)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    total_students = 100
    id_nums = np.arange(1, total_students + 1)
    np.random.shuffle(id_nums)
    student_ids = [f'S-{num:04d}' for num in id_nums]
    archetype_list = []
    for arch_name, config in ARCHETYPES.items():
        archetype_list.extend([arch_name] * config['count'])
    np.random.shuffle(archetype_list)
    cohort_groups = np.random.choice(['Section A', 'Section B', 'Section C'], size=total_students, p=[0.4, 0.35, 0.25])
    study_modes = np.random.choice(['Full-time', 'Part-time'], size=total_students, p=[0.75, 0.25])
    prior_support = np.random.choice([False, True], size=total_students, p=[0.85, 0.15])
    students_df = pd.DataFrame({'student_id': student_ids, 'archetype': archetype_list, 'cohort_group': cohort_groups, 'study_mode': study_modes, 'prior_support_flag': prior_support})
    students_df.to_csv(out_path / 'students.csv', index=False)
    needs_support = []
    for idx, row in students_df.iterrows():
        arch = row['archetype']
        if arch in ['gradual_decliner', 'chronic_low', 'sudden_dropper']:
            needs_support.append(1)
        elif arch in ['steady_performer', 'strong_irregular', 'recovering']:
            needs_support.append(0)
        else:
            needs_support.append(1 if np.random.rand() < 0.2 else 0)
    ground_truth_df = pd.DataFrame({'student_id': student_ids, 'archetype': archetype_list, 'needs_support': needs_support})
    ground_truth_df.to_csv(out_path / 'ground_truth_support_need.csv', index=False)
    weeks = list(range(1, 13))
    quiz_weeks = {2, 3, 5, 6, 8, 9, 11, 12}
    assignment_due_weeks = {2, 4, 6, 8, 10, 12}
    records = []
    for _, s_row in students_df.iterrows():
        s_id = s_row['student_id']
        arch = s_row['archetype']
        cfg = ARCHETYPES[arch]
        is_part_time = s_row['study_mode'] == 'Part-time'
        for w in weeks:
            base_att = cfg['att_mean']
            if is_part_time:
                base_att -= 8.0
            if arch == 'gradual_decliner':
                if w >= cfg['decline_start']:
                    base_att += (w - cfg['decline_start'] + 1) * cfg['decline_rate_att']
            elif arch == 'sudden_dropper':
                if w >= cfg['drop_week']:
                    base_att = cfg['collapsed_att']
            elif arch == 'recovering':
                if w >= cfg['recovery_start']:
                    base_att += (w - cfg['recovery_start'] + 1) * cfg['recovery_rate_att']
            else:
                base_att += (w - 1) * cfg.get('trend_att', 0.0)
            att_noise = np.random.normal(0, cfg['att_std'])
            att_val = float(np.clip(base_att + att_noise, 0.0, 100.0))
            if w not in assignment_due_weeks:
                assign_status = 'Not Due'
            else:
                probs = cfg['assign_probs']
                if arch == 'sudden_dropper' and w >= cfg['drop_week']:
                    probs = cfg['collapsed_assign_probs']
                elif arch == 'recovering' and w >= cfg['recovery_start']:
                    probs = cfg['improved_assign_probs']
                elif arch == 'gradual_decliner' and w >= cfg['decline_start']:
                    step = (w - cfg['decline_start']) * 0.08
                    p_sub = max(0.15, probs[0] - step)
                    p_late = min(0.35, probs[1] + step / 2)
                    p_miss = max(0.0, 1.0 - (p_sub + p_late))
                    probs = [p_sub, p_late, p_miss]
                assign_status = np.random.choice(['Submitted', 'Late', 'Missing'], p=probs)
            if w not in quiz_weeks:
                quiz_score = None
                quiz_taken = False
            else:
                base_quiz = cfg['quiz_mean']
                if arch == 'gradual_decliner':
                    if w >= cfg['decline_start']:
                        base_quiz += (w - cfg['decline_start'] + 1) * cfg['decline_rate_quiz']
                elif arch == 'sudden_dropper':
                    if w >= cfg['drop_week']:
                        base_quiz = cfg['collapsed_quiz']
                elif arch == 'recovering':
                    if w >= cfg['recovery_start']:
                        base_quiz += (w - cfg['recovery_start'] + 1) * cfg['recovery_rate_quiz']
                else:
                    base_quiz += (w - 1) * cfg.get('trend_quiz', 0.0)
                quiz_noise = np.random.normal(0, cfg['quiz_std'])
                raw_quiz = float(np.clip(base_quiz + quiz_noise, 0.0, 100.0))
                quiz_skip_prob = 0.03
                if arch == 'chronic_low':
                    quiz_skip_prob = 0.3
                elif arch == 'sudden_dropper' and w >= cfg['drop_week']:
                    quiz_skip_prob = 0.5
                elif arch == 'gradual_decliner' and w >= cfg['decline_start']:
                    quiz_skip_prob = 0.2
                if np.random.rand() < quiz_skip_prob:
                    quiz_taken = False
                    quiz_score = None
                else:
                    quiz_taken = True
                    quiz_score = round(raw_quiz, 1)
            records.append({'student_id': s_id, 'week': w, 'attendance_pct': round(att_val, 1), 'assignment_status': assign_status, 'quiz_score': quiz_score, 'quiz_taken': quiz_taken})
    weekly_df = pd.DataFrame(records)
    att_mask = np.random.rand(len(weekly_df)) < 0.05
    weekly_df.loc[att_mask, 'attendance_pct'] = np.nan
    quiz_mask = (weekly_df['quiz_taken'] == True) & (np.random.rand(len(weekly_df)) < 0.08)
    weekly_df.loc[quiz_mask, 'quiz_score'] = np.nan
    gap_students = np.random.choice(student_ids, size=4, replace=False)
    for g_id in gap_students:
        gap_start = np.random.choice([4, 5, 6, 7])
        mask = (weekly_df['student_id'] == g_id) & weekly_df['week'].isin([gap_start, gap_start + 1, gap_start + 2])
        weekly_df.loc[mask, 'attendance_pct'] = np.nan
        weekly_df.loc[mask, 'quiz_score'] = np.nan
        weekly_df.loc[mask, 'quiz_taken'] = False
        weekly_df.loc[mask, 'assignment_status'] = np.nan
    late_students = np.random.choice(student_ids, size=3, replace=False)
    for l_id in late_students:
        mask = (weekly_df['student_id'] == l_id) & (weekly_df['week'] <= 3)
        weekly_df.loc[mask, 'attendance_pct'] = np.nan
        weekly_df.loc[mask, 'quiz_score'] = np.nan
        weekly_df.loc[mask, 'quiz_taken'] = False
        weekly_df.loc[mask, 'assignment_status'] = np.nan
    dup_rows = weekly_df.iloc[[10, 45]].copy()
    weekly_df = pd.concat([weekly_df, dup_rows], ignore_index=True)
    weekly_df.loc[22, 'attendance_pct'] = 105.0
    weekly_df.loc[88, 'quiz_score'] = -10.0
    weekly_df.loc[112, 'assignment_status'] = 'Submitted_Invalid'
    weekly_df.to_csv(out_path / 'weekly_records.csv', index=False)
    print(f'Generated synthetic data in {out_path}:')
    print(f'  students.csv: {len(students_df)} students')
    print(f'  weekly_records.csv: {len(weekly_df)} rows')
    print(f'  ground_truth_support_need.csv: {len(ground_truth_df)} labels')
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SupportLens Synthetic Data Generator')
    parser.add_argument('--seed', type=int, default=42, help='Random seed (default 42)')
    parser.add_argument('--output_dir', type=str, default='data', help='Output directory')
    args = parser.parse_args()
    generate_synthetic_data(seed=args.seed, output_dir=args.output_dir)
