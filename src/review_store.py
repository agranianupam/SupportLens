from typing import Dict, Any, List, Optional
import sqlite3
import json
import datetime
import re
from pathlib import Path
DB_PATH = Path('db/supportlens.db')
VALID_DECISIONS = {'Confirmed', 'Corrected', 'Dismissed', 'Deferred'}
VALID_REASON_CODES = {'Known circumstance', 'Data error', 'Already supported', 'Strong performance elsewhere', 'Other'}
VALID_ACTION_STATUSES = {'Planned', 'Done', 'Declined by student', 'No longer needed'}
VALID_SUPPORT_LEVELS = {'On Track', 'Monitor', 'Suggest Outreach', 'Priority Check-in', 'Insufficient Data'}
PROHIBITED_DECISIONS = {'penalise', 'fail', 'punish', 'misconduct', 'disciplinary', 'drop student'}
from zoneinfo import ZoneInfo
KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

def parse_to_ist(ts: Any) -> Optional[datetime.datetime]:
    """
    Safely parse any ISO or string timestamp to an aware datetime in Asia/Kolkata timezone.
    Guarantees that already-IST timestamps (including formatted strings) are not double-converted.
    """
    if not ts:
        return None
    if isinstance(ts, datetime.datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=datetime.timezone.utc).astimezone(KOLKATA_TZ)
        return ts.astimezone(KOLKATA_TZ)
    try:
        clean = str(ts).strip()
        was_ist = False
        if clean.endswith(' IST'):
            clean = clean[:-4].strip()
            was_ist = True
        if clean.endswith('Z'):
            clean = clean[:-1] + '+00:00'
        dt = datetime.datetime.fromisoformat(clean)
        if dt.tzinfo is None:
            if was_ist:
                return dt.replace(tzinfo=KOLKATA_TZ)
            return dt.replace(tzinfo=datetime.timezone.utc).astimezone(KOLKATA_TZ)
        return dt.astimezone(KOLKATA_TZ)
    except Exception:
        return None

def get_current_timestamp() -> str:
    """Return current timestamp in Indian Standard Time (IST) ISO format."""
    return datetime.datetime.now(KOLKATA_TZ).isoformat()

def format_to_ist(ts: Any) -> str:
    """Convert any UTC/ISO timestamp to a formatted Asia/Kolkata (IST) string safely without double-converting."""
    if not ts:
        return "-"
    dt = parse_to_ist(ts)
    if dt is not None:
        return dt.strftime("%Y-%m-%d %H:%M:%S IST")
    return str(ts)[:19].replace("T", " ") + " IST"

class ReviewStore:

    def __init__(self, db_path: Optional[Any] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n            CREATE TABLE IF NOT EXISTS flags (\n                flag_id INTEGER PRIMARY KEY AUTOINCREMENT,\n                student_id TEXT NOT NULL,\n                as_of_week INTEGER NOT NULL,\n                support_level TEXT NOT NULL,\n                score INTEGER NOT NULL,\n                categories TEXT NOT NULL,\n                explanation_json TEXT NOT NULL,\n                created_at TEXT NOT NULL,\n                UNIQUE(student_id, as_of_week)\n            )\n            ')
            cursor.execute('\n            CREATE TABLE IF NOT EXISTS reviews (\n                review_id INTEGER PRIMARY KEY AUTOINCREMENT,\n                flag_id INTEGER NOT NULL,\n                student_id TEXT NOT NULL,\n                reviewer_code TEXT NOT NULL,\n                decision TEXT NOT NULL,\n                corrected_level TEXT,\n                reason_code TEXT,\n                reason_note TEXT,\n                reviewed_at TEXT NOT NULL,\n                FOREIGN KEY(flag_id) REFERENCES flags(flag_id)\n            )\n            ')
            cursor.execute('\n            CREATE TABLE IF NOT EXISTS actions (\n                action_id INTEGER PRIMARY KEY AUTOINCREMENT,\n                flag_id INTEGER,\n                student_id TEXT NOT NULL,\n                action_type TEXT NOT NULL,\n                action_note TEXT,\n                planned_date TEXT,\n                status TEXT NOT NULL,\n                created_by TEXT NOT NULL,\n                created_at TEXT NOT NULL\n            )\n            ')
            cursor.execute('\n            CREATE TABLE IF NOT EXISTS audit_log (\n                log_id INTEGER PRIMARY KEY AUTOINCREMENT,\n                timestamp TEXT NOT NULL,\n                actor_code TEXT NOT NULL,\n                event_type TEXT NOT NULL,\n                student_id TEXT NOT NULL,\n                flag_id INTEGER,\n                details_json TEXT NOT NULL\n            )\n            ')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id INTEGER NOT NULL UNIQUE,
                student_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                staff_note TEXT,
                recorded_by TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY(action_id) REFERENCES actions(action_id)
            )
            ''')
            cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_update
            BEFORE UPDATE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'GUARDRAIL VIOLATION: audit_log is strictly append-only; UPDATE is prohibited.');
            END;
            ''')
            cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_delete
            BEFORE DELETE ON audit_log
            BEGIN
                SELECT RAISE(ABORT, 'GUARDRAIL VIOLATION: audit_log is strictly append-only; DELETE is prohibited.');
            END;
            ''')
            conn.commit()

    def log_audit_event(self, actor_code: str, event_type: str, student_id: str, flag_id: Optional[int], details: Dict[str, Any]):
        timestamp = get_current_timestamp()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n                INSERT INTO audit_log (timestamp, actor_code, event_type, student_id, flag_id, details_json)\n                VALUES (?, ?, ?, ?, ?, ?)\n                ', (timestamp, actor_code, event_type, student_id, flag_id, json.dumps(details)))
            conn.commit()

    def record_export(self, file_type: str, actor_code: str = 'STAFF-01', details: Optional[Dict[str, Any]] = None):
        self.log_audit_event(
            actor_code=actor_code,
            event_type='EXPORT',
            student_id='COHORT',
            flag_id=None,
            details={'file_type': file_type, **(details or {})}
        )

    def reset_demo_data(self, actor_code: str = 'STAFF-DEMO'):
        """
        Clears demo reviews, actions, and feedback for demo resets.
        CRITICAL: The audit_log table is strictly append-only.
        A DEMO_RESET marker event is logged to preserve audit integrity.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM action_feedback')
            cursor.execute('DELETE FROM actions')
            cursor.execute('DELETE FROM reviews')
            conn.commit()
        self.log_audit_event(
            actor_code=actor_code,
            event_type='DEMO_RESET',
            student_id='SYSTEM',
            flag_id=None,
            details={'action': 'Reset demo coordinator reviews, actions, and feedback'}
        )

    def save_flag(self, flag_result: Dict[str, Any]) -> int:
        student_id = flag_result['student_id']
        as_of_week = flag_result['as_of_week']
        support_level = flag_result['support_level']
        score = flag_result['score']
        categories = json.dumps(flag_result['categories'])
        expl_payload = {
            'explanation': flag_result.get('explanation', {}),
            'fired_rules': [r['id'] if isinstance(r, dict) else r for r in flag_result.get('fired_rules', [])],
        }
        explanation_json = json.dumps(expl_payload)
        now = get_current_timestamp()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT flag_id, support_level, score FROM flags WHERE student_id=? AND as_of_week=?',
                (student_id, as_of_week)
            )
            existing = cursor.fetchone()
            if existing and existing['support_level'] == support_level and existing['score'] == score:
                return existing['flag_id']

            cursor.execute('''
                INSERT INTO flags (student_id, as_of_week, support_level, score, categories, explanation_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(student_id, as_of_week) DO UPDATE SET
                    support_level=excluded.support_level,
                    score=excluded.score,
                    categories=excluded.categories,
                    explanation_json=excluded.explanation_json
                ''', (student_id, as_of_week, support_level, score, categories, explanation_json, now))
            conn.commit()
            cursor.execute('SELECT flag_id FROM flags WHERE student_id=? AND as_of_week=?', (student_id, as_of_week))
            row = cursor.fetchone()
            flag_id = row['flag_id']
        self.log_audit_event(actor_code='SYSTEM_ENGINE', event_type='FLAG_EVALUATED', student_id=student_id, flag_id=flag_id, details={'support_level': support_level, 'score': score, 'as_of_week': as_of_week})
        return flag_id

    def save_flags_batch(self, flag_results: List[Dict[str, Any]], as_of_week: int) -> Dict[str, int]:
        """
        Saves or updates cohort flags in a single SQLite transaction.
        Avoids 100 individual connections and queries during snapshot generation.
        """
        now = get_current_timestamp()
        flag_ids = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT flag_id, student_id, support_level, score FROM flags WHERE as_of_week = ?', (as_of_week,))
            existing = {r['student_id']: dict(r) for r in cursor.fetchall()}

            for r in flag_results:
                s_id = r['student_id']
                support_level = r['support_level']
                score = r['score']
                ex = existing.get(s_id)
                if ex and ex['support_level'] == support_level and ex['score'] == score:
                    flag_ids[s_id] = ex['flag_id']
                else:
                    categories = json.dumps(r.get('categories', []))
                    expl_payload = {
                        'summary': r.get('explanation', {}).get('summary', '') if isinstance(r.get('explanation'), dict) else '',
                        'fired_rules': [rule['id'] if isinstance(rule, dict) else rule for rule in r.get('fired_rules', [])],
                    }
                    cursor.execute('''
                        INSERT INTO flags (student_id, as_of_week, support_level, score, categories, explanation_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(student_id, as_of_week) DO UPDATE SET
                            support_level=excluded.support_level,
                            score=excluded.score,
                            categories=excluded.categories,
                            explanation_json=excluded.explanation_json
                    ''', (s_id, as_of_week, support_level, score, categories, json.dumps(expl_payload), now))
            conn.commit()

            cursor.execute('SELECT flag_id, student_id FROM flags WHERE as_of_week = ?', (as_of_week,))
            for r in cursor.fetchall():
                flag_ids[r['student_id']] = r['flag_id']

        return flag_ids

    def record_review(self, flag_id: int, student_id: str, reviewer_code: str, decision: str, corrected_level: Optional[str]=None, reason_code: Optional[str]=None, reason_note: Optional[str]=None) -> int:
        reviewer_code = reviewer_code.strip()
        if not re.match(r'^(STAFF-\d+|COORDINATOR-\d+|STAFF-DEMO)$', reviewer_code, re.IGNORECASE):
            raise ValueError(f"Reviewer code must be an anonymised staff identifier (e.g. 'STAFF-01'), got '{reviewer_code}'.")
        if decision not in VALID_DECISIONS:
            raise ValueError(f"Invalid review decision '{decision}'. Allowed: {VALID_DECISIONS}")
        if decision.lower() in PROHIBITED_DECISIONS:
            raise ValueError('GUARDRAIL VIOLATION: Punitive review decisions are strictly prohibited!')
        if decision == 'Corrected':
            if not corrected_level or corrected_level not in VALID_SUPPORT_LEVELS:
                raise ValueError("A valid 'corrected_level' is required when correcting a flag.")
            if not reason_code or not reason_note or (not reason_note.strip()):
                raise ValueError('Both a reason code and an explanation note are required when correcting a flag.')
        if decision == 'Dismissed':
            if not reason_code:
                raise ValueError('A reason code is required when dismissing a flag as a false positive.')
        now = get_current_timestamp()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n                INSERT INTO reviews (flag_id, student_id, reviewer_code, decision, corrected_level, reason_code, reason_note, reviewed_at)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                ', (flag_id, student_id, reviewer_code, decision, corrected_level, reason_code, reason_note, now))
            conn.commit()
            review_id = cursor.lastrowid
        self.log_audit_event(actor_code=reviewer_code, event_type=f'REVIEW_{decision.upper()}', student_id=student_id, flag_id=flag_id, details={'decision': decision, 'corrected_level': corrected_level, 'reason_code': reason_code, 'reason_note': reason_note})
        return review_id

    def record_action(self, student_id: str, action_type: str, reviewer_code: str, flag_id: Optional[int]=None, action_note: str='', planned_date: Optional[str]=None, status: str='Planned') -> int:
        reviewer_code = reviewer_code.strip()
        if not re.match(r'^(STAFF-\d+|COORDINATOR-\d+|STAFF-DEMO)$', reviewer_code, re.IGNORECASE):
            raise ValueError(f"Reviewer code must be an anonymised staff identifier (e.g. 'STAFF-01'), got '{reviewer_code}'.")
        if status not in VALID_ACTION_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Allowed: {VALID_ACTION_STATUSES}")
        now = get_current_timestamp()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n                INSERT INTO actions (flag_id, student_id, action_type, action_note, planned_date, status, created_by, created_at)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                ', (flag_id, student_id, action_type, action_note, planned_date, status, reviewer_code, now))
            conn.commit()
            action_id = cursor.lastrowid
        self.log_audit_event(actor_code=reviewer_code, event_type='ACTION_RECORDED', student_id=student_id, flag_id=flag_id, details={'action_id': action_id, 'action_type': action_type, 'status': status, 'planned_date': planned_date})
        return action_id

    def update_action_status(self, action_id: int, new_status: str, actor_code: str):
        actor_code = actor_code.strip()
        if not re.match(r'^(STAFF-\d+|COORDINATOR-\d+|STAFF-DEMO)$', actor_code, re.IGNORECASE):
            raise ValueError(f"Actor code must be an anonymised staff identifier (e.g. 'STAFF-01'), got '{actor_code}'.")
        if new_status not in VALID_ACTION_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE actions SET status=? WHERE action_id=?', (new_status, action_id))
            cursor.execute('SELECT student_id, flag_id, action_type FROM actions WHERE action_id=?', (action_id,))
            row = cursor.fetchone()
            conn.commit()
        if row:
            self.log_audit_event(actor_code=actor_code, event_type='ACTION_STATUS_UPDATED', student_id=row['student_id'], flag_id=row['flag_id'], details={'action_id': action_id, 'new_status': new_status, 'action_type': row['action_type']})

    def get_latest_student_review(self, student_id: str, as_of_week: Optional[int]=None) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if as_of_week is not None:
                cursor.execute('\n                    SELECT r.*, f.support_level as system_level, f.score as system_score\n                    FROM reviews r\n                    JOIN flags f ON r.flag_id = f.flag_id\n                    WHERE r.student_id = ? AND f.as_of_week = ?\n                    ORDER BY r.review_id DESC LIMIT 1\n                    ', (student_id, as_of_week))
            else:
                cursor.execute('\n                    SELECT r.*, f.support_level as system_level, f.score as system_score\n                    FROM reviews r\n                    JOIN flags f ON r.flag_id = f.flag_id\n                    WHERE r.student_id = ?\n                    ORDER BY r.review_id DESC LIMIT 1\n                    ', (student_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_effective_student_status(self, student_id: str, system_level: str, as_of_week: int) -> Dict[str, Any]:
        review = self.get_latest_student_review(student_id, as_of_week)
        if not review:
            return {'display_level': system_level, 'is_reviewed': False, 'review_decision': 'Pending Review', 'override_applied': False, 'review': None}
        decision = review['decision']
        if decision == 'Confirmed':
            return {'display_level': system_level, 'is_reviewed': True, 'review_decision': 'Confirmed by Staff', 'override_applied': False, 'review': review}
        elif decision == 'Corrected':
            return {'display_level': review['corrected_level'], 'is_reviewed': True, 'review_decision': f"Corrected to {review['corrected_level']}", 'override_applied': True, 'review': review}
        elif decision == 'Dismissed':
            return {'display_level': 'On Track', 'is_reviewed': True, 'review_decision': f"Dismissed ({review.get('reason_code', 'False Positive')})", 'override_applied': True, 'review': review}
        else:
            return {'display_level': system_level, 'is_reviewed': True, 'review_decision': 'Deferred: Monitoring', 'override_applied': False, 'review': review}

    def get_all_effective_student_statuses(self, as_of_week: int, system_levels: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        Consolidates student review lookups into a single query to eliminate N+1 database queries.
        Returns a mapping: student_id -> status_dict
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, f.support_level as system_level, f.score as system_score
                FROM reviews r
                JOIN flags f ON r.flag_id = f.flag_id
                WHERE f.as_of_week = ?
                ORDER BY r.review_id ASC
            ''', (as_of_week,))
            rows = cursor.fetchall()

        latest_reviews = {}
        for row in rows:
            latest_reviews[row['student_id']] = dict(row)

        effective_statuses = {}
        for student_id, system_level in system_levels.items():
            review = latest_reviews.get(student_id)
            if not review:
                effective_statuses[student_id] = {
                    'display_level': system_level,
                    'is_reviewed': False,
                    'review_decision': 'Pending Review',
                    'override_applied': False,
                    'review': None,
                }
            else:
                decision = review['decision']
                if decision == 'Confirmed':
                    effective_statuses[student_id] = {
                        'display_level': system_level,
                        'is_reviewed': True,
                        'review_decision': 'Confirmed by Staff',
                        'override_applied': False,
                        'review': review,
                    }
                elif decision == 'Corrected':
                    effective_statuses[student_id] = {
                        'display_level': review['corrected_level'],
                        'is_reviewed': True,
                        'review_decision': f"Corrected to {review['corrected_level']}",
                        'override_applied': True,
                        'review': review,
                    }
                elif decision == 'Dismissed':
                    effective_statuses[student_id] = {
                        'display_level': 'On Track',
                        'is_reviewed': True,
                        'review_decision': f"Dismissed ({review.get('reason_code', 'False Positive')})",
                        'override_applied': True,
                        'review': review,
                    }
                else:
                    effective_statuses[student_id] = {
                        'display_level': system_level,
                        'is_reviewed': True,
                        'review_decision': 'Deferred: Monitoring',
                        'override_applied': False,
                        'review': review,
                    }
        return effective_statuses

    def get_student_history(self, student_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM flags WHERE student_id=? ORDER BY as_of_week ASC', (student_id,))
            flags = [dict(r) for r in cursor.fetchall()]
            cursor.execute('SELECT * FROM reviews WHERE student_id=? ORDER BY reviewed_at DESC', (student_id,))
            reviews = [dict(r) for r in cursor.fetchall()]
            cursor.execute('SELECT * FROM actions WHERE student_id=? ORDER BY created_at DESC', (student_id,))
            actions = [dict(r) for r in cursor.fetchall()]
        return {'flags': flags, 'reviews': reviews, 'actions': actions}

    def get_audit_log(self, limit: int=200, student_id: Optional[str]=None, event_type: Optional[str]=None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = 'SELECT * FROM audit_log WHERE 1=1'
            params = []
            if student_id:
                query += ' AND student_id = ?'
                params.append(student_id)
            if event_type:
                query += ' AND event_type LIKE ?'
                params.append(f'%{event_type}%')
            query += ' ORDER BY log_id DESC LIMIT ?'
            params.append(limit)
            cursor.execute(query, tuple(params))
            records = [dict(r) for r in cursor.fetchall()]

        # Sort chronologically by actual event timestamp (newest event first),
        # using log_id descending as a consistent tie-breaker for identical timestamps.
        fallback_dt = datetime.datetime.min.replace(tzinfo=KOLKATA_TZ)
        records.sort(
            key=lambda r: (
                parse_to_ist(r.get('timestamp')) or fallback_dt,
                r.get('log_id', 0)
            ),
            reverse=True
        )
        return records

    def get_feedback_loop_analytics(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT decision, count(*) as cnt FROM reviews GROUP BY decision')
            decision_counts = {r['decision']: r['cnt'] for r in cursor.fetchall()}
            total_reviews = sum(decision_counts.values())
            cursor.execute("SELECT reason_code, count(*) as cnt FROM reviews WHERE decision='Dismissed' GROUP BY reason_code")
            dismissal_reasons = {r['reason_code']: r['cnt'] for r in cursor.fetchall()}
            recommendations = []
            if dismissal_reasons.get('Data error', 0) >= 3:
                recommendations.append("High dismissal rate due to 'Data error': investigate upstream attendance/quiz sync issues.")
            if dismissal_reasons.get('Strong performance elsewhere', 0) >= 3:
                recommendations.append("Frequent dismissals for 'Strong performance elsewhere': consider strengthening Mitigating Rule M1 threshold.")
        return {'total_reviews': total_reviews, 'decision_breakdown': decision_counts, 'dismissal_reasons': dismissal_reasons, 'system_tuning_recommendations': recommendations}

    def get_review_analytics(self, dismissal_rate_threshold: float = 0.30, min_reviews_threshold: int = 5) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT r.decision, r.reason_code, f.explanation_json FROM reviews r JOIN flags f ON r.flag_id = f.flag_id')
            rows = cursor.fetchall()

        total_reviews = len(rows)
        decision_counts = {}
        reason_counts = {}
        rule_totals = {}
        rule_dismissals = {}

        for row in rows:
            decision = row['decision']
            reason = row['reason_code']
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            # Parse fired rules from flag explanation_json
            try:
                expl_data = json.loads(row['explanation_json'])
                if isinstance(expl_data, dict):
                    fired = expl_data.get('fired_rules', [])
                else:
                    fired = []
            except Exception:
                fired = []

            for r_item in fired:
                rid = r_item['id'] if isinstance(r_item, dict) else str(r_item)
                rule_totals[rid] = rule_totals.get(rid, 0) + 1
                if decision == 'Dismissed':
                    rule_dismissals[rid] = rule_dismissals.get(rid, 0) + 1

        decision_pcts = {
            dec: round((cnt / total_reviews) * 100, 1) if total_reviews > 0 else 0.0
            for dec, cnt in decision_counts.items()
        }

        per_rule_analytics = []
        suggested_rule_reviews = []
        for rid, tot in rule_totals.items():
            dism = rule_dismissals.get(rid, 0)
            rate = dism / tot if tot > 0 else 0.0
            per_rule_analytics.append({
                'Rule ID': rid,
                'Total Reviews': tot,
                'Dismissals': dism,
                'Dismissal Rate (%)': round(rate * 100, 1),
            })
            if rate > dismissal_rate_threshold and tot >= min_reviews_threshold:
                suggested_rule_reviews.append(
                    f"Rule {rid} was dismissed in {rate * 100:.0f}% of reviewed cases ({dism}/{tot}); consider reviewing its threshold."
                )

        data_quality_notice = None
        data_error_count = reason_counts.get('Data error', 0)
        total_dismissals = decision_counts.get('Dismissed', 0)
        if data_error_count >= 3 or (total_dismissals > 0 and (data_error_count / total_dismissals) >= 0.30):
            data_quality_notice = (
                f"Data quality attention needed: {data_error_count} flags were dismissed due to 'Data error'. "
                "Investigate upstream attendance/quiz sync issues."
            )

        return {
            'total_reviews': total_reviews,
            'decision_counts': decision_counts,
            'decision_pcts': decision_pcts,
            'reason_counts': reason_counts,
            'per_rule_analytics': per_rule_analytics,
            'suggested_rule_reviews': suggested_rule_reviews,
            'data_quality_notice': data_quality_notice,
        }

    def get_cohort_action_effectiveness(self, min_ratings_per_type: int = 3) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.action_id, a.action_type, a.status, af.outcome, af.staff_note
                FROM actions a
                LEFT JOIN action_feedback af ON a.action_id = af.action_id
            ''')
            rows = [dict(r) for r in cursor.fetchall()]

        total_actions = len(rows)
        planned_count = sum(1 for r in rows if r['status'] == 'Planned')
        completed_count = sum(1 for r in rows if r['status'] == 'Done')
        completed_pct = round((completed_count / total_actions * 100), 1) if total_actions > 0 else 0.0

        rated_rows = [r for r in rows if r.get('outcome') is not None]
        total_rated = len(rated_rows)

        helpful_count = sum(1 for r in rated_rows if r['outcome'] == 'Helpful')
        partially_helpful_count = sum(1 for r in rated_rows if r['outcome'] == 'Partially helpful')
        not_helpful_count = sum(1 for r in rated_rows if r['outcome'] == 'Not helpful')

        helpful_pct = round((helpful_count / total_rated * 100), 1) if total_rated > 0 else 0.0
        partially_helpful_pct = round((partially_helpful_count / total_rated * 100), 1) if total_rated > 0 else 0.0
        not_helpful_pct = round((not_helpful_count / total_rated * 100), 1) if total_rated > 0 else 0.0

        # Aggregate breakdown by action_type with minimum count rule (>= min_ratings_per_type)
        type_groups = {}
        for r in rated_rows:
            atype = r['action_type']
            if atype not in type_groups:
                type_groups[atype] = {'Helpful': 0, 'Partially helpful': 0, 'Not helpful': 0, 'total': 0}
            type_groups[atype][r['outcome']] += 1
            type_groups[atype]['total'] += 1

        breakdown_by_type = []
        for atype, g in type_groups.items():
            if g['total'] >= min_ratings_per_type:
                breakdown_by_type.append({
                    'Action Type': atype,
                    'Helpful': g['Helpful'],
                    'Partially helpful': g['Partially helpful'],
                    'Not helpful': g['Not helpful'],
                    'Total Rated': g['total'],
                })

        return {
            'total_actions': total_actions,
            'planned_count': planned_count,
            'completed_count': completed_count,
            'completed_pct': completed_pct,
            'total_rated': total_rated,
            'helpful_count': helpful_count,
            'helpful_pct': helpful_pct,
            'partially_helpful_count': partially_helpful_count,
            'partially_helpful_pct': partially_helpful_pct,
            'not_helpful_count': not_helpful_count,
            'not_helpful_pct': not_helpful_pct,
            'breakdown_by_type': breakdown_by_type,
            'is_empty': total_rated == 0,
        }

    def record_action_feedback(
        self,
        action_id: int,
        outcome: str,
        staff_note: str = "",
        recorded_by: str = "STAFF-01",
    ):
        recorded_by = recorded_by.strip()
        if not re.match(r'^(STAFF-\d+|COORDINATOR-\d+|STAFF-DEMO)$', recorded_by, re.IGNORECASE):
            raise ValueError(f"Reviewer code must be an anonymised staff identifier (e.g. 'STAFF-01'), got '{recorded_by}'.")
        valid_outcomes = {
            "Helpful",
            "Partially helpful",
            "Not helpful",
        }

        if outcome not in valid_outcomes:
            raise ValueError(f"Invalid feedback outcome: {outcome}")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT student_id, status FROM actions WHERE action_id = ?",
                (action_id,),
            )
            action = cursor.fetchone()

            if action is None:
                raise ValueError("Follow-up action not found.")

            if action["status"] != "Done":
                raise ValueError(
                    "Feedback can only be recorded for completed actions."
                )

            cursor.execute(
                """
                INSERT INTO action_feedback (
                    action_id, student_id, outcome, staff_note,
                    recorded_by, recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(action_id) DO UPDATE SET
                    outcome = excluded.outcome,
                    staff_note = excluded.staff_note,
                    recorded_by = excluded.recorded_by,
                    recorded_at = excluded.recorded_at
                """,
                (
                    action_id,
                    action["student_id"],
                    outcome,
                    staff_note.strip(),
                    recorded_by,
                    get_current_timestamp(),
                ),
            )
            conn.commit()

            self.log_audit_event(
            actor_code=recorded_by,
            event_type="ACTION_FEEDBACK_RECORDED",
            student_id=action["student_id"],
            flag_id=None,
            details={
                "action_id": action_id,
                "outcome": outcome,
            },
        )

    def get_action_feedback(self, action_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM action_feedback
                WHERE action_id = ?
                """,
                (action_id,),
            )
            row = cursor.fetchone()

        return dict(row) if row else None
