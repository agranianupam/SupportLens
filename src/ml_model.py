from typing import Dict, Any, List, Tuple, Optional
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer, MissingIndicator
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
PROHIBITED_COLUMNS = {'cohort_group', 'study_mode', 'prior_support_flag', 'archetype', 'student_id', 'needs_support', 'as_of_week', 'data_confidence_level'}
FEATURE_COLUMNS = ['att_mean_recent', 'att_mean_overall', 'att_trend', 'att_drop_from_baseline', 'low_att_streak', 'att_missing_rate', 'missing_count_recent', 'late_rate_recent', 'submission_rate_overall', 'missing_streak', 'assignment_unknown_rate', 'quiz_mean_recent', 'quiz_mean_overall', 'quiz_trend', 'quiz_below_threshold_count', 'quiz_participation_rate', 'quiz_missing_rate', 'data_confidence_score']
MODEL_DIR = Path('data/models')

class SupportLensML:

    def __init__(self, model_dir: Optional[Path]=None):
        self.model_dir = model_dir or MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.scaler = None
        self.imputer = None
        self.logreg_model = None
        self.dt_model = None
        self.feature_names = FEATURE_COLUMNS
        self.tree_rules_text = ''

    def prepare_feature_matrix(self, features_df: pd.DataFrame, fit: bool=False) -> np.ndarray:
        for col in features_df.columns:
            if col in PROHIBITED_COLUMNS and col in FEATURE_COLUMNS:
                raise ValueError(f"CRITICAL GUARDRAIL VIOLATION: Prohibited column '{col}' cannot enter ML pipeline!")
        X = features_df[self.feature_names].copy().values
        if fit:
            self.imputer = SimpleImputer(strategy='median')
            X_imp = self.imputer.fit_transform(X)
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X_imp)
        else:
            if self.imputer is None or self.scaler is None:
                raise ValueError('Imputer and Scaler must be fit before transform!')
            X_imp = self.imputer.transform(X)
            X_scaled = self.scaler.transform(X_imp)
        return X_scaled

    def train_models(self, features_df: pd.DataFrame, labels_df: pd.DataFrame, random_state: int=42) -> Dict[str, Any]:
        merged = pd.merge(features_df, labels_df[['student_id', 'needs_support']], on='student_id')
        y = merged['needs_support'].values
        X = self.prepare_feature_matrix(merged, fit=True)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=random_state, stratify=y)
        base_lr = LogisticRegression(class_weight='balanced', random_state=random_state, max_iter=1000)
        base_lr.fit(X_train, y_train)
        self.logreg_model = base_lr
        self.dt_model = DecisionTreeClassifier(max_depth=3, class_weight='balanced', random_state=random_state)
        self.dt_model.fit(X_train, y_train)
        self.tree_rules_text = export_text(self.dt_model, feature_names=self.feature_names)
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
        cv_scores = cross_val_score(base_lr, X, y, cv=skf, scoring='roc_auc')
        y_pred = base_lr.predict(X_test)
        y_prob = base_lr.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
        metrics = {'cv_roc_auc_mean': float(np.mean(cv_scores)), 'cv_roc_auc_std': float(np.std(cv_scores)), 'test_roc_auc': float(auc), 'tree_rules': self.tree_rules_text, 'feature_coefficients': dict(zip(self.feature_names, [float(c) for c in base_lr.coef_[0]]))}
        self.save()
        return metrics

    def predict(self, features_df: pd.DataFrame) -> pd.DataFrame:
        if self.logreg_model is None:
            self.load()
        X = self.prepare_feature_matrix(features_df, fit=False)
        probs = self.logreg_model.predict_proba(X)[:, 1]
        coefs = self.logreg_model.coef_[0]
        results = []
        for i, s_id in enumerate(features_df['student_id']):
            prob = float(probs[i])
            contributions = X[i] * coefs
            top_idx = np.argsort(np.abs(contributions))[::-1][:3]
            top_factors = []
            for idx in top_idx:
                fname = self.feature_names[idx]
                contrib = contributions[idx]
                val = features_df.iloc[i][fname]
                friendly_name = fname.replace('_', ' ').title()
                if contrib > 0:
                    top_factors.append(f'{friendly_name} pushed toward support need ({val})')
                else:
                    top_factors.append(f'{friendly_name} mitigated support need ({val})')
            results.append({'student_id': s_id, 'ml_support_probability': round(prob, 3), 'ml_flag': prob >= 0.5, 'top_contributing_factors': top_factors})
        return pd.DataFrame(results)

    def save(self):
        joblib.dump(self.logreg_model, self.model_dir / 'logreg_model.joblib')
        joblib.dump(self.dt_model, self.model_dir / 'dt_model.joblib')
        joblib.dump(self.scaler, self.model_dir / 'scaler.joblib')
        joblib.dump(self.imputer, self.model_dir / 'imputer.joblib')
        with open(self.model_dir / 'tree_rules.txt', 'w', encoding='utf-8') as f:
            f.write(self.tree_rules_text)

    def load(self):
        self.logreg_model = joblib.load(self.model_dir / 'logreg_model.joblib')
        self.dt_model = joblib.load(self.model_dir / 'dt_model.joblib')
        self.scaler = joblib.load(self.model_dir / 'scaler.joblib')
        self.imputer = joblib.load(self.model_dir / 'imputer.joblib')
        tree_path = self.model_dir / 'tree_rules.txt'
        if tree_path.exists():
            with open(tree_path, 'r', encoding='utf-8') as f:
                self.tree_rules_text = f.read()

def compute_agreement(rule_level: str, ml_flag_or_prob: Any, ml_threshold: float = 0.5) -> Dict[str, str]:
    rule_flag = rule_level in ['Suggest Outreach', 'Priority Check-in']
    if isinstance(ml_flag_or_prob, bool):
        ml_flag = ml_flag_or_prob
    else:
        ml_flag = float(ml_flag_or_prob) >= ml_threshold

    if rule_flag and ml_flag:
        return {
            'badge': 'Both indicate support may help',
            'icon': '✅',
            'type': 'both_support',
            'description': 'Both rule engine and ML model suggest outreach would be beneficial.',
        }
    elif not rule_flag and (not ml_flag):
        return {
            'badge': 'Both on track',
            'icon': '✅',
            'type': 'both_ontrack',
            'description': 'Both rule engine and ML model indicate the student is currently on track.',
        }
    elif rule_flag and (not ml_flag):
        return {
            'badge': 'Rules only: review for possible false positive',
            'icon': '⚠️',
            'type': 'rules_only',
            'description': 'Rule engine fired but ML probability is below threshold; review for potential false positive.',
        }
    else:
        return {
            'badge': 'ML only: review for possible missed signal',
            'icon': '⚠️',
            'type': 'ml_only',
            'description': 'ML model indicates potential need while rule thresholds were not crossed; review for possible missed signal.',
        }
