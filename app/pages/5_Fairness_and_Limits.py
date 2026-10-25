import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from app.components.guardrails import render_guardrails_banner, render_footer
from app.components.charts import (
    create_subgroup_fairness_chart,
    create_missing_stress_chart,
    create_insufficient_data_growth_chart,
)
from app.data_loader import load_raw_data, get_cohort_snapshot
from src.fairness import audit_subgroup_fairness
from src.evaluation import missingness_stress_test
st.set_page_config(page_title='Fairness & Limitations - SupportLens', page_icon='⚖️', layout='wide')
st.title('⚖️ Algorithmic Fairness, Missing Data & System Limitations')
st.markdown('SupportLens is built around responsible AI design principles. This page provides empirical verification of subgroup fairness, stresstests missing-data resilience, and documents technical and human limitations.')
students_df, cleaned_weekly, ground_truth, _ = load_raw_data()
features_df, cohort_records = get_cohort_snapshot(10)
st.markdown('### 1. Subgroup Fairness Audit (Synthetic Non-Sensitive Groups)')
st.markdown('> **Crucial Ethical Guardrail:** Group attributes (`cohort_group`, `prior_support_flag`) are **strictly barred from model features**. They are retained solely to audit performance across subgroups.')
audit_attr = st.radio('Select Subgroup Attribute for Audit', options=['cohort_group', 'prior_support_flag'], format_func=lambda x: 'Cohort Section (Sections A, B, C)' if x == 'cohort_group' else 'Prior Academic Support Record', horizontal=True)
audit_res = audit_subgroup_fairness(features_df=features_df, students_df=students_df, labels_df=ground_truth, flag_results=cohort_records, attribute_col=audit_attr)
f_col1, f_col2, f_col3 = st.columns(3)
f_col1.metric('Demographic Parity Gap', f"{audit_res['demographic_parity_gap_pct']}%", 'Tolerance: < 10%')
f_col2.metric('Equal Opportunity (Recall) Gap', f"{audit_res['equal_opportunity_gap_pct']}%", 'Tolerance: < 10%')
f_col3.metric('False Positive Rate Gap', f"{audit_res['fpr_gap_pct']}%", 'Low disparity')
fig_fairness = create_subgroup_fairness_chart(audit_res['subgroups'], audit_attr.replace('_', ' ').title())
st.plotly_chart(fig_fairness, use_container_width=True)
sub_rows = []
for grp, m in audit_res['subgroups'].items():
    grp_label = ("Prior Support" if str(grp).lower() in ['true', '1'] else "First-Time Cohort") if audit_attr == 'prior_support_flag' else str(grp)
    sub_rows.append({'Subgroup': grp_label, 'Student Count': m['count'], 'Flagged Count': m['flag_count'], 'Flag Rate (%)': f"{m['flag_rate_pct']:.1f}%", 'Recall / Sensitivity': f"{m['recall']:.1%}", 'False Positive Rate': f"{m['fpr']:.1%}", 'Precision': f"{m['precision']:.3f}", 'F1 Score': f"{m['f1']:.3f}"})
st.dataframe(pd.DataFrame(sub_rows), use_container_width=True, hide_index=True)
st.info(f"""#### 💡 Case Study: Cohort Section Parity & Mitigating Rule Dampening
- **The Operational Challenge:** Course sections (A, B, and C) naturally vary in meeting times, laboratory schedules, and instructor pacing. A rigid or single-signal early-warning rule risks generating artificial disparities across lecture sections.
- **The Naïve Risk:** A simplistic 'Attendance < 75% alone' rule produces a wide flag-rate disparity across sections, disproportionately alarming students whose attendance was affected by schedule conflicts despite strong quiz performance.
- **SupportLens Mitigation:** Through **Mitigating Rule M1** (strong quiz mastery offsets raw attendance drops) and **Rule M2** (rewarding positive multi-week trajectories), SupportLens protects autonomous learners and maintains balanced parity across all course sections.""")
st.markdown('### 2. Missing-Data Stress Testing & Resilience')
st.markdown('To test resilience under deteriorating data recording environments, we simulate escalating levels of injected synthetic missingness (5%, 10%, 20%, 30%) across multiple random seeds:')

@st.cache_data
def get_cached_stress_test():
    return missingness_stress_test(
        weekly_df=cleaned_weekly,
        students_df=students_df,
        labels_df=ground_truth,
        as_of_week=10,
        levels=[0.05, 0.10, 0.20, 0.30],
        seeds=3,
    )

col_str_btn, col_str_info = st.columns([1, 3])
with col_str_btn:
    trigger_stress = st.button("▶️ Run Stress Test Simulation", key="btn_run_stress", type="primary")

if trigger_stress:
    st.session_state['run_stress'] = True

if st.session_state.get('run_stress', False):
    with st.spinner('Simulating data degradation across 5% to 30% missingness levels...'):
        stress_res = get_cached_stress_test()
    stress_df = stress_res['stress_df']
    stress_takeaway = stress_res['takeaway']

    st_col1, st_col2 = st.columns(2)
    with st_col1:
        fig_stress = create_missing_stress_chart(stress_df)
        st.plotly_chart(fig_stress, use_container_width=True)
    with st_col2:
        fig_insuff = create_insufficient_data_growth_chart(stress_df)
        st.plotly_chart(fig_insuff, use_container_width=True)

    st.markdown('**Stress Test Performance & Telemetry Table:**')
    st.dataframe(stress_df, use_container_width=True, hide_index=True)
    st.success(f"🛡️ **Empirical Takeaway:** {stress_takeaway}")
else:
    st.info("💡 Missing-data stress testing injects synthetic data corruption from 5% to 30% to demonstrate that SupportLens abstains ('Insufficient Data') rather than inventing false alarms. Click **'Run Stress Test Simulation'** above to execute this experiment on demand.")

st.markdown('---')
st.markdown('### 3. System Boundaries & Governance Charter')
lim_col1, lim_col2 = st.columns(2)
with lim_col1:
    st.markdown('#### ⚠️ Technical & Behavioral Limitations')
    st.markdown("\n        1. **Synthetic Data Boundaries:** While modeled on realistic distributions, synthetic data cannot mirror the full complexity of human students.\n        2. **Weekly Granularity:** Intra-week acute emergencies cannot be captured by weekly snapshots.\n        3. **The 'Silent Struggle':** Absence of an alert does not guarantee a student is doing well. Emotional wellbeing or health hurdles without academic drop-off require compassionate human observation.\n        4. **Local Threshold Calibration:** Default rules (75% attendance, 50% quiz) are baselines and must be tuned to specific university policies.\n        ")
with lim_col2:
    st.markdown('#### 🏛️ Long-Term Governance Recommendations')
    st.markdown('\n        1. **Strictly Human-in-the-Loop:** Automated disciplinary decisions, holds, or grade impacts are technically and philosophically prohibited.\n        2. **Staff Pacing & Training:** Coordinators should be trained in supportive, non-confrontational outreach practices.\n        3. **Student Transparency:** Students should be informed that supportive early-warning systems operate in the course, with a clear appeal and opt-out pathway.\n        4. **Mid-Term Calibration Audits:** Review coordinator dismissal feedback at Week 6 each semester to refine rules.\n        ')
render_guardrails_banner()
render_footer()
