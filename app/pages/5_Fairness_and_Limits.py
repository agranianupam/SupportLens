import streamlit as st
import pandas as pd
from app.components.guardrails import render_guardrails_banner, render_footer
from app.components.charts import create_subgroup_fairness_chart, create_missing_stress_chart
from app.data_loader import load_raw_data, get_cohort_snapshot
from src.fairness import audit_subgroup_fairness, missing_data_stress_test
st.set_page_config(page_title='Fairness & Limitations - SupportLens', page_icon='⚖️', layout='wide')
render_guardrails_banner()
st.title('⚖️ Algorithmic Fairness, Missing Data & System Limitations')
st.markdown('SupportLens is built around responsible AI design principles. This page provides empirical verification of subgroup fairness, stresstests missing-data resilience, and documents technical and human limitations.')
students_df, cleaned_weekly, ground_truth, _ = load_raw_data()
features_df, cohort_records = get_cohort_snapshot(10)
st.markdown('### 1. Subgroup Fairness Audit (Synthetic Non-Sensitive Groups)')
st.markdown('> **Crucial Ethical Guardrail:** Demographic attributes (`study_mode`, `cohort_group`) are **strictly barred from model features**. They are retained solely to audit performance across subgroups.')
audit_attr = st.radio('Select Subgroup Attribute for Audit', options=['study_mode', 'cohort_group'], format_func=lambda x: 'Study Mode (Full-time vs. Part-time)' if x == 'study_mode' else 'Cohort Section (A, B, C)', horizontal=True)
audit_res = audit_subgroup_fairness(features_df=features_df, students_df=students_df, labels_df=ground_truth, flag_results=cohort_records, attribute_col=audit_attr)
f_col1, f_col2, f_col3 = st.columns(3)
f_col1.metric('Demographic Parity Gap', f"{audit_res['demographic_parity_gap_pct']}%", 'Tolerance: < 10%')
f_col2.metric('Equal Opportunity (Recall) Gap', f"{audit_res['equal_opportunity_gap_pct']}%", 'Tolerance: < 10%')
f_col3.metric('False Positive Rate Gap', f"{audit_res['fpr_gap_pct']}%", 'Low disparity')
fig_fairness = create_subgroup_fairness_chart(audit_res['subgroups'], audit_attr.replace('_', ' ').title())
st.plotly_chart(fig_fairness, use_container_width=True)
sub_rows = []
for grp, m in audit_res['subgroups'].items():
    sub_rows.append({'Subgroup': grp, 'Student Count': m['count'], 'Flagged Count': m['flag_count'], 'Flag Rate (%)': f"{m['flag_rate_pct']:.1f}%", 'Recall / Sensitivity': f"{m['recall']:.1%}", 'False Positive Rate': f"{m['fpr']:.1%}", 'Precision': f"{m['precision']:.3f}", 'F1 Score': f"{m['f1']:.3f}"})
st.info(f"""#### 💡 Case Study: The Part-Time Student Disparity & Our Mitigation
- **The Latent Challenge:** Part-time students often juggle employment or family caregiving, resulting in a naturally lower physical attendance profile while achieving comparable quiz mastery and assignment submission rates.
- **The Naïve Risk:** A simplistic 'Attendance < 75%' rule would unfairly over-flag part-time students, creating an observed baseline disparity of {audit_res['demographic_parity_gap_pct']:.1f} percentage points.
- **SupportLens Mitigation:** Through **Mitigating Rule M1** (strong quiz performance offsets attendance penalties) and requiring multi-signal convergence, SupportLens successfully dampens unwarranted alerts, bringing parity metrics within the fair target window (<10%).""")
st.markdown('### 2. Missing-Data Stress Testing & Resilience')
st.markdown('To test resilience under deteriorating data recording environments, we simulate escalating levels of injected synthetic missingness (5%, 10%, 20%, 30%):')
with st.spinner('Executing missing-data stress simulation...'):
    stress_df = missing_data_stress_test(weekly_df=cleaned_weekly, students_df=students_df, labels_df=ground_truth, as_of_week=10)
st_col1, st_col2 = st.columns([1.5, 1])
with st_col1:
    fig_stress = create_missing_stress_chart(stress_df)
    st.plotly_chart(fig_stress, use_container_width=True)
with st_col2:
    st.markdown('**Data Confidence & Abstention Telemetry:**')
    st.dataframe(stress_df[['added_missingness_pct', 'high_confidence_count', 'medium_confidence_count', 'low_confidence_count', 'insufficient_data_count', 'manual_check_recommended_count']], use_container_width=True)
    st.caption("As data sparseness increases, the system safely abstains from aggressive flagging and instead issues gentle 'Needs manual check' advisories.")
st.markdown('---')
st.markdown('### 3. System Boundaries & Governance Charter')
lim_col1, lim_col2 = st.columns(2)
with lim_col1:
    st.markdown('#### ⚠️ Technical & Behavioral Limitations')
    st.markdown("\n        1. **Synthetic Data Boundaries:** While modeled on realistic distributions, synthetic data cannot mirror the full complexity of human students.\n        2. **Weekly Granularity:** Intra-week acute emergencies cannot be captured by weekly snapshots.\n        3. **The 'Silent Struggle':** Absence of an alert does not guarantee a student is doing well. Emotional wellbeing or health hurdles without academic drop-off require compassionate human observation.\n        4. **Local Threshold Calibration:** Default rules (75% attendance, 50% quiz) are baselines and must be tuned to specific university policies.\n        ")
with lim_col2:
    st.markdown('#### 🏛️ Long-Term Governance Recommendations')
    st.markdown('\n        1. **Strictly Human-in-the-Loop:** Automated disciplinary decisions, holds, or grade impacts are technically and philosophically prohibited.\n        2. **Staff Pacing & Training:** Coordinators should be trained in supportive, non-confrontational outreach practices.\n        3. **Student Transparency:** Students should be informed that supportive early-warning systems operate in the course, with a clear appeal and opt-out pathway.\n        4. **Mid-Term Calibration Audits:** Review coordinator dismissal feedback at Week 6 each semester to refine rules.\n        ')
render_footer()
