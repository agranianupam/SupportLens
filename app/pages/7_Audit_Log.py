import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import json
from app.components.guardrails import render_guardrails_banner, render_footer
from app.data_loader import get_review_store
st.set_page_config(page_title='Audit Log - SupportLens', page_icon='📜', layout='wide')
st.title('📜 Immutable Audit Log & Accountability Register')
st.markdown('To ensure accountability and transparency, every automated scoring event, staff review decision, level override, and supportive action is permanently recorded in an append-only ledger.')
store = get_review_store()
f_col1, f_col2, f_col3 = st.columns(3)
with f_col1:
    filter_student = st.text_input('Filter by Student ID', placeholder='e.g. S-0042').strip().upper()
with f_col2:
    filter_event = st.selectbox('Filter by Event Type', options=['All Events', 'REVIEW_', 'ACTION_', 'FLAG_EVALUATED'])
with f_col3:
    log_limit = st.slider('Record Limit', min_value=50, max_value=500, value=200, step=50)
event_query = None if filter_event == 'All Events' else filter_event
raw_logs = store.get_audit_log(limit=log_limit, student_id=filter_student if filter_student else None, event_type=event_query)
st.markdown(f'**Displaying {len(raw_logs)} logged events:**')
if raw_logs:
    display_rows = []
    for l in raw_logs:
        details_obj = json.loads(l['details_json'])
        details_summary = ', '.join([f'{k}: {v}' for k, v in details_obj.items()])
        display_rows.append({'Log ID': l['log_id'], 'Timestamp (UTC)': l['timestamp'][:19].replace('T', ' '), 'Actor Code': l['actor_code'], 'Event Type': l['event_type'], 'Student ID': l['student_id'], 'Flag ID': l['flag_id'] if l['flag_id'] else '-', 'Event Details': details_summary})
    df_logs = pd.DataFrame(display_rows)
    st.dataframe(df_logs, use_container_width=True)
    from src.export import generate_audit_log_csv
    audit_csv = generate_audit_log_csv(raw_logs)
    if st.download_button(
        label='📥 Download Audit Log as CSV',
        data=audit_csv,
        file_name='supportlens_audit_log.csv',
        mime='text/csv',
    ):
        store.record_export('AUDIT_LOG_CSV', actor_code='STAFF-01', details={'record_count': len(raw_logs)})
else:
    st.info('No audit logs matching current filter.')
st.markdown('---')
st.markdown('🛡️ **Integrity Notice:** Audit log rows cannot be updated, edited, or deleted through the user interface. All human coordinator interactions remain strictly auditable to uphold student privacy and procedural fairness.')
render_guardrails_banner()
render_footer()
