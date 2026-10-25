import sys
from pathlib import Path

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from app.components.guardrails import render_guardrails_banner, render_footer
from app.components.badges import support_level_badge, confidence_badge
from app.components.charts import create_cohort_level_donut, create_cohort_weekly_trends
from app.data_loader import load_raw_data, get_cohort_snapshot, get_review_store
st.set_page_config(page_title='SupportLens - Academic Early-Warning Dashboard', page_icon='🎓', layout='wide', initial_sidebar_state='expanded')
st.title('🎓 SupportLens')
st.subheader('Transparent, Human-in-the-Loop Early-Warning Academic Support Dashboard')

st.sidebar.header('⚙️ Global Navigation & Filters')
demo_mode = st.sidebar.toggle('🎭 Demo Mode', value=True, help='Activates guided walkthrough buttons and archetype inspection')
default_week = int(st.session_state.get('snapshot_week', 10))
as_of_week = st.sidebar.slider('📅 Snapshot Week (Time-Travel)', min_value=4, max_value=12, value=default_week, step=1)
st.session_state['snapshot_week'] = as_of_week
st.sidebar.caption('Computed strictly as of the selected week with zero look-ahead bias.')

students_df, cleaned_weekly, ground_truth, quality_report = load_raw_data()
features_df, cohort_records = get_cohort_snapshot(as_of_week)
store = get_review_store()

if demo_mode:
    from src.archetypes import select_dynamic_archetypes
    archetypes = select_dynamic_archetypes(as_of_week, features_df, cohort_records)

    st.markdown('### 🎬 Guided Demo: Key Student Archetypes')
    st.caption('Explore curated student profiles demonstrating core ethical safeguard behaviors with a single click.')
    d_col1, d_col2, d_col3, d_col4 = st.columns(4)

    with d_col1:
        st.markdown('**1. Gradual Decliner**')
        arch1 = archetypes.get('decliner')
        if arch1:
            st.caption(f"📌 {arch1['badge']}")
            st.write(arch1['description'])
            st.markdown(f"**Student:** `{arch1['student_id']}`")
            if st.button(arch1['inspect_label'], use_container_width=True, key=f"demo_{arch1['student_id']}_{as_of_week}"):
                st.session_state['selected_student_id'] = arch1['student_id']
                st.session_state['snapshot_week'] = as_of_week
                st.switch_page('pages/2_Student_Detail.py')
        else:
            st.caption(f"Week {as_of_week}")
            st.info("No clear match yet.")
            st.button("No Match Available", disabled=True, use_container_width=True, key=f"demo_none_decl_{as_of_week}")

    with d_col2:
        st.markdown('**2. Strong-but-Irregular**')
        arch2 = archetypes.get('strong_irregular')
        if arch2:
            st.caption(f"📌 {arch2['badge']}")
            st.write(arch2['description'])
            st.markdown(f"**Student:** `{arch2['student_id']}`")
            if st.button(arch2['inspect_label'], use_container_width=True, key=f"demo_{arch2['student_id']}_{as_of_week}"):
                st.session_state['selected_student_id'] = arch2['student_id']
                st.session_state['snapshot_week'] = as_of_week
                st.switch_page('pages/2_Student_Detail.py')
        else:
            st.caption(f"Week {as_of_week}")
            st.info("No clear match yet.")
            st.button("No Match Available", disabled=True, use_container_width=True, key=f"demo_none_si_{as_of_week}")

    with d_col3:
        st.markdown('**3. Data-Gap Case**')
        arch3 = archetypes.get('data_gap')
        if arch3:
            st.caption(f"📌 {arch3['badge']}")
            st.write(arch3['description'])
            st.markdown(f"**Student:** `{arch3['student_id']}`")
            if st.button(arch3['inspect_label'], use_container_width=True, key=f"demo_{arch3['student_id']}_{as_of_week}"):
                st.session_state['selected_student_id'] = arch3['student_id']
                st.session_state['snapshot_week'] = as_of_week
                st.switch_page('pages/2_Student_Detail.py')
        else:
            st.caption(f"Week {as_of_week}")
            st.info("No clear match yet.")
            st.button("No Match Available", disabled=True, use_container_width=True, key=f"demo_none_dg_{as_of_week}")

    with d_col4:
        st.markdown('**4. Recovering Student**')
        arch4 = archetypes.get('recovering')
        if arch4:
            st.caption(f"📌 {arch4['badge']}")
            st.write(arch4['description'])
            st.markdown(f"**Student:** `{arch4['student_id']}`")
            if st.button(arch4['inspect_label'], use_container_width=True, key=f"demo_{arch4['student_id']}_{as_of_week}"):
                st.session_state['selected_student_id'] = arch4['student_id']
                st.session_state['snapshot_week'] = as_of_week
                st.switch_page('pages/2_Student_Detail.py')
        else:
            st.caption(f"Week {as_of_week}")
            st.info("No clear match yet.")
            st.button("No Match Available", disabled=True, use_container_width=True, key=f"demo_none_rec_{as_of_week}")
            
    with st.expander('🔄 Reset Demo Data (Presentation Control)', expanded=False):
        st.markdown('Clears demo staff reviews, actions, and feedback. **The audit log remains append-only**: a reset marker event will be permanently recorded.')
        confirm_reset = st.checkbox('Confirm demo data reset for presentation', key='confirm_demo_reset')
        if st.button('⚠️ Reset Demo Reviews & Actions', disabled=not confirm_reset, type='primary', key='btn_reset_demo'):
            store.reset_demo_data(actor_code='STAFF-DEMO')
            st.success('Demo data reset completed. A DEMO_RESET event was written to the immutable audit log.')
            st.rerun()

    st.markdown('---')

level_counts = {
    'On Track': sum(1 for r in cohort_records if r['display_level'] == 'On Track'),
    'Monitor': sum(1 for r in cohort_records if r['display_level'] == 'Monitor'),
    'Suggest Outreach': sum(1 for r in cohort_records if r['display_level'] == 'Suggest Outreach'),
    'Priority Check-in': sum(1 for r in cohort_records if r['display_level'] == 'Priority Check-in'),
    'Insufficient Data': sum(1 for r in cohort_records if r['display_level'] == 'Insufficient Data'),
}
needs_data_check_count = sum(1 for r in cohort_records if r.get('needs_manual_check', False))
reviewed_count = sum(1 for r in cohort_records if r.get('is_reviewed', False))

st.markdown('### 📊 Cohort Pulse (As of Week ' + str(as_of_week) + ')')
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Total Cohort Roster', f'{len(students_df)} students', '100% Synthetic', help='Total enrolled students in simulated cohort')
col2.metric('🟢 On Track', f"{level_counts['On Track']}", f"{level_counts['On Track']}% of class", help='Students demonstrating consistent academic engagement and attendance')
col3.metric('🟠 Suggest Outreach', f"{level_counts['Suggest Outreach']}", 'Early assistance', help='Students with 2+ converging signals where proactive advisor email may help')
col4.metric('🔴 Priority Check-in', f"{level_counts['Priority Check-in']}", 'Timely 1-on-1', help='Students with acute multi-week drops recommended for urgent check-in')
col5.metric('⚪ Needs Data Check', f'{needs_data_check_count}', 'Low confidence / sparse', help='Students with low data confidence requiring LMS/attendance record verification')
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
dq_col1.metric('Overall Completeness', f"{quality_report['overall_data_completeness_pct']}%", 'Healthy threshold', help='Percentage of non-missing expected weekly attendance, quiz, and assignment records')
dq_col2.metric('Duplicates Sanitized', f"{quality_report['duplicates_removed']} rows", 'Deduplicated', help='Duplicate weekly submission records deduplicated during automated ingestion')
dq_col3.metric('Anomalies Corrected', f"{quality_report['invalid_attendance_corrected'] + quality_report['invalid_quiz_corrected']} values", 'Clamped to NaN', help='Out-of-range attendance percentages or negative quiz scores safely converted to missing')
dq_col4.metric('Coordinator Reviews Logged', f'{reviewed_count} records', 'Human-in-the-loop', help='Number of automated early-warning flags reviewed by university coordinators')
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

st.markdown('---')
render_guardrails_banner()
render_footer()

