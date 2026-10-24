from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from src.features import compute_features
from src.rules_engine import RulesEngine
from src.evaluation import compute_binary_metrics

def audit_subgroup_fairness(features_df: pd.DataFrame, students_df: pd.DataFrame, labels_df: pd.DataFrame, flag_results: List[Dict[str, Any]], attribute_col: str='study_mode') -> Dict[str, Any]:
    merged = pd.merge(features_df, students_df[['student_id', attribute_col]], on='student_id')
    merged = pd.merge(merged, labels_df[['student_id', 'needs_support']], on='student_id')
    flags_map = {r['student_id']: 1 if r['support_level'] in ['Suggest Outreach', 'Priority Check-in'] else 0 for r in flag_results}
    merged['flagged'] = merged['student_id'].map(flags_map)
    groups = merged[attribute_col].unique()
    subgroup_metrics = {}
    for g in sorted(groups):
        sub = merged[merged[attribute_col] == g]
        y_true = sub['needs_support'].values
        y_pred = sub['flagged'].values
        m = compute_binary_metrics(y_true, y_pred)
        subgroup_metrics[str(g)] = {'count': len(sub), 'flag_count': int(sub['flagged'].sum()), 'flag_rate_pct': float(round(sub['flagged'].mean() * 100, 1)), 'precision': m['precision'], 'recall': m['recall'], 'fpr': m['false_positive_rate'], 'f1': m['f1']}
    flag_rates = [v['flag_rate_pct'] for v in subgroup_metrics.values()]
    recalls = [v['recall'] for v in subgroup_metrics.values()]
    fprs = [v['fpr'] for v in subgroup_metrics.values()]
    demographic_parity_gap = float(round(max(flag_rates) - min(flag_rates), 1))
    equal_opportunity_gap = float(round((max(recalls) - min(recalls)) * 100, 1))
    fpr_gap = float(round((max(fprs) - min(fprs)) * 100, 1))
    disparities_detected = []
    if demographic_parity_gap > 10.0:
        disparities_detected.append(f'Demographic parity disparity of {demographic_parity_gap}% exceeds 10% threshold.')
    if equal_opportunity_gap > 10.0:
        disparities_detected.append(f'Equal opportunity gap of {equal_opportunity_gap}% exceeds 10% threshold.')
    return {'attribute': attribute_col, 'subgroups': subgroup_metrics, 'demographic_parity_gap_pct': demographic_parity_gap, 'equal_opportunity_gap_pct': equal_opportunity_gap, 'fpr_gap_pct': fpr_gap, 'disparities_detected': disparities_detected}

def missing_data_stress_test(weekly_df: pd.DataFrame, students_df: pd.DataFrame, labels_df: pd.DataFrame, as_of_week: int=10, missing_levels: List[float]=[0.05, 0.1, 0.2, 0.3], seed: int=42) -> pd.DataFrame:
    np.random.seed(seed)
    records = []
    for extra_miss in missing_levels:
        df_corrupt = weekly_df.copy()
        mask_att = np.random.rand(len(df_corrupt)) < extra_miss
        df_corrupt.loc[mask_att, 'attendance_pct'] = np.nan
        mask_quiz = (df_corrupt['quiz_taken'] == True) & (np.random.rand(len(df_corrupt)) < extra_miss)
        df_corrupt.loc[mask_quiz, 'quiz_score'] = np.nan
        f_df = compute_features(df_corrupt, as_of_week=as_of_week)
        engine = RulesEngine()
        results = engine.score_all_students(f_df)
        merged = pd.merge(f_df, labels_df, on='student_id')
        y_true = merged['needs_support'].values
        preds = np.array([1 if r['support_level'] in ['Suggest Outreach', 'Priority Check-in'] else 0 for r in results])
        m = compute_binary_metrics(y_true, preds)
        conf_counts = pd.Series([r['data_confidence'] for r in results]).value_counts().to_dict()
        insufficient_data_count = sum((1 for r in results if r['support_level'] == 'Insufficient Data'))
        manual_check_count = sum((1 for r in results if r.get('needs_manual_check', False)))
        records.append({'added_missingness_pct': int(extra_miss * 100), 'precision': m['precision'], 'recall': m['recall'], 'f1': m['f1'], 'alert_burden_pct': m['alert_burden_pct'], 'high_confidence_count': conf_counts.get('High', 0), 'medium_confidence_count': conf_counts.get('Medium', 0), 'low_confidence_count': conf_counts.get('Low', 0), 'insufficient_data_count': insufficient_data_count, 'manual_check_recommended_count': manual_check_count})
    return pd.DataFrame(records)
