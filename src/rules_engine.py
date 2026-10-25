from typing import Dict, Any, List, Optional
import yaml
from pathlib import Path
import numpy as np
import pandas as pd
DEFAULT_CONFIG_PATH = Path('config.yaml')

def load_config(config_path: Optional[Path]=None) -> Dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

class RulesEngine:

    def __init__(self, config: Optional[Dict[str, Any]]=None, config_override: Optional[Dict[str, Any]]=None):
        self.config = config or load_config()
        if config_override:
            # Deep merge config override if provided
            for k, v in config_override.items():
                if isinstance(v, dict) and k in self.config and isinstance(self.config[k], dict):
                    self.config[k].update(v)
                else:
                    self.config[k] = v
        self.default_override = config_override or {}
        self.thresholds = self.config.get('thresholds', {})
        self.rules_cfg = self.config.get('rules', {})
        self.mitigating_cfg = self.config.get('mitigating_rules', {})
        self.levels_cfg = self.config.get('scoring_levels', {})

    def evaluate_student(self, features: Dict[str, Any], historical_scores: Optional[List[int]]=None, custom_thresholds: Optional[Dict[str, Any]]=None, config_override: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
        cfg_ovr = {**self.default_override, **(config_override or {})}
        th = self.thresholds.copy()
        if custom_thresholds:
            for cat, vals in custom_thresholds.items():
                if cat in th and isinstance(vals, dict):
                    th[cat].update(vals)
                else:
                    th[cat] = vals
        att_th = th.get('attendance', {})
        assign_th = th.get('submission', {})
        quiz_th = th.get('quiz', {})
        rec_th = th.get('recovery', {})
        conf_th = th.get('data_confidence', {})
        low_att_cutoff = att_th.get('low_att_cutoff', 75.0)
        critical_att_cutoff = att_th.get('critical_att_cutoff', 60.0)
        att_streak_cutoff = att_th.get('streak_weeks', 3)
        att_drop_cutoff = att_th.get('drop_from_baseline_cutoff', 20.0)
        sudden_drop_cutoff = att_th.get('sudden_drop_cutoff', 25.0)
        missing_count_cutoff = assign_th.get('missing_count_cutoff', 2)
        missing_streak_cutoff = assign_th.get('missing_streak_cutoff', 2)
        late_rate_cutoff = assign_th.get('late_rate_cutoff', 0.5)
        overall_sub_cutoff = assign_th.get('overall_submission_cutoff', 0.6)
        low_quiz_cutoff = quiz_th.get('low_quiz_cutoff', 50.0)
        quiz_trend_cutoff = quiz_th.get('quiz_trend_cutoff', -5.0)
        quiz_low_count_cutoff = quiz_th.get('quiz_below_threshold_count_cutoff', 2)
        quiz_part_cutoff = quiz_th.get('quiz_participation_cutoff', 0.6)
        high_quiz_mitigation = quiz_th.get('high_quiz_mitigation_cutoff', 80.0)
        att_trend_recovery = rec_th.get('att_trend_recovery', 3.0)
        quiz_trend_recovery = rec_th.get('quiz_trend_recovery', 3.0)
        fired_rules = []
        mitigating_rules = []
        abstained_rules = []
        categories = set()
        raw_score = 0
        if features.get('att_insufficient') and features.get('quiz_insufficient') and features.get('assign_insufficient'):
            return {'student_id': features.get('student_id'), 'as_of_week': features.get('as_of_week'), 'support_level': 'Insufficient Data', 'score': 0, 'categories': ['Insufficient Data'], 'fired_rules': [], 'mitigating_rules': [], 'abstained_rules': ['A1', 'A2', 'A3', 'A4', 'S1', 'S2', 'S3', 'S4', 'Q1', 'Q2', 'Q3', 'Q4', 'C1', 'C2'], 'data_confidence': features.get('data_confidence_level', 'Low'), 'data_confidence_score': features.get('data_confidence_score', 0.0), 'needs_manual_check': True, 'persistence_applied': False}
        if features.get('att_insufficient'):
            abstained_rules.extend(['A1', 'A2', 'A3', 'A4'])
        else:
            att_recent = features.get('att_mean_recent')
            att_streak = features.get('low_att_streak', 0)
            att_drop = features.get('att_drop_from_baseline', 0.0)
            if att_recent is not None and (not np.isnan(att_recent)):
                if att_recent < low_att_cutoff:
                    fired_rules.append({'id': 'A1', 'category': 'Attendance', 'description': f'Recent attendance ({att_recent:.1f}%) is below the {low_att_cutoff:.1f}% check-in threshold', 'observed_value': att_recent, 'threshold': low_att_cutoff, 'points': 2})
                    raw_score += 2
                    categories.add('Attendance Concern')
                if att_recent < critical_att_cutoff:
                    fired_rules.append({'id': 'A2', 'category': 'Attendance', 'description': f'Recent attendance ({att_recent:.1f}%) is critically low (< {critical_att_cutoff:.1f}%)', 'observed_value': att_recent, 'threshold': critical_att_cutoff, 'points': 2})
                    raw_score += 2
                    categories.add('Attendance Concern')
            if att_streak >= att_streak_cutoff:
                fired_rules.append({'id': 'A3', 'category': 'Attendance', 'description': f'Low attendance streak: {att_streak} consecutive weeks below {low_att_cutoff:.1f}%', 'observed_value': att_streak, 'threshold': att_streak_cutoff, 'points': 2})
                raw_score += 2
                categories.add('Attendance Concern')
            if att_drop is not None and (not np.isnan(att_drop)) and (att_drop >= att_drop_cutoff):
                fired_rules.append({'id': 'A4', 'category': 'Attendance', 'description': f'Attendance dropped by {att_drop:.1f} points compared to early-term baseline', 'observed_value': att_drop, 'threshold': att_drop_cutoff, 'points': 2})
                raw_score += 2
                categories.add('Attendance Concern')
        if features.get('assign_insufficient'):
            abstained_rules.extend(['S1', 'S2', 'S3', 'S4'])
        else:
            m_recent = features.get('missing_count_recent', 0)
            m_streak = features.get('missing_streak', 0)
            late_rate = features.get('late_rate_recent', 0.0)
            sub_rate = features.get('submission_rate_overall')
            if m_recent >= missing_count_cutoff:
                fired_rules.append({'id': 'S1', 'category': 'Submission', 'description': f'{m_recent} assignments unsubmitted in recent due weeks (threshold: ≥{missing_count_cutoff})', 'observed_value': m_recent, 'threshold': missing_count_cutoff, 'points': 2})
                raw_score += 2
                categories.add('Submission Concern')
            if m_streak >= missing_streak_cutoff:
                fired_rules.append({'id': 'S2', 'category': 'Submission', 'description': f'Streak of {m_streak} consecutive missed assignments', 'observed_value': m_streak, 'threshold': missing_streak_cutoff, 'points': 2})
                raw_score += 2
                categories.add('Submission Concern')
            if late_rate >= late_rate_cutoff:
                fired_rules.append({'id': 'S3', 'category': 'Submission', 'description': f'High late rate: {late_rate * 100:.0f}% of recent submissions were late', 'observed_value': late_rate, 'threshold': late_rate_cutoff, 'points': 1})
                raw_score += 1
                categories.add('Submission Concern')
            if sub_rate is not None and (not np.isnan(sub_rate)) and (sub_rate < overall_sub_cutoff):
                fired_rules.append({'id': 'S4', 'category': 'Submission', 'description': f'Overall submission rate ({sub_rate * 100:.0f}%) is under {overall_sub_cutoff * 100:.0f}%', 'observed_value': sub_rate, 'threshold': overall_sub_cutoff, 'points': 2})
                raw_score += 2
                categories.add('Submission Concern')
        if features.get('quiz_insufficient'):
            abstained_rules.extend(['Q1', 'Q2', 'Q3', 'Q4'])
        else:
            q_recent = features.get('quiz_mean_recent')
            q_trend = features.get('quiz_trend')
            q_low_count = features.get('quiz_below_threshold_count', 0)
            q_part = features.get('quiz_participation_rate', 1.0)
            if q_recent is not None and (not np.isnan(q_recent)) and (q_recent < low_quiz_cutoff):
                fired_rules.append({'id': 'Q1', 'category': 'Assessment', 'description': f'Recent quiz average ({q_recent:.1f}%) is below {low_quiz_cutoff:.1f}%', 'observed_value': q_recent, 'threshold': low_quiz_cutoff, 'points': 2})
                raw_score += 2
                categories.add('Assessment Concern')
            if q_trend is not None and (not np.isnan(q_trend)) and (q_trend <= quiz_trend_cutoff):
                fired_rules.append({'id': 'Q2', 'category': 'Assessment', 'description': f'Quiz scores downward trend of {abs(q_trend):.1f} points/quiz', 'observed_value': q_trend, 'threshold': quiz_trend_cutoff, 'points': 2})
                raw_score += 2
                categories.add('Assessment Concern')
            if q_low_count >= quiz_low_count_cutoff:
                fired_rules.append({'id': 'Q3', 'category': 'Assessment', 'description': f'{q_low_count} quizzes recorded below 50%', 'observed_value': q_low_count, 'threshold': quiz_low_count_cutoff, 'points': 1})
                raw_score += 1
                categories.add('Assessment Concern')
            if q_part < quiz_part_cutoff:
                fired_rules.append({'id': 'Q4', 'category': 'Assessment', 'description': f'Quiz participation rate ({q_part * 100:.0f}%) is under {quiz_part_cutoff * 100:.0f}%', 'observed_value': q_part, 'threshold': quiz_part_cutoff, 'points': 1})
                raw_score += 1
                categories.add('Assessment Concern')
        if not cfg_ovr.get('disable_compound', False):
            active_concerns = {'Attendance Concern', 'Submission Concern', 'Assessment Concern'}
            if active_concerns.issubset(categories):
                fired_rules.append({'id': 'C1', 'category': 'Engagement Drop', 'description': 'Multi-signal concern: Attendance, Submission, and Assessment challenges all present', 'observed_value': 'All 3 active', 'threshold': 'All 3 active', 'points': 2})
                raw_score += 2
                categories.add('Engagement Drop (Compound)')
            att_drop_val = features.get('att_drop_from_baseline')
            miss_count_val = features.get('missing_count_recent', 0)
            c2_triggered = False
            if att_drop_val is not None and (not np.isnan(att_drop_val)):
                if att_drop_val >= sudden_drop_cutoff and miss_count_val >= 2:
                    c2_triggered = True
                    fired_rules.append({'id': 'C2', 'category': 'Engagement Drop', 'description': f'Sudden change: attendance dropped {att_drop_val:.1f} pts from baseline with {miss_count_val} missed assignments', 'observed_value': f'drop={att_drop_val:.1f}, missing={miss_count_val}', 'threshold': f'drop>={sudden_drop_cutoff}, missing>=2', 'points': 2})
                    raw_score += 2
                    categories.add('Engagement Drop (Compound)')
        else:
            c2_triggered = False

        if not cfg_ovr.get('disable_m1', False):
            q_recent_val = features.get('quiz_mean_recent')
            miss_count_val = features.get('missing_count_recent', 0)
            if q_recent_val is not None and (not np.isnan(q_recent_val)):
                if q_recent_val >= high_quiz_mitigation and miss_count_val == 0:
                    mitigating_rules.append({'id': 'M1', 'category': 'Mitigating', 'description': f'Strong quiz mastery ({q_recent_val:.1f}%) with on-time submissions offsets low attendance', 'points': -2})
                    raw_score = max(0, raw_score - 2)

        if not cfg_ovr.get('disable_m2', False):
            att_trend_val = features.get('att_trend')
            quiz_trend_val = features.get('quiz_trend')
            if att_trend_val is not None and quiz_trend_val is not None:
                if not np.isnan(att_trend_val) and (not np.isnan(quiz_trend_val)):
                    if att_trend_val > att_trend_recovery and quiz_trend_val > quiz_trend_recovery:
                        mitigating_rules.append({'id': 'M2', 'category': 'Mitigating', 'description': f'Positive recovery: attendance (+{att_trend_val:.1f}/wk) and quizzes (+{quiz_trend_val:.1f}/wk) both improving', 'points': -2})
                        raw_score = max(0, raw_score - 2)

        if raw_score <= 2:
            base_level = 'On Track'
        elif raw_score <= 4:
            base_level = 'Monitor'
        elif raw_score <= 7:
            base_level = 'Suggest Outreach'
        else:
            base_level = 'Priority Check-in'

        persist_cfg = th.get('persistence', {})
        persistence_enabled = persist_cfg.get('enabled', True) and not cfg_ovr.get('disable_persistence', False)
        persist_window = persist_cfg.get('window_weeks', 3)
        persist_required = persist_cfg.get('required_count', 2)
        persistence_applied = False
        persistence_note = "Single snapshot evaluation"

        if base_level in ['Suggest Outreach', 'Priority Check-in'] and (not c2_triggered):
            if persistence_enabled and historical_scores is not None and len(historical_scores) >= (persist_window - 1):
                recent_scores = historical_scores[-(persist_window - 1):] + [raw_score]
                high_concern_count = sum((1 for s in recent_scores if s >= 5))
                if high_concern_count < persist_required:
                    base_level = 'Monitor'
                    persistence_applied = True
                    persistence_note = f"Watching: single-week signal (high concern in {high_concern_count} of last {len(recent_scores)} snapshots; {persist_required} required)"
                else:
                    persistence_note = f"Concern confirmed in {high_concern_count} of last {len(recent_scores)} snapshots"
            elif persistence_enabled and historical_scores is not None:
                persistence_note = f"Concern present (early snapshot history: {len(historical_scores) + 1} weeks observed)"

        data_conf_level = features.get('data_confidence_level', 'High')
        needs_manual_check = False
        if data_conf_level == 'Low' and raw_score >= 3:
            mitigating_rules.append({'id': 'M3', 'category': 'Mitigating', 'description': 'Low data confidence: capped at Monitor with recommendation for records check', 'points': 0})
            base_level = 'Monitor'
            needs_manual_check = True
        if features.get('att_insufficient') and features.get('quiz_insufficient'):
            base_level = 'Insufficient Data'
            needs_manual_check = True

        return {
            'student_id': features.get('student_id'),
            'as_of_week': features.get('as_of_week'),
            'support_level': base_level,
            'score': raw_score,
            'categories': sorted(list(categories)) if categories else ['On Track'],
            'fired_rules': fired_rules,
            'mitigating_rules': mitigating_rules,
            'abstained_rules': abstained_rules,
            'data_confidence': data_conf_level,
            'data_confidence_score': features.get('data_confidence_score', 1.0),
            'needs_manual_check': needs_manual_check,
            'persistence_applied': persistence_applied,
            'persistence_note': persistence_note
        }

    def score_all_students(self, features_df: pd.DataFrame, historical_snapshots: Optional[Dict[str, List[int]]]=None, custom_thresholds: Optional[Dict[str, Any]]=None, config_override: Optional[Dict[str, Any]]=None) -> List[Dict[str, Any]]:
        results = []
        for _, row in features_df.iterrows():
            feat = row.to_dict()
            s_id = feat.get('student_id')
            hist = historical_snapshots.get(s_id) if historical_snapshots else None
            res = self.evaluate_student(feat, historical_scores=hist, custom_thresholds=custom_thresholds, config_override=config_override)
            results.append(res)
        return results
