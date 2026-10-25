import streamlit as st

def inject_aesthetic_black_red_bg():
    st.markdown("""
        <style>
            /* Main background: aesthetic deep black with subtle crimson ambient radial glow */
            .stApp {
                background: radial-gradient(ellipse at 50% 0%, #1c0508 0%, #0c0203 40%, #050102 100%) !important;
                background-attachment: fixed !important;
                color: #F1F5F9 !important;
            }

            /* Sidebar styling */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #130305 0%, #080102 100%) !important;
                border-right: 1px solid rgba(230, 57, 70, 0.22) !important;
            }

            /* Top header bar */
            [data-testid="stHeader"] {
                background: rgba(7, 2, 3, 0.75) !important;
                backdrop-filter: blur(12px) !important;
            }

            /* Metric cards & expanders with dark glassmorphic styling & subtle red borders */
            div[data-testid="stMetric"] {
                background: rgba(22, 6, 9, 0.65) !important;
                border: 1px solid rgba(230, 57, 70, 0.22) !important;
                border-radius: 8px !important;
                padding: 12px 16px !important;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45), 0 0 15px rgba(230, 57, 70, 0.05) !important;
            }

            div[data-testid="stExpander"] {
                background: rgba(18, 5, 7, 0.6) !important;
                border: 1px solid rgba(230, 57, 70, 0.2) !important;
                border-radius: 8px !important;
            }

            /* Tabs with aesthetic crimson active indicators */
            button[data-baseweb="tab"] {
                color: #94A3B8 !important;
                font-weight: 500 !important;
            }

            button[data-baseweb="tab"][aria-selected="true"] {
                color: #FF5A68 !important;
                border-bottom: 2px solid #E63946 !important;
            }

            /* Styled scrollbars */
            ::-webkit-scrollbar {
                width: 7px;
                height: 7px;
            }
            ::-webkit-scrollbar-track {
                background: #080102;
            }
            ::-webkit-scrollbar-thumb {
                background: #3B0D13;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #E63946;
            }
        </style>
    """, unsafe_allow_html=True)


def render_guardrails_banner():
    inject_aesthetic_black_red_bg()
    st.markdown("""
        <div style="background: rgba(24, 6, 9, 0.85); border: 1px solid rgba(230, 57, 70, 0.35); border-left: 5px solid #E63946; padding: 14px 18px; border-radius: 6px; margin: 12px 0 20px 0; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5), 0 0 20px rgba(230, 57, 70, 0.1);">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.4rem;">🛡️</span>
                <div>
                    <strong style="color: #FF6B7A; font-size: 0.95rem; letter-spacing: 0.4px;">ETHICAL AI GUARDRAIL & HUMAN-IN-THE-LOOP MANDATE</strong><br/>
                    <span style="color: #E2E8F0; font-size: 0.88rem; line-height: 1.5;">
                        This system is an early-warning supportive tool to help course coordinators offer timely academic assistance. 
                        <strong>It never makes grades, penalties, holds, or final academic decisions.</strong> 
                        Human review by an authorised staff member is strictly required before any supportive outreach is initiated.
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_footer():
    st.markdown('---')
    st.markdown("""
        <div style="text-align: center; color: #94A3B8; font-size: 0.82rem; padding: 12px 0;">
            🔒 <strong style="color: #CBD5E1;">100% Synthetic Data Demonstration</strong> • No real students, emails, or personal identifiers • 
            <span style="color: #FF6B7A;">SupportLens Early-Warning Prototype</span> • For Academic Coordinator Decision Support Only
        </div>
    """, unsafe_allow_html=True)

