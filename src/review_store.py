from typing import Dict, Any, List, Optional
import sqlite3
import json
import datetime
from pathlib import Path
DB_PATH = Path('db/supportlens.db')
VALID_DECISIONS = {'Confirmed', 'Corrected', 'Dismissed', 'Deferred'}
VALID_REASON_CODES = {'Known circumstance', 'Data error', 'Already supported', 'Strong performance elsewhere', 'Other'}
VALID_ACTION_STATUSES = {'Planned', 'Done', 'Declined by student', 'No longer needed'}
VALID_SUPPORT_LEVELS = {'On Track', 'Monitor', 'Suggest Outreach', 'Priority Check-in', 'Insufficient Data'}
PROHIBITED_DECISIONS = {'penalise', 'fail', 'punish', 'misconduct', 'disciplinary', 'drop student'}

class ReviewStore:

    def __init__(self, db_path: Optional[Path]=None):
        self.db_path = db_path or DB_PATH
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
            conn.commit()

    def log_audit_event(self, actor_code: str, event_type: str, student_id: str, flag_id: Optional[int], details: Dict[str, Any]):
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n                INSERT INTO audit_log (timestamp, actor_code, event_type, student_id, flag_id, details_json)\n                VALUES (?, ?, ?, ?, ?, ?)\n                ', (timestamp, actor_code, event_type, student_id, flag_id, json.dumps(details)))
            conn.commit()

    def save_flag(self, flag_result: Dict[str, Any]) -> int:
        student_id = flag_result['student_id']
        as_of_week = flag_result['as_of_week']
        support_level = flag_result['support_level']
        score = flag_result['score']
        categories = json.dumps(flag_result['categories'])
        explanation_json = json.dumps(flag_result.get('explanation', {}))
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n                INSERT INTO flags (student_id, as_of_week, support_level, score, categories, explanation_json, created_at)\n                VALUES (?, ?, ?, ?, ?, ?, ?)\n                ON CONFLICT(student_id, as_of_week) DO UPDATE SET\n                    support_level=excluded.support_level,\n                    score=excluded.score,\n                    categories=excluded.categories,\n                    explanation_json=excluded.explanation_json\n                ', (student_id, as_of_week, support_level, score, categories, explanation_json, now))
            conn.commit()
            cursor.execute('SELECT flag_id FROM flags WHERE student_id=? AND as_of_week=?', (student_id, as_of_week))
            row = cursor.fetchone()
            flag_id = row['flag_id']
        self.log_audit_event(actor_code='SYSTEM_ENGINE', event_type='FLAG_EVALUATED', student_id=student_id, flag_id=flag_id, details={'support_level': support_level, 'score': score, 'as_of_week': as_of_week})
        return flag_id

    def record_review(self, flag_id: int, student_id: str, reviewer_code: str, decision: str, corrected_level: Optional[str]=None, reason_code: Optional[str]=None, reason_note: Optional[str]=None) -> int:
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
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n                INSERT INTO reviews (flag_id, student_id, reviewer_code, decision, corrected_level, reason_code, reason_note, reviewed_at)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                ', (flag_id, student_id, reviewer_code, decision, corrected_level, reason_code, reason_note, now))
            conn.commit()
            review_id = cursor.lastrowid
        self.log_audit_event(actor_code=reviewer_code, event_type=f'REVIEW_{decision.upper()}', student_id=student_id, flag_id=flag_id, details={'decision': decision, 'corrected_level': corrected_level, 'reason_code': reason_code, 'reason_note': reason_note})
        return review_id

    def record_action(self, student_id: str, action_type: str, reviewer_code: str, flag_id: Optional[int]=None, action_note: str='', planned_date: Optional[str]=None, status: str='Planned') -> int:
        if status not in VALID_ACTION_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Allowed: {VALID_ACTION_STATUSES}")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('\n                INSERT INTO actions (flag_id, student_id, action_type, action_note, planned_date, status, created_by, created_at)\n                VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n                ', (flag_id, student_id, action_type, action_note, planned_date, status, reviewer_code, now))
            conn.commit()
            action_id = cursor.lastrowid
        self.log_audit_event(actor_code=reviewer_code, event_type='ACTION_RECORDED', student_id=student_id, flag_id=flag_id, details={'action_id': action_id, 'action_type': action_type, 'status': status, 'planned_date': planned_date})
        return action_id

    def update_action_status(self, action_id: int, new_status: str, actor_code: str):
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
            return [dict(r) for r in cursor.fetchall()]

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

    def record_action_feedback(
    self,
    action_id: int,
    outcome: str,
    staff_note: str = "",
    recorded_by: str = "STAFF-01",
    ):
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
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
