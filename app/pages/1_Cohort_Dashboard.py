import streamlit as st
import pandas as pd
from app.components.guardrails import render_guardrails_banner, render_footer
from app.components.badges import support_level_badge, confidence_badge, agreement_badge, review_status_badge
from app.data_loader import load_raw_data, get_cohort_snapshot, get_review_store
from src.export import generate_weekly_summary_csv, generate_cohort_report_markdown
st.set_page_config(page_title='Cohort Dashboard - SupportLens', page_icon='👥', layout='wide')
render_guardrails_banner()
st.title('👥 Cohort Overview & Support Triage')
st.markdown('Filter, sort, and inspect all 100 students as of the current snapshot week.')
st.sidebar.header('🔍 Filters')
as_of_week = st.sidebar.slider('📅 Snapshot Week', min_value=4, max_value=12, value=10, step=1)
level_filter = st.sidebar.multiselect('Support Level', options=['Priority Check-in', 'Suggest Outreach', 'Monitor', 'On Track', 'Insufficient Data'], default=['Priority Check-in', 'Suggest Outreach', 'Monitor', 'On Track', 'Insufficient Data'])
conf_filter = st.sidebar.multiselect('Data Confidence', options=['High', 'Medium', 'Low'], default=['High', 'Medium', 'Low'])
search_id = st.sidebar.text_input('🔎 Search Student ID', placeholder='e.g. S-0042').strip().upper()
with st.expander('🎛️ Coordinator What-If Threshold Tuning (Simulation Panel)', expanded=False):
    st.markdown('Simulate how adjusting core thresholds impacts student flag counts across the cohort in real-time. Simulations run entirely in-memory and will **not** alter production configuration unless saved.')
    w_col1, w_col2, w_col3 = st.columns(3)
    with w_col1:
        sim_att_cutoff = st.slider('Attendance Cut-off (Rule A1)', 50.0, 90.0, 75.0, 1.0)
    with w_col2:
        sim_miss_cutoff = st.slider('Missing Count Cut-off (Rule S1)', 1, 4, 2, 1)
    with w_col3:
        sim_quiz_cutoff = st.slider('Quiz Check-in Cut-off (Rule Q1)', 30.0, 75.0, 50.0, 5.0)
    sim_custom = {'attendance': {'low_att_cutoff': sim_att_cutoff}, 'submission': {'missing_count_cutoff': sim_miss_cutoff}, 'quiz': {'low_quiz_cutoff': sim_quiz_cutoff}}
features_df, cohort_records = get_cohort_snapshot(as_of_week, custom_thresholds=sim_custom)
filtered_records = [r for r in cohort_records if r['display_level'] in level_filter and r['data_confidence'] in conf_filter and (not search_id or search_id in r['student_id'])]
st.markdown(f'**Showing {len(filtered_records)} of {len(cohort_records)} students**')
table_rows = []
for r in filtered_records:
    s_id = r['student_id']
    level_b = support_level_badge(r['display_level'])
    conf_b = confidence_badge(r['data_confidence'], r['data_confidence_score'])
    ag_b = agreement_badge(r['agreement'])
    rev_b = review_status_badge(r['review_decision'])
    cats = ', '.join(r['categories'])
    table_rows.append({'Student ID': s_id, 'Effective Level': level_b, 'Concern Categories': cats, 'Score': r['score'], 'ML Probability': f"{r['ml_probability']:.2f}", 'Rule-vs-ML Agreement': ag_b, 'Data Confidence': conf_b, 'Review Status': rev_b})
df_display = pd.DataFrame(table_rows)
if len(df_display) > 0:
    st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
else:
    st.info('No students match the current filter selection.')
st.markdown('---')
st.markdown('### 📥 Export Anonymised Cohort Artifacts')
ex_col1, ex_col2 = st.columns(2)
with ex_col1:
    csv_data = generate_weekly_summary_csv(filtered_records)
    st.download_button(label='📄 Download Anonymised Weekly Summary (CSV)', data=csv_data, file_name=f'supportlens_cohort_week_{as_of_week}.csv', mime='text/csv', use_container_width=True)
with ex_col2:
    kpi_dict = {'total_students': len(cohort_records), 'on_track_count': sum((1 for r in cohort_records if r['display_level'] == 'On Track')), 'on_track_pct': round(sum((1 for r in cohort_records if r['display_level'] == 'On Track')) / len(cohort_records) * 100, 1), 'monitor_count': sum((1 for r in cohort_records if r['display_level'] == 'Monitor')), 'monitor_pct': round(sum((1 for r in cohort_records if r['display_level'] == 'Monitor')) / len(cohort_records) * 100, 1), 'suggest_outreach_count': sum((1 for r in cohort_records if r['display_level'] == 'Suggest Outreach')), 'suggest_outreach_pct': round(sum((1 for r in cohort_records if r['display_level'] == 'Suggest Outreach')) / len(cohort_records) * 100, 1), 'priority_checkin_count': sum((1 for r in cohort_records if r['display_level'] == 'Priority Check-in')), 'priority_checkin_pct': round(sum((1 for r in cohort_records if r['display_level'] == 'Priority Check-in')) / len(cohort_records) * 100, 1), 'insufficient_data_count': sum((1 for r in cohort_records if r['display_level'] == 'Insufficient Data'))}
    md_report = generate_cohort_report_markdown(as_of_week, kpi_dict, filtered_records)
    st.download_button(label='📑 Download Coordinator Summary Report (Markdown)', data=md_report, file_name=f'supportlens_report_week_{as_of_week}.md', mime='text/markdown', use_container_width=True)
render_footer()
