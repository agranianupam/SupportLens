from pathlib import Path
from typing import Dict, Any, Tuple, List
import pandas as pd
import streamlit as st
from src.data_quality import clean_and_validate_data
from src.features import compute_features
from src.rules_engine import RulesEngine, load_config
import importlib
import src.review_store
if not hasattr(src.review_store, 'format_to_ist') or not hasattr(src.review_store.ReviewStore, 'save_flags_batch'):
    importlib.reload(src.review_store)
from src.ml_model import SupportLensML, compute_agreement
from src.review_store import ReviewStore, format_to_ist
from src.explain import generate_explanation

@st.cache_data
def load_raw_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    students_df = pd.read_csv('data/students.csv')
    weekly_raw_df = pd.read_csv('data/weekly_records.csv')
    ground_truth_df = pd.read_csv('data/ground_truth_support_need.csv')
    cleaned_weekly_df, quality_report = clean_and_validate_data(weekly_raw_df, students_df)
    return (students_df, cleaned_weekly_df, ground_truth_df, quality_report)

def get_review_store() -> ReviewStore:
    import importlib
    import src.review_store
    importlib.reload(src.review_store)
    return src.review_store.ReviewStore()

@st.cache_resource
def get_ml_system() -> SupportLensML:
    ml = SupportLensML()
    try:
        ml.load()
    except Exception:
        students_df, cleaned_weekly, ground_truth, _ = load_raw_data()
        feat_df = compute_features(cleaned_weekly, as_of_week=10)
        ml.train_models(feat_df, ground_truth)
    return ml

@st.cache_data
def get_cached_features(as_of_week: int) -> pd.DataFrame:
    _, cleaned_weekly, _, _ = load_raw_data()
    return compute_features(cleaned_weekly, as_of_week=as_of_week)

@st.cache_data
def compute_historical_snapshots(as_of_week: int) -> Dict[str, List[int]]:
    _, cleaned_weekly, _, _ = load_raw_data()
    engine = RulesEngine()
    history: Dict[str, List[int]] = {}
    prev_weeks = [w for w in [as_of_week - 2, as_of_week - 1] if w >= 4]
    for w in prev_weeks:
        w_feats = get_cached_features(w)
        w_res = engine.score_all_students(w_feats, config_override={'disable_persistence': True})
        for r in w_res:
            sid = r['student_id']
            if sid not in history:
                history[sid] = []
            history[sid].append(r['score'])
    return history


def get_cohort_snapshot(as_of_week: int, custom_thresholds: Dict[str, Any]=None) -> Tuple[pd.DataFrame, list]:
    students_df, cleaned_weekly, ground_truth, _ = load_raw_data()
    features_df = get_cached_features(as_of_week)
    engine = RulesEngine()
    store = get_review_store()
    ml = get_ml_system()
    hist_snapshots = compute_historical_snapshots(as_of_week)
    flag_results = engine.score_all_students(features_df, historical_snapshots=hist_snapshots, custom_thresholds=custom_thresholds)
    ml_preds = ml.predict(features_df)
    ml_dict = ml_preds.set_index('student_id').to_dict(orient='index')

    # Batch save flags in a single transaction (avoids 100 separate queries)
    if hasattr(store, 'save_flags_batch'):
        flag_ids = store.save_flags_batch(flag_results, as_of_week)
    else:
        flag_ids = {r['student_id']: store.save_flag(r) for r in flag_results}

    # Batch lookup review statuses in a single query (avoids 100 separate queries)
    system_levels = {r['student_id']: r['support_level'] for r in flag_results}
    if hasattr(store, 'get_all_effective_student_statuses'):
        effective_statuses = store.get_all_effective_student_statuses(as_of_week, system_levels)
    else:
        effective_statuses = {
            s_id: store.get_effective_student_status(s_id, lvl, as_of_week)
            for s_id, lvl in system_levels.items()
        }

    cohort_records = []
    meta_dict = students_df.set_index('student_id').to_dict(orient='index')
    feat_dict = features_df.set_index('student_id').to_dict(orient='index')

    for r in flag_results:
        s_id = r['student_id']
        r['flag_id'] = flag_ids.get(s_id, 1)
        effective = effective_statuses.get(s_id, {})
        r['display_level'] = effective.get('display_level', r['support_level'])
        r['review_decision'] = effective.get('review_decision', 'Pending Review')
        r['is_reviewed'] = effective.get('is_reviewed', False)
        r['override_applied'] = effective.get('override_applied', False)

        ml_info = ml_dict.get(s_id, {})
        r['ml_probability'] = ml_info.get('ml_support_probability', 0.0)
        r['ml_flag'] = ml_info.get('ml_flag', False)
        r['top_contributing_factors'] = ml_info.get('top_contributing_factors', [])
        r['agreement'] = compute_agreement(r['display_level'], r['ml_flag'])

        feat_row = feat_dict.get(s_id, {})
        r['explanation'] = generate_explanation(r, feat_row)

        m = meta_dict.get(s_id, {})
        r['cohort_group'] = m.get('cohort_group', 'Unknown')
        r['study_mode'] = m.get('study_mode', 'Unknown')
        cohort_records.append(r)

    return (features_df, cohort_records)
