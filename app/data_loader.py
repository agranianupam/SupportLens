from pathlib import Path
from typing import Dict, Any, Tuple, List
import pandas as pd
import streamlit as st
from src.data_quality import clean_and_validate_data
from src.features import compute_features
from src.rules_engine import RulesEngine, load_config
from src.ml_model import SupportLensML, compute_agreement
from src.review_store import ReviewStore
from src.explain import generate_explanation

@st.cache_data
def load_raw_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    students_df = pd.read_csv('data/students.csv')
    weekly_raw_df = pd.read_csv('data/weekly_records.csv')
    ground_truth_df = pd.read_csv('data/ground_truth_support_need.csv')
    cleaned_weekly_df, quality_report = clean_and_validate_data(weekly_raw_df, students_df)
    return (students_df, cleaned_weekly_df, ground_truth_df, quality_report)

@st.cache_resource
def get_review_store() -> ReviewStore:
    return ReviewStore()

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

def compute_historical_snapshots(cleaned_weekly: pd.DataFrame, as_of_week: int, engine: RulesEngine) -> Dict[str, List[int]]:
    history: Dict[str, List[int]] = {}
    prev_weeks = [w for w in [as_of_week - 2, as_of_week - 1] if w >= 4]
    for w in prev_weeks:
        w_feats = compute_features(cleaned_weekly, as_of_week=w)
        w_res = engine.score_all_students(w_feats, config_override={'disable_persistence': True})
        for r in w_res:
            sid = r['student_id']
            if sid not in history:
                history[sid] = []
            history[sid].append(r['score'])
    return history


def get_cohort_snapshot(as_of_week: int, custom_thresholds: Dict[str, Any]=None) -> Tuple[pd.DataFrame, list]:
    students_df, cleaned_weekly, ground_truth, _ = load_raw_data()
    features_df = compute_features(cleaned_weekly, as_of_week=as_of_week)
    engine = RulesEngine()
    store = get_review_store()
    ml = get_ml_system()
    hist_snapshots = compute_historical_snapshots(cleaned_weekly, as_of_week, engine)
    flag_results = engine.score_all_students(features_df, historical_snapshots=hist_snapshots, custom_thresholds=custom_thresholds)
    ml_preds = ml.predict(features_df)
    ml_dict = ml_preds.set_index('student_id').to_dict(orient='index')
    cohort_records = []
    for r in flag_results:
        s_id = r['student_id']
        f_id = store.save_flag(r)
        r['flag_id'] = f_id
        effective = store.get_effective_student_status(s_id, r['support_level'], as_of_week)
        r['display_level'] = effective['display_level']
        r['review_decision'] = effective['review_decision']
        r['is_reviewed'] = effective['is_reviewed']
        r['override_applied'] = effective['override_applied']
        ml_info = ml_dict.get(s_id, {})
        r['ml_probability'] = ml_info.get('ml_support_probability', 0.0)
        r['ml_flag'] = ml_info.get('ml_flag', False)
        r['top_contributing_factors'] = ml_info.get('top_contributing_factors', [])
        ag = compute_agreement(r['display_level'], r['ml_flag'])
        r['agreement'] = ag
        feat_row = features_df[features_df['student_id'] == s_id].iloc[0].to_dict()
        r['explanation'] = generate_explanation(r, feat_row)
        cohort_records.append(r)
    meta_dict = students_df.set_index('student_id').to_dict(orient='index')
    for r in cohort_records:
        m = meta_dict.get(r['student_id'], {})
        r['cohort_group'] = m.get('cohort_group', 'Unknown')
        r['study_mode'] = m.get('study_mode', 'Unknown')
    return (features_df, cohort_records)
