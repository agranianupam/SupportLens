import streamlit as st

def render_guardrails_banner():
    st.markdown('\n        <div style="background-color: #EBF3FB; border-left: 5px solid #2B6CB0; padding: 12px 16px; border-radius: 4px; margin-bottom: 20px;">\n            <div style="display: flex; align-items: center; gap: 10px;">\n                <span style="font-size: 1.3rem;">🛡️</span>\n                <div>\n                    <strong style="color: #1A365D; font-size: 0.95rem;">ETHICAL AI GUARDRAIL & HUMAN-IN-THE-LOOP MANDATE</strong><br/>\n                    <span style="color: #2D3748; font-size: 0.88rem;">\n                        This system is an early-warning supportive tool to help course coordinators offer timely academic assistance. \n                        <strong>It never makes grades, penalties, holds, or final academic decisions.</strong> \n                        Human review by an authorised staff member is strictly required before any supportive outreach is initiated.\n                    </span>\n                </div>\n            </div>\n        </div>\n        ', unsafe_allow_html=True)

def render_footer():
    st.markdown('---')
    st.markdown('\n        <div style="text-align: center; color: #718096; font-size: 0.82rem; padding: 10px 0;">\n            🔒 <strong>100% Synthetic Data Demonstration</strong> • No real students, emails, or personal identifiers • \n            SupportLens Early-Warning Prototype • For Academic Coordinator Decision Support Only\n        </div>\n        ', unsafe_allow_html=True)
