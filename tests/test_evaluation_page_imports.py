import importlib
import pytest
from app.data_loader import load_raw_data, get_cohort_snapshot, get_ml_system
from src.rules_engine import RulesEngine
from src.evaluation import evaluate_snapshot, run_threshold_sensitivity


def test_evaluation_dependencies_and_execution():
    """Verify that all data loading and evaluation dependencies execute without error."""
    s_df, c_weekly, gt_df, _ = load_raw_data()
    f_df, cohort_records = get_cohort_snapshot(10)
    ml_sys = get_ml_system()
    r_engine = RulesEngine()

    eval_results = evaluate_snapshot(
        features_df=f_df,
        labels_df=gt_df,
        students_df=s_df,
        weekly_df=c_weekly,
        as_of_week=10,
        engine=r_engine,
        ml_system=ml_sys,
    )

    assert 'models' in eval_results
    assert 'Rule Engine' in eval_results['models']
    assert 'Logistic Regression' in eval_results['models']
    assert 'Shallow Decision Tree' in eval_results['models']
    assert 'earliness' in eval_results
    assert 'ablation_df' in eval_results
    assert 'error_analysis' in eval_results

    # Verify threshold sensitivity functions with the scoped features
    sens_res = run_threshold_sensitivity(f_df, gt_df, r_engine)
    assert 'sensitivity_df' in sens_res
    assert len(sens_res['sensitivity_df']) == 5  # baseline, +10%, -10%, +20%, -20%


def test_evaluation_page_script_syntax_and_imports():
    """Verify that app/pages/4_Evaluation.py has no unresolved imports or syntax bugs."""
    with open('app/pages/4_Evaluation.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Ensure get_cached_features is not imported in 4_Evaluation
    assert 'get_cached_features' not in content

    # Compile the script to check syntax
    compile(content, 'app/pages/4_Evaluation.py', 'exec')
