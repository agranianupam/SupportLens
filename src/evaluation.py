from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
from src.features import compute_features
from src.rules_engine import RulesEngine
from src.ml_model import SupportLensML
from src.data_generator import generate_synthetic_data
from src.data_quality import clean_and_validate_data

def compute_binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray]=None) -> Dict[str, Any]:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    fpr = fp / max(1, fp + tn)
    fnr = fn / max(1, fn + tp)
    alert_burden = (tp + fp) / max(1, len(y_true))
    metrics = {'tp': int(tp), 'fp': int(fp), 'tn': int(tn), 'fn': int(fn), 'precision': float(round(prec, 3)), 'recall': float(round(rec, 3)), 'f1': float(round(f1, 3)), 'false_positive_rate': float(round(fpr, 3)), 'false_negative_rate': float(round(fnr, 3)), 'alert_burden_pct': float(round(alert_burden * 100, 1))}
    if y_prob is not None:
        try:
            metrics['roc_auc'] = float(round(roc_auc_score(y_true, y_prob), 3))
            metrics['pr_auc'] = float(round(average_precision_score(y_true, y_prob), 3))
        except Exception:
            metrics['roc_auc'] = None
            metrics['pr_auc'] = None
    return metrics

def evaluate_snapshot(features_df: pd.DataFrame, labels_df: pd.DataFrame, students_df: pd.DataFrame, weekly_df: pd.DataFrame, as_of_week: int=10, engine: Optional[RulesEngine]=None, ml_system: Optional[SupportLensML]=None) -> Dict[str, Any]:
    engine = engine or RulesEngine()
    if ml_system is None:
        ml_system = SupportLensML()
        try:
            ml_system.load()
        except Exception:
            ml_system.train_models(features_df, labels_df)
    merged = pd.merge(features_df, labels_df, on='student_id')
    merged = pd.merge(merged, students_df[['student_id', 'study_mode', 'cohort_group']], on='student_id')
    y_true = merged['needs_support'].values
    flag_results = engine.score_all_students(merged)
    rule_preds = np.array([1 if res['support_level'] in ['Suggest Outreach', 'Priority Check-in'] else 0 for res in flag_results])
    rule_metrics = compute_binary_metrics(y_true, rule_preds)
    ml_preds_df = ml_system.predict(merged)
    ml_prob = ml_preds_df['ml_support_probability'].values
    ml_bin = (ml_prob >= 0.5).astype(int)
    ml_metrics = compute_binary_metrics(y_true, ml_bin, y_prob=ml_prob)
    X_scaled = ml_system.prepare_feature_matrix(merged)
    dt_prob = ml_system.dt_model.predict_proba(X_scaled)[:, 1]
    dt_bin = (dt_prob >= 0.5).astype(int)
    dt_metrics = compute_binary_metrics(y_true, dt_bin, y_prob=dt_prob)
    att_baseline_pred = (merged['att_mean_recent'].fillna(100.0) < 75.0).astype(int).values
    baseline1_metrics = compute_binary_metrics(y_true, att_baseline_pred)
    quiz_baseline_pred = (merged['quiz_mean_recent'].fillna(100.0) < 50.0).astype(int).values
    baseline2_metrics = compute_binary_metrics(y_true, quiz_baseline_pred)
    earliness_records = []
    all_weeks = list(range(4, 13))
    weekly_clean, _ = clean_and_validate_data(weekly_df, students_df)
    true_support_ids = set(labels_df[labels_df['needs_support'] == 1]['student_id'])
    first_flag_week = {}
    for w in all_weeks:
        w_feats = compute_features(weekly_clean, as_of_week=w)
        w_res = engine.score_all_students(w_feats)
        for r in w_res:
            s_id = r['student_id']
            if s_id in true_support_ids and s_id not in first_flag_week:
                if r['support_level'] in ['Suggest Outreach', 'Priority Check-in']:
                    first_flag_week[s_id] = w
    flagged_weeks = list(first_flag_week.values())
    avg_first_flag_week = float(round(np.mean(flagged_weeks), 2)) if flagged_weeks else None
    flagged_pct_by_w8 = float(round(sum((1 for fw in flagged_weeks if fw <= 8)) / max(1, len(true_support_ids)) * 100, 1))
    merged['rule_pred'] = rule_preds
    false_positives = merged[(merged['rule_pred'] == 1) & (merged['needs_support'] == 0)]
    false_negatives = merged[(merged['rule_pred'] == 0) & (merged['needs_support'] == 1)]
    fp_by_archetype = false_positives['archetype'].value_counts().to_dict()
    fn_by_archetype = false_negatives['archetype'].value_counts().to_dict()
    unmitigated_scores = []
    for _, row in merged.iterrows():
        feat = row.to_dict()
        res = engine.evaluate_student(feat)
        unmit_score = res['score']
        if res['mitigating_rules']:
            for m in res['mitigating_rules']:
                unmit_score += abs(m.get('points', 0))
        unmit_flag = 1 if unmit_score >= 5 else 0
        unmitigated_scores.append(unmit_flag)
    ablation_metrics = compute_binary_metrics(y_true, np.array(unmitigated_scores))
    return {'as_of_week': as_of_week, 'models': {'Rule Engine': rule_metrics, 'Logistic Regression': ml_metrics, 'Shallow Decision Tree': dt_metrics, 'Baseline: Attendance < 75%': baseline1_metrics, 'Baseline: Quiz < 50%': baseline2_metrics}, 'earliness': {'avg_first_flag_week': avg_first_flag_week, 'flagged_by_week_8_pct': flagged_pct_by_w8, 'total_true_need_students': len(true_support_ids), 'detected_students_count': len(flagged_weeks)}, 'error_analysis': {'false_positives_by_archetype': fp_by_archetype, 'false_negatives_by_archetype': fn_by_archetype, 'total_fp': int(rule_metrics['fp']), 'total_fn': int(rule_metrics['fn'])}, 'ablation': {'full_system': rule_metrics, 'without_mitigations': ablation_metrics, 'fp_reduction': int(ablation_metrics['fp'] - rule_metrics['fp'])}}

def compute_multi_seed_sensitivity(seeds: List[int]=[42, 43, 44, 45, 46], tmp_base_dir: str='data/eval_seeds') -> pd.DataFrame:
    records = []
    for s in seeds:
        out_d = f'{tmp_base_dir}/seed_{s}'
        generate_synthetic_data(seed=s, output_dir=out_d)
        s_df = pd.read_csv(f'{out_d}/students.csv')
        w_df = pd.read_csv(f'{out_d}/weekly_records.csv')
        gt_df = pd.read_csv(f'{out_d}/ground_truth_support_need.csv')
        clean_w, _ = clean_and_validate_data(w_df, s_df)
        f_df = compute_features(clean_w, as_of_week=10)
        engine = RulesEngine()
        results = engine.score_all_students(f_df)
        preds = np.array([1 if r['support_level'] in ['Suggest Outreach', 'Priority Check-in'] else 0 for r in results])
        merged = pd.merge(f_df, gt_df, on='student_id')
        y_true = merged['needs_support'].values
        m = compute_binary_metrics(y_true, preds)
        records.append({'seed': s, 'precision': m['precision'], 'recall': m['recall'], 'f1': m['f1'], 'alert_burden_pct': m['alert_burden_pct'], 'fpr': m['false_positive_rate']})
    df = pd.DataFrame(records)
    return df
