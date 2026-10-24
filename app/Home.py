import streamlit as st
import pandas as pd
from app.components.guardrails import render_guardrails_banner, render_footer
from app.components.badges import support_level_badge, confidence_badge
from app.components.charts import create_cohort_level_donut, create_cohort_weekly_trends
from app.data_loader import load_raw_data, get_cohort_snapshot, get_review_store
st.set_page_config(page_title='SupportLens - Academic Early-Warning Dashboard', page_icon='🎓', layout='wide', initial_sidebar_state='expanded')
render_guardrails_banner()
st.title('🎓 SupportLens')
st.subheader('Transparent, Human-in-the-Loop Early-Warning Academic Support Dashboard')
st.markdown('\n    **SupportLens** enables university course coordinators to identify students who may benefit from proactive, \n    compassionate academic guidance before small hurdles compound into course withdrawal. \n    Operating on interpretable rules cross-checked by transparent machine learning, \n    **the system never makes automated penalties, grades, or disciplinary decisions.** \n    Human review is mandatory, every flag is explainable in plain English, and coordinator decisions always supersede system outputs.\n    ')
st.sidebar.header('⚙️ Global Navigation & Filters')
as_of_week = st.sidebar.slider('📅 Snapshot Week (Time-Travel)', min_value=4, max_value=12, value=10, step=1)
st.sidebar.caption('Computed strictly as of the selected week with zero look-ahead bias.')
students_df, cleaned_weekly, ground_truth, quality_report = load_raw_data()
features_df, cohort_records = get_cohort_snapshot(as_of_week)
store = get_review_store()
level_counts = {'On Track': sum((1 for r in cohort_records if r['display_level'] == 'On Track')), 'Monitor': sum((1 for r in cohort_records if r['display_level'] == 'Monitor')), 'Suggest Outreach': sum((1 for r in cohort_records if r['display_level'] == 'Suggest Outreach')), 'Priority Check-in': sum((1 for r in cohort_records if r['display_level'] == 'Priority Check-in')), 'Insufficient Data': sum((1 for r in cohort_records if r['display_level'] == 'Insufficient Data'))}
needs_data_check_count = sum((1 for r in cohort_records if r.get('needs_manual_check', False)))
reviewed_count = sum((1 for r in cohort_records if r.get('is_reviewed', False)))
st.markdown('### 📊 Cohort Pulse (As of Week ' + str(as_of_week) + ')')
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Total Cohort Roster', f'{len(students_df)} students', '100% Synthetic')
col2.metric('🟢 On Track', f"{level_counts['On Track']}", f"{level_counts['On Track']}% of class")
col3.metric('🟠 Suggest Outreach', f"{level_counts['Suggest Outreach']}", 'Early assistance')
col4.metric('🔴 Priority Check-in', f"{level_counts['Priority Check-in']}", 'Timely 1-on-1')
col5.metric('⚪ Needs Data Check', f'{needs_data_check_count}', 'Low confidence / sparse')
st.markdown('---')
c_chart1, c_chart2 = st.columns([1, 2])
with c_chart1:
    fig_donut = create_cohort_level_donut(level_counts)
    st.plotly_chart(fig_donut, use_container_width=True)
with c_chart2:
    fig_trends = create_cohort_weekly_trends(cleaned_weekly, as_of_week)
    st.plotly_chart(fig_trends, use_container_width=True)
st.markdown('---')
st.markdown('### 🧹 Data Quality & Ingestion Telemetry')
st.markdown('SupportLens continuously verifies data integrity upon ingestion. Invalid values are transparently converted to missing values and tracked-**students are never silently dropped.**')
dq_col1, dq_col2, dq_col3, dq_col4 = st.columns(4)
dq_col1.metric('Overall Completeness', f"{quality_report['overall_data_completeness_pct']}%", 'Healthy threshold')
dq_col2.metric('Duplicates Sanitized', f"{quality_report['duplicates_removed']} rows", 'Deduplicated')
dq_col3.metric('Anomalies Corrected', f"{quality_report['invalid_attendance_corrected'] + quality_report['invalid_quiz_corrected']} values", 'Clamped to NaN')
dq_col4.metric('Coordinator Reviews Logged', f'{reviewed_count} records', 'Human-in-the-loop')
st.markdown('---')
st.markdown('### 🧭 How to Use SupportLens in 4 Compassionate Steps')
step1, step2, step3, step4 = st.columns(4)
with step1:
    st.info('**1. Explore Cohort**\n\nReview cohort-wide engagement trajectories and filter by concern category on the **Cohort Dashboard**.')
with step2:
    st.info("**2. Investigate Signals**\n\nOpen **Student Detail** to inspect plain-English explanations, rule vs. ML agreement, and 'What's Going Well'.")
with step3:
    st.info('**3. Review & Correct**\n\nConfirm, adjust, or dismiss flags in the **Staff Review** panel. Human coordinator judgment always overrides the system.')
with step4:
    st.info('**4. Supportive Outreach**\n\nSelect tailored supportive action templates (tutoring, extension, study guide) and log all actions in the **Audit Log**.')
render_footer()
