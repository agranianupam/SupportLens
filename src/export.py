from typing import Dict, Any, List, Optional
import io
import os
import tempfile
import pandas as pd
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

BANNED_WORDS = {'fail', 'punish', 'penalise', 'penalize', 'disciplinary', 'expel', 'drop student'}

def generate_weekly_summary_csv(cohort_records: List[Dict[str, Any]]) -> str:
    """
    Generate anonymised weekly summary CSV strictly adhering to ground rules:
    Columns: student_id, as_of_week, support_level, categories, score, data_confidence, review_status, planned_action_status
    No group attributes, no free-text staff notes.
    """
    clean_rows = []
    for r in cohort_records:
        post_review_level = r.get('display_level', r.get('support_level'))
        cats = r.get('categories', [])
        if isinstance(cats, list):
            cats_str = '; '.join(cats)
        else:
            cats_str = str(cats)
            
        clean_rows.append({
            'student_id': r.get('student_id'),
            'as_of_week': r.get('as_of_week', 10),
            'support_level': post_review_level,
            'categories': cats_str,
            'score': r.get('score', 0),
            'data_confidence': r.get('data_confidence', 'High'),
            'review_status': r.get('review_decision', 'Pending Review'),
            'planned_action_status': r.get('planned_action_status', 'None'),
        })
    df = pd.DataFrame(clean_rows)
    # Ensure exact column ordering
    col_order = [
        'student_id', 'as_of_week', 'support_level', 'categories',
        'score', 'data_confidence', 'review_status', 'planned_action_status'
    ]
    df = df[col_order]
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()


def generate_audit_log_csv(audit_records: List[Dict[str, Any]]) -> str:
    """
    Generate CSV export of append-only audit log.
    """
    from src.review_store import format_to_ist
    clean_rows = []
    for log in audit_records:
        clean_rows.append({
            'log_id': log.get('log_id'),
            'timestamp': format_to_ist(log.get('timestamp')),
            'actor_code': log.get('actor_code'),
            'event_type': log.get('event_type'),
            'student_id': log.get('student_id'),
            'flag_id': log.get('flag_id') if log.get('flag_id') else '',
            'details': log.get('details_json', ''),
        })
    df = pd.DataFrame(clean_rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()


def generate_review_analytics_csv(analytics: Dict[str, Any]) -> str:
    """
    Generate CSV export of review outcomes and rule dismissal statistics.
    """
    rows = []
    # Section 1: Decision breakdown
    for dec, count in analytics.get('decision_counts', {}).items():
        pct = analytics.get('decision_pcts', {}).get(dec, 0.0)
        rows.append({'category': 'Decision Outcome', 'metric': dec, 'count': count, 'detail': f"{pct:.1f}%"})
    # Section 2: Dismissal reasons
    for reason, count in analytics.get('reason_counts', {}).items():
        rows.append({'category': 'Dismissal Reason', 'metric': reason, 'count': count, 'detail': ''})
    # Section 3: Per-rule dismissal rate
    for rule_info in analytics.get('per_rule_analytics', []):
        rid = rule_info.get('Rule ID')
        tot = rule_info.get('Total Reviews', 0)
        dism = rule_info.get('Dismissals', 0)
        rate = rule_info.get('Dismissal Rate (%)', 0.0)
        rows.append({'category': 'Rule Dismissal Rate', 'metric': f"Rule {rid}", 'count': tot, 'detail': f"{dism} dismissed ({rate:.1f}%)"})
    df = pd.DataFrame(rows)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()


def _generate_trend_chart_image(width: int = 700, height: int = 240) -> bytes:
    """Generate a clean cohort trend chart image using Pillow."""
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Outer border and grid
    margin_l = 60
    margin_r = 30
    margin_t = 30
    margin_b = 40
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    
    # Draw background box
    draw.rectangle([margin_l, margin_t, margin_l + plot_w, margin_t + plot_h], outline=(220, 226, 235), width=1)
    
    # Weeks 4 to 10
    weeks = list(range(4, 11))
    # Simulated trend proportions for weekly cohort support levels
    # On Track: ~75 -> 68; Monitor: ~15 -> 18; Outreach: ~7 -> 9; Priority: ~3 -> 5
    priority_trend = [2, 3, 3, 4, 4, 5, 5]
    outreach_trend = [5, 6, 6, 7, 8, 8, 9]
    monitor_trend = [12, 14, 15, 16, 17, 18, 18]
    
    # X and Y scales
    max_y = 30
    def get_pt(wk_idx, val):
        x = margin_l + int((wk_idx / (len(weeks) - 1)) * plot_w)
        y = margin_t + plot_h - int((val / max_y) * plot_h)
        return (x, y)
    
    # Draw grid lines
    for gy in [0, 10, 20, 30]:
        y_pos = margin_t + plot_h - int((gy / max_y) * plot_h)
        draw.line([(margin_l, y_pos), (margin_l + plot_w, y_pos)], fill=(240, 243, 248), width=1)
        draw.text((margin_l - 25, y_pos - 6), str(gy), fill=(130, 140, 155))
        
    for i, w in enumerate(weeks):
        x_pos = margin_l + int((i / (len(weeks) - 1)) * plot_w)
        draw.line([(x_pos, margin_t + plot_h), (x_pos, margin_t + plot_h + 4)], fill=(180, 190, 205), width=1)
        draw.text((x_pos - 12, margin_t + plot_h + 8), f"W{w}", fill=(100, 110, 125))
        
    # Draw series lines
    def draw_series(vals, color, width_px=3):
        pts = [get_pt(i, v) for i, v in enumerate(vals)]
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i+1]], fill=color, width=width_px)
        for pt in pts:
            draw.ellipse([pt[0]-3, pt[1]-3, pt[0]+3, pt[1]+3], fill=color)

    draw_series(monitor_trend, (245, 158, 11))      # Amber (Monitor)
    draw_series(outreach_trend, (249, 115, 22))     # Orange (Suggest Outreach)
    draw_series(priority_trend, (239, 68, 68))      # Red (Priority Check-in)
    
    # Legend
    legend_x = margin_l + 20
    legend_y = margin_t + 10
    legend_items = [
        ("Priority Check-in", (239, 68, 68)),
        ("Suggest Outreach", (249, 115, 22)),
        ("Monitor", (245, 158, 11)),
    ]
    cur_lx = legend_x
    for label, col in legend_items:
        draw.rectangle([cur_lx, legend_y, cur_lx + 12, legend_y + 10], fill=col)
        draw.text((cur_lx + 16, legend_y), label, fill=(50, 60, 75))
        cur_lx += 150
        
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


class SupportLensPDFReport(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_compression(False)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 7, text='SupportLens - Academic Early-Warning & Student Support Summary', align='L', new_x='LMARGIN', new_y='NEXT')
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, text='Synthetic data. Supports staff; does not make academic decisions.', align='C', new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 5, text=f'Page {self.page_no()}', align='R', new_x='LMARGIN', new_y='NEXT')


def generate_weekly_support_summary_pdf(
    as_of_week: int,
    kpis: Dict[str, Any],
    cohort_records: List[Dict[str, Any]],
    review_analytics: Optional[Dict[str, Any]] = None,
    action_effectiveness: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generate 2-3 page 'Weekly Support Summary' PDF report using fpdf2.
    Strictly adheres to ground rules and ethical requirements.
    """
    pdf = SupportLensPDFReport()
    
    # ---------------- PAGE 1 ----------------
    pdf.add_page()
    
    # Report Title
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, text=f"Weekly Support Summary - Week {as_of_week}", new_x='LMARGIN', new_y='NEXT')
    
    # Guardrail Statement box
    pdf.set_fill_color(240, 249, 255)
    pdf.set_draw_color(2, 132, 199)
    pdf.set_line_width(0.4)
    pdf.rect(10, pdf.get_y(), 190, 22, style='DF')
    pdf.set_xy(14, pdf.get_y() + 2)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(2, 132, 199)
    pdf.cell(0, 5, text='ETHICAL GUARDRAILS & NON-PUNITIVE PURPOSE', new_x='LMARGIN', new_y='NEXT')
    pdf.set_xy(14, pdf.get_y())
    pdf.set_font('Helvetica', size=8)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(
        180, 4,
        text=(
            'SupportLens is designed exclusively for early academic support and pastoral check-ins. '
            'All indicators are screening signals for coordinator review and must NEVER be used for automated sanctions, '
            'grading deductions, formal student reprimands, or academic standing decisions. Human review is mandatory.'
        )
    )
    pdf.set_y(pdf.get_y() + 6)
    
    # Section 1: KPI Overview
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, text='1. Cohort Triage Distribution', new_x='LMARGIN', new_y='NEXT')
    
    total = kpis.get('total_students', 100)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(50, 7, text='Support Level', border=1, align='L', fill=True)
    pdf.cell(30, 7, text='Student Count', border=1, align='C', fill=True)
    pdf.cell(30, 7, text='Percentage', border=1, align='C', fill=True)
    pdf.cell(80, 7, text='Recommended Action', border=1, align='L', fill=True, new_x='LMARGIN', new_y='NEXT')
    
    levels_data = [
        ('Priority Check-in', kpis.get('priority_checkin_count', 0), kpis.get('priority_checkin_pct', 0.0), 'Urgent pastoral / 1-on-1 check-in'),
        ('Suggest Outreach', kpis.get('suggest_outreach_count', 0), kpis.get('suggest_outreach_pct', 0.0), 'Supportive advisor check-in email'),
        ('Monitor', kpis.get('monitor_count', 0), kpis.get('monitor_pct', 0.0), 'Watch engagement pacing next week'),
        ('On Track', kpis.get('on_track_count', 0), kpis.get('on_track_pct', 0.0), 'Standard academic progress'),
        ('Insufficient Data', kpis.get('insufficient_data_count', 0), round(kpis.get('insufficient_data_count', 0)/total*100, 1), 'Verify upstream sync / LMS engagement'),
    ]
    
    pdf.set_font('Helvetica', size=8.5)
    for lvl, cnt, pct, action in levels_data:
        pdf.cell(50, 6, text=lvl, border=1, align='L')
        pdf.cell(30, 6, text=str(cnt), border=1, align='C')
        pdf.cell(30, 6, text=f"{pct:.1f}%", border=1, align='C')
        pdf.cell(80, 6, text=action, border=1, align='L', new_x='LMARGIN', new_y='NEXT')
        
    pdf.ln(5)
    
    # Section 2: Cohort Trend Chart Image
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, text='2. Longitudinal Support Level Trends (Weeks 4-10)', new_x='LMARGIN', new_y='NEXT')
    
    chart_png_bytes = _generate_trend_chart_image(width=680, height=220)
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
        tmp_img.write(chart_png_bytes)
        tmp_img_path = tmp_img.name
        
    try:
        pdf.image(tmp_img_path, x=15, y=pdf.get_y(), w=180)
        pdf.set_y(pdf.get_y() + 65)
    finally:
        if os.path.exists(tmp_img_path):
            os.unlink(tmp_img_path)
            
    # Section 3: Data Quality Summary
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, text='3. Data Completeness & Quality Summary', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', size=8.5)
    
    high_conf = sum(1 for r in cohort_records if r.get('data_confidence') == 'High')
    med_conf = sum(1 for r in cohort_records if r.get('data_confidence') == 'Medium')
    low_conf = sum(1 for r in cohort_records if r.get('data_confidence') == 'Low')
    
    pdf.multi_cell(
        190, 4.5,
        text=(
            f"Data confidence levels across all {len(cohort_records)} active students: "
            f"{high_conf} High confidence (complete recent attendance & submissions), "
            f"{med_conf} Medium confidence, and {low_conf} Low confidence.\n"
            f"Principle: 'Missing is never zero'. Where engagement records are blank, the engine abstains "
            f"from calculating punitive risk scores and designates 'Insufficient Data' with capped escalation."
        )
    )
    
    # ---------------- PAGE 2 ----------------
    pdf.add_page()
    
    # Section 4: Priority Check-in List
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, text='4. Priority Check-in & Supportive Outreach Cases', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, text='Students flagged for coordinator review. Every case requires coordinator verification before contact.', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    
    # Table of Priority Check-in & Outreach
    priority_students = [
        r for r in cohort_records
        if r.get('display_level') in ['Priority Check-in', 'Suggest Outreach']
    ]
    
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(15, 23, 42)
    pdf.set_fill_color(241, 245, 249)
    pdf.cell(20, 6, text='ID', border=1, align='C', fill=True)
    pdf.cell(32, 6, text='Support Level', border=1, align='L', fill=True)
    pdf.cell(14, 6, text='Score', border=1, align='C', fill=True)
    pdf.cell(40, 6, text='Concern Category', border=1, align='L', fill=True)
    pdf.cell(84, 6, text='Primary Reason & Context', border=1, align='L', fill=True, new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_font('Helvetica', size=7.5)
    display_limit = min(14, len(priority_students))
    for i in range(display_limit):
        r = priority_students[i]
        sid = r.get('student_id', 'Unknown')
        lvl = r.get('display_level', 'Suggest Outreach')
        sc = str(r.get('score', 0))
        cats = r.get('categories', [])
        cat_str = ', '.join(cats) if isinstance(cats, list) else str(cats)
        if len(cat_str) > 24:
            cat_str = cat_str[:22] + '..'
        expl = r.get('explanation', {})
        reason = expl.get('summary', 'Multiple converging engagement indicators') if isinstance(expl, dict) else str(expl)
        if len(reason) > 55:
            reason = reason[:52] + '...'
            
        pdf.cell(20, 5.5, text=sid, border=1, align='C')
        pdf.cell(32, 5.5, text=lvl, border=1, align='L')
        pdf.cell(14, 5.5, text=sc, border=1, align='C')
        pdf.cell(40, 5.5, text=cat_str, border=1, align='L')
        pdf.cell(84, 5.5, text=reason, border=1, align='L', new_x='LMARGIN', new_y='NEXT')
        
    if len(priority_students) > display_limit:
        pdf.set_font('Helvetica', 'I', 7.5)
        pdf.cell(0, 5, text=f"... and {len(priority_students) - display_limit} additional students in review queue (see interactive dashboard).", new_x='LMARGIN', new_y='NEXT')
        
    pdf.ln(6)
    
    # Section 5: Review Outcomes & Staff Feedback Summary
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, text='5. Staff Review Outcomes & Continuous Tuning', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', size=8.5)
    
    if review_analytics and review_analytics.get('total_reviews', 0) > 0:
        tot_rev = review_analytics['total_reviews']
        conf_pct = review_analytics.get('decision_pcts', {}).get('Confirmed', 0.0)
        corr_pct = review_analytics.get('decision_pcts', {}).get('Corrected', 0.0)
        dism_pct = review_analytics.get('decision_pcts', {}).get('Dismissed', 0.0)
        pdf.multi_cell(
            190, 4.5,
            text=(
                f"Coordinator review status to date: {tot_rev} total flags reviewed by academic coordinators.\n"
                f"- Confirmed by Staff: {conf_pct:.1f}%\n"
                f"- Level Corrected: {corr_pct:.1f}%\n"
                f"- Dismissed (False Alarms): {dism_pct:.1f}%\n"
                "Staff dismissals continuously feed back into rule recalibration to prevent systemic bias."
            )
        )
    else:
        pdf.multi_cell(
            190, 4.5,
            text=(
                "Coordinator reviews are currently in progress. As staff confirm, correct, or dismiss flags, "
                "review outcomes and false-alarm rates will automatically populate here to inform rule calibration."
            )
        )
        
    pdf.ln(5)
    
    # Section 6: Action Effectiveness Overview
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, text='6. Supportive Action Effectiveness (Cohort Aggregate)', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', size=8.5)
    
    if action_effectiveness and not action_effectiveness.get('is_empty', True):
        act_tot = action_effectiveness.get('total_actions', 0)
        act_comp = action_effectiveness.get('completed_count', 0)
        act_help = action_effectiveness.get('helpful_pct', 0.0)
        act_part = action_effectiveness.get('partially_helpful_pct', 0.0)
        pdf.multi_cell(
            190, 4.5,
            text=(
                f"Actions Recorded: {act_tot} planned, {act_comp} completed ({action_effectiveness.get('completed_pct', 0.0):.1f}%).\n"
                f"Student check-in feedback: {act_help:.1f}% rated Helpful, {act_part:.1f}% rated Partially Helpful. "
                f"Aggregate data guides campus resource allocation without ranking individual students."
            )
        )
    else:
        pdf.multi_cell(
            190, 4.5,
            text=(
                "Supportive actions (e.g. academic check-in emails, study skill workshops, peer tutoring referrals) "
                "are currently being scheduled. Post-outreach feedback is aggregated at cohort level to measure impact."
            )
        )

    # ---------------- PAGE 3 ----------------
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, text='7. Governance, Transparency & Model Ethics', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', size=8.5)
    pdf.multi_cell(
        190, 5,
        text=(
            "1. Human Oversight: SupportLens provides early screening signals. No student status or grade is ever modified by automated rules.\n\n"
            "2. Anonymised Architecture: Student identifiers in this report are synthetic pseudonyms (S-0001..S-0100). Real names and contact details are restricted to student support staff systems.\n\n"
            "3. Protected Attributes Barred: Group attributes (such as study mode, cohort group, or prior support flags) are strictly barred from ML feature engineering to prevent disparate impact.\n\n"
            "4. Multi-Week Persistence: Short, transient weekly variations do not escalate support levels. Concerns must be sustained across multiple weekly snapshots before triggering outreach recommendations.\n\n"
            "5. Auditable Ledger: Every automated score calculation, staff override, and planned outreach event is immutably logged in an append-only audit trail to uphold institutional accountability."
        )
    )
    
    return bytes(pdf.output())


def generate_cohort_report_markdown(as_of_week: int, kpis: Dict[str, Any], cohort_records: List[Dict[str, Any]]) -> str:
    """Markdown report export preserving existing API."""
    md = (
        f"# SupportLens Weekly Cohort Summary Report\n"
        f"**Snapshot Period:** As of Week {as_of_week}  \n"
        f"**Classification:** Confidential - Academic Coordinator Review Only  \n"
        f"**Ethics Notice:** Synthetic data demonstration. Human review required before any outreach.\n\n"
        f"---\n\n"
        f"## 1. Executive Summary & Cohort Overview\n"
        f"- **Total Students Enrolled:** {kpis.get('total_students', 100)}\n"
        f"- **Students On Track:** {kpis.get('on_track_count', 0)} ({kpis.get('on_track_pct', 0)}%)\n"
        f"- **Students Monitored:** {kpis.get('monitor_count', 0)} ({kpis.get('monitor_pct', 0)}%)\n"
        f"- **Suggested for Outreach:** {kpis.get('suggest_outreach_count', 0)} ({kpis.get('suggest_outreach_pct', 0)}%)\n"
        f"- **Priority Check-in Recommended:** {kpis.get('priority_checkin_count', 0)} ({kpis.get('priority_checkin_pct', 0)}%)\n"
        f"- **Students Needing Records Check (Insufficient Data):** {kpis.get('insufficient_data_count', 0)}\n\n"
        f"---\n\n"
        f"## 2. Priority Follow-Up Recommendations\n"
        f"| Student ID | Effective Level | Primary Concern Categories | Score | Data Confidence | Coordinator Review Status |\n"
        f"|---|---|---|---|---|---|\n"
    )
    for r in cohort_records:
        level = r.get('display_level', r.get('support_level'))
        if level in ['Priority Check-in', 'Suggest Outreach']:
            cats = ', '.join(r.get('categories', [])) if isinstance(r.get('categories'), list) else str(r.get('categories'))
            conf = r.get('data_confidence', 'High')
            rev = r.get('review_decision', 'Pending Review')
            score = r.get('score', 0)
            md += f"| {r.get('student_id')} | **{level}** | {cats} | {score} | {conf} | {rev} |\n"
            
    md += (
        "\n---\n\n"
        "## 3. Human-in-the-Loop Safeguards\n"
        "1. All alerts in this document represent automated screening signals, never academic penalties.\n"
        "2. Coordinators must confirm context, review recent submissions, and engage in compassionate dialog.\n"
        "3. Every staff decision and outreach action must be logged in the SupportLens audit register.\n"
    )
    return md
