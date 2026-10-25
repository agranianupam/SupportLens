import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from app.components.guardrails import render_guardrails_banner, render_footer
from app.components.badges import support_level_badge, confidence_badge, agreement_badge, review_status_badge
from app.components.charts import create_student_attendance_chart, create_student_assignment_strip, create_student_quiz_chart
from app.data_loader import load_raw_data, get_cohort_snapshot, get_review_store
st.set_page_config(page_title='Student Detail - SupportLens', page_icon='👤', layout='wide')
default_week = int(st.session_state.get('snapshot_week', 10))
as_of_week = st.sidebar.slider('📅 Snapshot Week', min_value=4, max_value=12, value=default_week, step=1)
st.session_state['snapshot_week'] = as_of_week
students_df, cleaned_weekly, ground_truth, _ = load_raw_data()
features_df, cohort_records = get_cohort_snapshot(as_of_week)
store = get_review_store()
st.sidebar.markdown('---')
st.sidebar.markdown(' **Presentation Demo Mode**')
demo_archetypes = {'Select a demo case...': None, 'Gradual Decliner (Falling Attendance)': 'gradual_decliner', 'Strong but Irregular (False Positive Trap)': 'strong_irregular', 'Sudden Dropper (Recent Change)': 'sudden_dropper', 'Recovering (Improved Engagement)': 'recovering', 'Data Gap Case (Sparse Records)': 'chronic_low'}
demo_choice = st.sidebar.selectbox('Jump to Archetype Case', list(demo_archetypes.keys()))
selected_id = None
if demo_choice and demo_archetypes[demo_choice]:
    target_arch = demo_archetypes[demo_choice]
    matches = students_df[students_df['archetype'] == target_arch]['student_id'].tolist()
    if matches:
        selected_id = matches[0]
all_ids = sorted([r['student_id'] for r in cohort_records])
if not selected_id and 'selected_student_id' in st.session_state and st.session_state['selected_student_id'] in all_ids:
    selected_id = st.session_state['selected_student_id']
default_index = all_ids.index(selected_id) if selected_id in all_ids else 0
student_id = st.sidebar.selectbox('Select Student ID', all_ids, index=default_index)
rec = next((r for r in cohort_records if r['student_id'] == student_id), None)
s_weekly = cleaned_weekly[cleaned_weekly['student_id'] == student_id].sort_values('week')
if rec is None:
    st.error(f'Student {student_id} not found.')
    st.stop()
st.title(f'👤 Student Profile: {student_id}')
h_col1, h_col2, h_col3, h_col4 = st.columns(4)
with h_col1:
    st.markdown('**Effective Support Level:**')
    st.markdown(support_level_badge(rec['display_level']), unsafe_allow_html=True)
with h_col2:
    st.markdown('**Review Status:**')
    st.markdown(review_status_badge(rec['review_decision']), unsafe_allow_html=True)
with h_col3:
    st.markdown('**Data Confidence:**')
    st.markdown(confidence_badge(rec['data_confidence'], rec['data_confidence_score']), unsafe_allow_html=True)
with h_col4:
    st.markdown('**Rule vs ML Alignment:**')
    st.markdown(agreement_badge(rec['agreement']), unsafe_allow_html=True)
if rec.get('override_applied'):
    st.warning(f"ℹ️ **Human Coordinator Override Active:** System originally scored this student as **{rec['support_level']}**, but staff review decided **{rec['display_level']}**.")
st.markdown('---')
st.markdown('### 📈 Engagement Trajectory Small Multiples (Weeks 1 to ' + str(as_of_week) + ')')
t_col1, t_col2, t_col3 = st.columns(3)
with t_col1:
    fig_att = create_student_attendance_chart(s_weekly, as_of_week)
    st.plotly_chart(fig_att, use_container_width=True)
with t_col2:
    fig_strip = create_student_assignment_strip(s_weekly, as_of_week)
    st.plotly_chart(fig_strip, use_container_width=True)
with t_col3:
    fig_quiz = create_student_quiz_chart(s_weekly, as_of_week)
    st.plotly_chart(fig_quiz, use_container_width=True)
st.markdown('---')
e_col1, e_col2 = st.columns([1.3, 1])
expl = rec.get('explanation', {})
with e_col1:
    st.markdown('### 🔍 Why This Support Level Was Suggested')
    st.info(expl.get('summary', 'No automated concern detected.'))
    fired = rec.get('fired_rules', [])
    if fired:
        st.markdown('**Triggered Rule Detail:**')
        fired_df = pd.DataFrame([{'Rule': r['id'], 'Category': r['category'], 'Observed Metric': r['observed_value'], 'Threshold': r['threshold'], 'Points': f"+{r['points']}", 'Explanation': r['description']} for r in fired])
        st.table(fired_df)
    else:
        st.caption('No rules triggered. Engagement remains within expected parameters.')
    abstained = rec.get('abstained_rules', [])
    if abstained:
        st.caption(f"ℹ️ Rules abstained due to insufficient data points: {', '.join(abstained)}")
    persistence_note = expl.get('persistence', rec.get('persistence_note', 'Evaluated over snapshot history.'))
    st.markdown(f"**Multi-Week Persistence:** {persistence_note}")
with e_col2:
    st.markdown("### 🌟 What's Going Well (Strengths)")
    st.success(expl.get('strengths', 'The student is actively enrolled.'))
    st.markdown('### 🤖 Interpretable ML Cross-Check')
    ml_prob = rec.get('ml_probability', 0.0)
    st.markdown(f'**ML Predicted Support Probability:** `{ml_prob:.1%}`')
    st.caption('Logistic Regression (Balanced, Interpretable Weights)')
    st.caption('ℹ️ Note: The rule engine drives the displayed flag; ML is a cross-check only.')
    top_factors = rec.get('top_contributing_factors', [])
    if top_factors:
        st.markdown('**Top Influencing Factors:**')
        for tf in top_factors[:3]:
            st.markdown(f'- {tf}')
st.markdown('---')
st.markdown('### ✍️ Staff Review & Supportive Action Panel')
st.markdown('Human coordinator oversight is required before any outreach. Select a review decision, record compassionate follow-up actions, and submit.')
with st.form('staff_review_form'):
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown('#### 1. Review Decision')
        staff_code = st.text_input('Reviewer Code (Anonymised)', value='STAFF-01')
        decision = st.selectbox('Decision', options=['Confirmed', 'Corrected', 'Dismissed', 'Deferred'], help='Confirmed: agree with flag. Corrected: change support level. Dismissed: false alarm. Deferred: monitor next week.')
        corrected_level = None
        if decision == 'Corrected':
            corrected_level = st.selectbox('Corrected Support Level', options=['On Track', 'Monitor', 'Suggest Outreach', 'Priority Check-in', 'Insufficient Data'])
        reason_code = st.selectbox('Reason Code (Required for Corrected/Dismissed)', options=['', 'Known circumstance', 'Data error', 'Already supported', 'Strong performance elsewhere', 'Other'])
        reason_note = st.text_area('Review Explanation Note', placeholder='Document coordinator rationale (e.g., approved medical leave in week 5)...')
    with r_col2:
        st.markdown('#### 2. Record Supportive Follow-up Action')
        suggested_actions = expl.get('suggested_actions', [])
        action_options = ['None'] + suggested_actions + ['Custom Supportive Action']
        selected_action = st.selectbox('Action Template', options=action_options)
        custom_action_text = ''
        if selected_action == 'Custom Supportive Action':
            custom_action_text = st.text_input('Specify Custom Action', placeholder='e.g. Schedule informal coffee check-in')
        action_note = st.text_area('Outreach Notes / Resources to Share', placeholder='Include links to study guides, workshop dates, etc.')
        planned_date = st.date_input('Target Follow-up Date')
        action_status = st.selectbox('Action Status', options=['Planned', 'Done', 'Declined by student', 'No longer needed'])
    submit_review = st.form_submit_button('💾 Save Review & Action to Immutable Audit Log', use_container_width=True)
    if submit_review:
        try:
            flag_id = rec.get('flag_id')
            if decision == 'Corrected':
                if not reason_code or not reason_note.strip():
                    st.error('Both a Reason Code and an Explanation Note are strictly required when correcting a flag.')
                    st.stop()
            if decision == 'Dismissed' and (not reason_code):
                st.error('A Reason Code is required when dismissing a flag as a false positive.')
                st.stop()
            store.record_review(flag_id=flag_id, student_id=student_id, reviewer_code=staff_code, decision=decision, corrected_level=corrected_level, reason_code=reason_code if reason_code else None, reason_note=reason_note if reason_note else None)
            final_action_type = custom_action_text if selected_action == 'Custom Supportive Action' else selected_action
            if final_action_type and final_action_type != 'None':
                store.record_action(student_id=student_id, action_type=final_action_type, reviewer_code=staff_code, flag_id=flag_id, action_note=action_note, planned_date=str(planned_date), status=action_status)
            st.success(f"Review decision '{decision}' recorded successfully! Coordinator decision overrides system flag across all dashboards.")
            st.rerun()
        except Exception as e:
            st.error(f'Error saving review: {str(e)}')
st.markdown('---')
st.markdown('### 📜 Student Review & Action Lineage')
hist = store.get_student_history(student_id)
h_tab1, h_tab2, h_tab3 = st.tabs(['Past Reviews', 'Planned Actions', 'Historical Flags'])
with h_tab1:
    if hist['reviews']:
        st.table(pd.DataFrame(hist['reviews'])[['reviewed_at', 'reviewer_code', 'decision', 'corrected_level', 'reason_code', 'reason_note']])
    else:
        st.caption('No reviews logged yet for this student.')

with h_tab2:
    if hist['actions']:
        st.markdown("#### Follow-up Action Tracker")
        st.caption(
            "Track supportive actions and update their progress. "
            "Every status change is recorded in the audit log."
        )

        actions_df = pd.DataFrame(hist['actions'])
        st.dataframe(
            actions_df[
                [
                    'action_id',
                    'created_at',
                    'action_type',
                    'planned_date',
                    'status',
                    'action_note',
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Update an Existing Action")

        action_ids = [int(a['action_id']) for a in hist['actions']]
        selected_action_id = st.selectbox(
            "Select action to update",
            options=action_ids,
            format_func=lambda aid: next(
                f"#{aid} — {a['action_type']} ({a['status']})"
                for a in hist['actions']
                if int(a['action_id']) == aid
            ),
            key="followup_action_id",
        )

        selected_record = next(
            a for a in hist['actions']
            if int(a['action_id']) == selected_action_id
        )

        valid_statuses = [
            'Planned',
            'Done',
            'Declined by student',
            'No longer needed',
        ]

        with st.form("update_followup_status_form"):
            new_status = st.selectbox(
                "New follow-up status",
                options=valid_statuses,
                index=valid_statuses.index(selected_record['status'])
                if selected_record['status'] in valid_statuses else 0,
            )

            update_submitted = st.form_submit_button(
                "Save Follow-up Status"
            )

            if update_submitted:
                try:
                    if new_status == selected_record['status']:
                        st.info("This action already has that status.")
                    else:
                        store.update_action_status(
                            action_id=selected_action_id,
                            new_status=new_status,
                            actor_code="STAFF-01",
                        )
                        st.success(
                            f"Action #{selected_action_id} updated to "
                            f"'{new_status}'. The change was recorded."
                        )
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not update action: {e}")

        st.markdown("#### Follow-up Effectiveness")

        completed_actions = [
            action
            for action in hist["actions"]
            if action["status"] == "Done"
        ]

        if completed_actions:
            action_options = {
                f"Action #{action['action_id']} — {action['action_type']}": action
                for action in completed_actions
            }

            selected_label = st.selectbox(
                "Select a completed action",
                list(action_options.keys()),
                key="feedback_action_select",
            )

            selected_action = action_options[selected_label]
            existing_feedback = store.get_action_feedback(
                selected_action["action_id"]
            )

            with st.form("action_feedback_form"):
                outcome = st.selectbox(
                    "How effective was this follow-up?",
                    ["Helpful", "Partially helpful", "Not helpful"],
                )

                staff_note = st.text_area(
                    "Staff note (optional)",
                    placeholder="Record any observed outcome...",
                )

                submitted = st.form_submit_button("Save Feedback")

                if submitted:
                    try:
                        store.record_action_feedback(
                            action_id=selected_action["action_id"],
                            outcome=outcome,
                            staff_note=staff_note,
                            recorded_by="STAFF-01",
                        )
                        st.success("Follow-up feedback saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save feedback: {exc}")

            if existing_feedback:
                st.caption(
                    f"Last recorded by: {existing_feedback['recorded_by']}"
                )
                if existing_feedback["staff_note"]:
                    st.write(existing_feedback["staff_note"])
        else:
            st.info(
                "Mark a follow-up action as Done before recording its effectiveness."
            )
    else:
        st.caption(
            "No follow-up actions recorded yet for this student. "
            "Record an action in the Staff Review panel first."
        )

with h_tab3:
    if hist['flags']:
        st.table(pd.DataFrame(hist['flags'])[['as_of_week', 'support_level', 'score', 'categories', 'created_at']])
    else:
        st.caption('No historical flags recorded.')

render_guardrails_banner()
render_footer()
