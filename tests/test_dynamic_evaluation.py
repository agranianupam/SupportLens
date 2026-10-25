import pytest
import pandas as pd
import numpy as np
from app.data_loader import load_raw_data, get_cohort_snapshot, get_ml_system
from src.rules_engine import RulesEngine
from src.evaluation import (
    evaluate_snapshot,
    compute_binary_metrics,
    run_multiseed_evaluation,
    run_threshold_sensitivity,
)
from src.ml_model import SupportLensML, PROHIBITED_COLUMNS


def test_evaluation_week_selection_dynamic():
    """Verify that changing evaluation weeks recalculates metrics dynamically across weeks 4 to 12."""
    s_df, c_weekly, gt_df, _ = load_raw_data()
    ml_sys = get_ml_system()
    engine = RulesEngine()

    weeks_to_test = [4, 8, 10, 12]
    eval_by_week = {}

    for w in weeks_to_test:
        f_df, _ = get_cohort_snapshot(w)
        res = evaluate_snapshot(
            features_df=f_df,
            labels_df=gt_df,
            students_df=s_df,
            weekly_df=c_weekly,
            as_of_week=w,
            engine=engine,
            ml_system=ml_sys,
        )
        eval_by_week[w] = res
        r_m = res['models']['Rule Engine']
        assert r_m['tp'] + r_m['fp'] + r_m['fn'] + r_m['tn'] == 100
        assert r_m['tp'] + r_m['fn'] == 29
        assert r_m['fp'] + r_m['tn'] == 71

    # Check dynamic trajectory: Recall and F1 should increase from Week 4 to Week 10
    w4_metrics = eval_by_week[4]['models']['Rule Engine']
    w8_metrics = eval_by_week[8]['models']['Rule Engine']
    w10_metrics = eval_by_week[10]['models']['Rule Engine']

    assert w4_metrics['recall'] < w8_metrics['recall'] <= w10_metrics['recall']
    assert w4_metrics['f1'] < w8_metrics['f1'] <= w10_metrics['f1']


def test_benchmark_week_10_numerical_exactness():
    """Verify that Week 10 preserves the exact benchmark numbers."""
    s_df, c_weekly, gt_df, _ = load_raw_data()
    f_df, _ = get_cohort_snapshot(10)
    ml_sys = get_ml_system()
    engine = RulesEngine()

    res = evaluate_snapshot(
        features_df=f_df,
        labels_df=gt_df,
        students_df=s_df,
        weekly_df=c_weekly,
        as_of_week=10,
        engine=engine,
        ml_system=ml_sys,
    )

    r_m = res['models']['Rule Engine']
    assert r_m['tp'] == 23
    assert r_m['fp'] == 0
    assert r_m['fn'] == 6
    assert r_m['tn'] == 71
    assert r_m['precision'] == 1.000
    assert r_m['recall'] == 0.793
    assert r_m['f1'] == 0.885
    assert r_m['alert_burden_pct'] == 23.0


def test_baseline_and_models_consistency():
    """Verify all models & baselines evaluate on identical cohorts without data leakage."""
    s_df, c_weekly, gt_df, _ = load_raw_data()
    f_df, _ = get_cohort_snapshot(10)
    ml_sys = get_ml_system()
    engine = RulesEngine()

    res = evaluate_snapshot(
        features_df=f_df,
        labels_df=gt_df,
        students_df=s_df,
        weekly_df=c_weekly,
        as_of_week=10,
        engine=engine,
        ml_system=ml_sys,
    )

    # Ensure all 5 models have exactly 100 students evaluated on the same 29 positives
    for model_name, m in res['models'].items():
        assert m['tp'] + m['fp'] + m['fn'] + m['tn'] == 100
        assert m['tp'] + m['fn'] == 29
        assert m['fp'] + m['tn'] == 71

    # Data leakage check: Ensure ground truth labels and group attributes are strictly prohibited
    assert 'needs_support' in PROHIBITED_COLUMNS
    assert 'cohort_group' in PROHIBITED_COLUMNS
    assert 'study_mode' in PROHIBITED_COLUMNS
    assert 'prior_support_flag' in PROHIBITED_COLUMNS
    assert 'needs_support' not in ml_sys.feature_names
    from src.ml_model import FEATURE_COLUMNS
    assert 'needs_support' not in FEATURE_COLUMNS


def test_multiseed_stability_is_computed(tmp_path):
    """Verify that multi-seed evaluation executes live calculations across seeds."""
    seeds = [42, 7, 123]
    res = run_multiseed_evaluation(seeds=seeds, as_of_week=10, tmp_base_dir=str(tmp_path))
    detailed_df = res['detailed_df']
    summary_df = res['summary_df']

    assert len(detailed_df) == len(seeds) * 5
    rule_rows = detailed_df[detailed_df['Method'] == 'Rule Engine']
    assert len(rule_rows) == len(seeds)
    # Check that performance is not a fixed dummy value across seeds
    f1_values = rule_rows['F1 Score'].tolist()
    assert len(set(f1_values)) > 1, "Seeds should exhibit empirical metric variation."


def test_early_weeks_and_insufficient_data_graceful():
    """Verify that evaluating very early weeks or missing records handles boundaries gracefully."""
    s_df, c_weekly, gt_df, _ = load_raw_data()
    ml_sys = get_ml_system()
    engine = RulesEngine()

    # Week 1 snapshot (only 1 week of attendance, no assignment or trend)
    f_df1, _ = get_cohort_snapshot(1)
    res1 = evaluate_snapshot(
        features_df=f_df1,
        labels_df=gt_df,
        students_df=s_df,
        weekly_df=c_weekly,
        as_of_week=1,
        engine=engine,
        ml_system=ml_sys,
    )
    r_m1 = res1['models']['Rule Engine']
    assert r_m1['tp'] + r_m1['fp'] + r_m1['fn'] + r_m1['tn'] == 100
    assert r_m1['precision'] >= 0.0
    assert r_m1['recall'] >= 0.0
    assert r_m1['f1'] >= 0.0
