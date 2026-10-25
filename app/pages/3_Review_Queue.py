import streamlit as st
import pandas as pd
from app.components.guardrails import render_guardrails_banner, render_footer
from app.components.badges import support_level_badge, confidence_badge, agreement_badge, review_status_badge
from app.data_loader import load_raw_data, get_cohort_snapshot, get_review_store
st.set_page_config(page_title='Review Queue - SupportLens', page_icon='📋', layout='wide')
render_guardrails_banner()
st.title('📋 Coordinator Review Queue & Action Tracker')
st.markdown('Prioritised action queue to ensure coordinator time is directed where supportive outreach is most urgently needed. Flags are prioritized by urgency, rule-vs-ML disagreements, and low data confidence.')
as_of_week = st.sidebar.slider('📅 Snapshot Week', min_value=4, max_value=12, value=10, step=1)
store = get_review_store()
features_df, cohort_records = get_cohort_snapshot(as_of_week)

def get_priority_weight(rec: dict) -> int:
    lvl = rec.get('display_level')
    weight = 0
    if lvl == 'Priority Check-in':
        weight += 100
    elif lvl == 'Suggest Outreach':
        weight += 60
    elif lvl == 'Monitor':
        weight += 20
    elif lvl == 'Insufficient Data':
        weight += 40
    if rec.get('agreement', {}).get('type') in ['rules_only', 'ml_only']:
        weight += 30
    if rec.get('data_confidence') == 'Low':
        weight += 25
    if not rec.get('is_reviewed', False):
        weight += 10
    return weight
sorted_queue = sorted(cohort_records, key=get_priority_weight, reverse=True)
disagreement_records = [
    r for r in cohort_records if r.get('agreement', {}).get('type') in ['rules_only', 'ml_only']
]

tab_queue, tab_disagreements, tab_actions, tab_analytics = st.tabs([
    '🚀 Prioritised Triage Queue',
    f'⚠️ Worth a Second Look ({len(disagreement_records)})',
    '📌 Action Tracker',
    '🔄 Feedback Loop Analytics',
])

with tab_queue:
    show_unreviewed_only = st.checkbox('Show unreviewed students only', value=True)
    if show_unreviewed_only:
        display_queue = [r for r in sorted_queue if not r.get('is_reviewed', False)]
    else:
        display_queue = sorted_queue
    st.markdown(f'**{len(display_queue)} students in triage queue**')
    for r in display_queue[:15]:
        s_id = r['student_id']
        with st.expander(f"{r['display_level']} • {s_id} (Score: {r['score']}, Confidence: {r['data_confidence']})"):
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                st.markdown(f"**Level:** {support_level_badge(r['display_level'])}", unsafe_allow_html=True)
                st.markdown(f"**Review:** {review_status_badge(r['review_decision'])}", unsafe_allow_html=True)
                st.markdown(f"**Categories:** {', '.join(r['categories'])}")
            with c2:
                st.markdown(f"**Data Confidence:** {confidence_badge(r['data_confidence'], r['data_confidence_score'])}", unsafe_allow_html=True)
                st.markdown(f"**Alignment:** {agreement_badge(r['agreement'])}", unsafe_allow_html=True)
                st.markdown(f"**ML Probability:** `{r['ml_probability']:.1%}`")
            with c3:
                st.caption(r['explanation']['summary'])
            st.markdown('---')
            q_col1, q_col2, q_col3 = st.columns([1, 1, 2])
            with q_col1:
                if st.button('✓ Quick Confirm', key=f'conf_{s_id}'):
                    store.record_review(r['flag_id'], s_id, 'STAFF-01', 'Confirmed')
                    st.success(f'{s_id} confirmed!')
                    st.rerun()
            with q_col2:
                if st.button('✕ Quick Dismiss (False Alarm)', key=f'dism_{s_id}'):
                    store.record_review(r['flag_id'], s_id, 'STAFF-01', 'Dismissed', reason_code='Known circumstance', reason_note='Quick dismissed via review queue')
                    st.info(f'{s_id} dismissed.')
                    st.rerun()
            with q_col3:
                st.caption('For full inspection and custom supportive action plans, open **Student Detail**.')

with tab_disagreements:
    st.markdown('### ⚠️ Worth a Second Look: Rule-vs-ML Disagreements')
    st.info(
        "ℹ️ **Architectural Note:** The interpretable rule engine drives the displayed flag; "
        "machine learning acts strictly as an auxiliary cross-check to illuminate subtle patterns "
        "or potential false positives."
    )
    if disagreement_records:
        st.markdown(f"**{len(disagreement_records)} students with rule-vs-ML misalignment:**")
        for r in disagreement_records:
            s_id = r['student_id']
            ag = r.get('agreement', {})
            with st.expander(f"{r['student_id']} — {ag.get('badge')} (Score: {r['score']}, ML: {r['ml_probability']:.1%})"):
                d_c1, d_c2 = st.columns([1, 1])
                with d_c1:
                    st.markdown(f"**Rule Level:** {support_level_badge(r['display_level'])}", unsafe_allow_html=True)
                    st.markdown(f"**Alignment:** {agreement_badge(ag)}", unsafe_allow_html=True)
                    st.markdown(f"**Data Confidence:** {confidence_badge(r['data_confidence'], r['data_confidence_score'])}", unsafe_allow_html=True)
                    st.caption(f"Reason: {ag.get('description', '')}")
                with d_c2:
                    st.markdown("**Top ML Contributing Factors (Plain English):**")
                    factors = r.get('top_contributing_factors', [])
                    if factors:
                        for f in factors[:3]:
                            st.markdown(f"- {f}")
                    else:
                        st.caption("No specific outlier features detected.")
                st.markdown('---')
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button('✓ Confirm Rule Flag', key=f'dis_conf_{s_id}'):
                        store.record_review(r['flag_id'], s_id, 'STAFF-01', 'Confirmed')
                        st.success(f'{s_id} confirmed!')
                        st.rerun()
                with btn_col2:
                    if st.button('✕ Dismiss as False Alarm', key=f'dis_dism_{s_id}'):
                        store.record_review(r['flag_id'], s_id, 'STAFF-01', 'Dismissed', reason_code='Strong performance elsewhere', reason_note='Dismissed via Disagreements Review')
                        st.info(f'{s_id} dismissed.')
                        st.rerun()
    else:
        st.success("✅ Zero disagreements between Rule Engine and ML model at current threshold settings.")
with tab_actions:
    st.markdown('### 📌 Active Supportive Follow-up Actions')
    all_actions = store.get_student_history('')['actions']
    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM actions ORDER BY planned_date ASC')
        actions_list = [dict(r) for r in cursor.fetchall()]
    if actions_list:
        act_df = pd.DataFrame(actions_list)
        st.dataframe(act_df[['action_id', 'student_id', 'action_type', 'planned_date', 'status', 'created_by', 'action_note']], use_container_width=True)
        st.markdown('#### Update Action Status')
        up_col1, up_col2, up_col3 = st.columns(3)
        with up_col1:
            sel_act_id = st.selectbox('Action ID to Update', [a['action_id'] for a in actions_list])
        with up_col2:
            new_st = st.selectbox('New Status', ['Planned', 'Done', 'Declined by student', 'No longer needed'])
        with up_col3:
            if st.button('Update Status'):
                store.update_action_status(sel_act_id, new_st, 'STAFF-01')
                st.success(f'Action {sel_act_id} updated to {new_st}!')
                st.rerun()
    else:
        st.info("No supportive actions recorded yet. Open a student's profile to record planned outreach.")
with tab_analytics:
    st.markdown('### 🔄 Review Feedback Loop & System Tuning')
    st.markdown('Staff review decisions serve as the true ground truth signal in a live deployment. Analyzing dismissals identifies data quality bugs and guides rule threshold recalibration.')
    fb = store.get_feedback_loop_analytics()
    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        st.markdown(f"**Total Coordinator Reviews Completed:** `{fb['total_reviews']}`")
        if fb['decision_breakdown']:
            st.table(pd.DataFrame(list(fb['decision_breakdown'].items()), columns=['Review Decision', 'Count']))
        else:
            st.caption('No reviews logged yet.')
    with fb_col2:
        st.markdown('**Common Dismissal (False Positive) Reasons:**')
        if fb['dismissal_reasons']:
            st.table(pd.DataFrame(list(fb['dismissal_reasons'].items()), columns=['Dismissal Reason', 'Count']))
        else:
            st.caption('No dismissals recorded.')
    st.markdown('#### 💡 Continuous Improvement Suggestions')
    if fb['system_tuning_recommendations']:
        for rec_text in fb['system_tuning_recommendations']:
            st.warning(f'🔧 **Recommended Action:** {rec_text}')
    else:
        st.success('Current review patterns indicate healthy threshold calibration. No systemic bias detected.')
render_footer()
