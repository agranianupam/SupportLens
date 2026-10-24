from typing import Dict, Any, List
import io
import pandas as pd

def generate_weekly_summary_csv(cohort_records: List[Dict[str, Any]]) -> str:
    clean_rows = []
    for r in cohort_records:
        clean_rows.append({'student_id': r.get('student_id'), 'as_of_week': r.get('as_of_week'), 'support_level': r.get('display_level', r.get('support_level')), 'system_level': r.get('support_level'), 'score': r.get('score'), 'categories': ', '.join(r.get('categories', [])), 'data_confidence': r.get('data_confidence'), 'data_confidence_score': r.get('data_confidence_score'), 'ml_probability': r.get('ml_probability'), 'review_status': r.get('review_decision', 'Pending Review')})
    df = pd.DataFrame(clean_rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def generate_cohort_report_markdown(as_of_week: int, kpis: Dict[str, Any], cohort_records: List[Dict[str, Any]]) -> str:
    md = f"# SupportLens Weekly Cohort Summary Report\n**Snapshot Period:** As of Week {as_of_week}  \n**Classification:** Confidential - Academic Coordinator Review Only  \n**Ethics Notice:** Synthetic data demonstration. Human review required before any outreach.\n\n---\n\n## 1. Executive Summary & Cohort Overview\n- **Total Students Enrolled:** {kpis.get('total_students', 100)}\n- **Students On Track:** {kpis.get('on_track_count', 0)} ({kpis.get('on_track_pct', 0)}%)\n- **Students Monitored:** {kpis.get('monitor_count', 0)} ({kpis.get('monitor_pct', 0)}%)\n- **Suggested for Outreach:** {kpis.get('suggest_outreach_count', 0)} ({kpis.get('suggest_outreach_pct', 0)}%)\n- **Priority Check-in Recommended:** {kpis.get('priority_checkin_count', 0)} ({kpis.get('priority_checkin_pct', 0)}%)\n- **Students Needing Records Check (Insufficient Data):** {kpis.get('insufficient_data_count', 0)}\n\n---\n\n## 2. Priority Follow-Up Recommendations\nThe following students have demonstrated multiple converging indicators where supportive coordinator check-ins could be most impactful:\n\n| Student ID | Effective Level | Primary Concern Categories | Score | Data Confidence | Coordinator Review Status |\n|---|---|---|---|---|---|\n"
    for r in cohort_records:
        level = r.get('display_level', r.get('support_level'))
        if level in ['Priority Check-in', 'Suggest Outreach']:
            cats = ', '.join(r.get('categories', []))
            conf = r.get('data_confidence', 'High')
            rev = r.get('review_decision', 'Pending Review')
            score = r.get('score', 0)
            md += f"| {r.get('student_id')} | **{level}** | {cats} | {score} | {conf} | {rev} |\n"
    md += '\n---\n\n## 3. Human-in-the-Loop Safeguards\n1. All alerts in this document represent automated screening signals, never academic penalties.\n2. Coordinators must confirm context, review recent submissions, and engage in compassionate dialog.\n3. Every staff decision and outreach action must be logged in the SupportLens audit register.\n'
    return md
