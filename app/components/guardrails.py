import streamlit as st

def inject_aesthetic_theme():
    st.markdown("""
        <style>
            /* Main background: Pristine, serene mint/cyan/white gradient */
            .stApp {
                background: linear-gradient(135deg, #F0FDF4 0%, #ECFDF5 30%, #F0FDFA 70%, #F8FAFC 100%) !important;
                background-attachment: fixed !important;
                color: #0F172A !important;
            }

            /* Sidebar: Soft mint-tinted off-white */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #F2FBF9 0%, #FFFFFF 100%) !important;
                border-right: 1px solid #E6F4F1 !important;
            }

            /* Header bar: Ethereal frosted glass */
            [data-testid="stHeader"] {
                background: rgba(248, 250, 252, 0.8) !important;
                backdrop-filter: blur(12px) !important;
            }

            /* Metric cards: Crisp elevated white with subtle teal borders */
            div[data-testid="stMetric"] {
                background: #FFFFFF !important;
                border: 1px solid rgba(13, 148, 136, 0.16) !important;
                border-radius: 12px !important;
                padding: 16px 20px !important;
                box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02) !important;
            }

            div[data-testid="stExpander"] {
                background: #FFFFFF !important;
                border: 1px solid rgba(13, 148, 136, 0.18) !important;
                border-radius: 12px !important;
                box-shadow: 0 2px 8px rgba(15, 23, 42, 0.03) !important;
            }

            /* Tabs styling with modern teal active indicator */
            button[data-baseweb="tab"] {
                color: #64748B !important;
                font-weight: 500 !important;
            }

            button[data-baseweb="tab"][aria-selected="true"] {
                color: #0D9488 !important;
                font-weight: 600 !important;
                border-bottom: 2px solid #0D9488 !important;
            }

            /* Styled scrollbars */
            ::-webkit-scrollbar {
                width: 7px;
                height: 7px;
            }
            ::-webkit-scrollbar-track {
                background: #F0FDF4;
            }
            ::-webkit-scrollbar-thumb {
                background: #99F6E4;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #14B8A6;
            }
        </style>
    """, unsafe_allow_html=True)


def render_guardrails_banner():
    inject_aesthetic_theme()
    st.markdown("""
        <div style="background: linear-gradient(90deg, #ECFDF5 0%, #F0FDFA 100%); border-left: 5px solid #0D9488; border: 1px solid rgba(13, 148, 136, 0.22); border-left-width: 5px; padding: 14px 18px; border-radius: 10px; margin: 12px 0 20px 0; box-shadow: 0 4px 15px rgba(13, 148, 136, 0.06);">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 1.4rem;">🛡️</span>
                <div>
                    <strong style="color: #0F766E; font-size: 0.95rem; letter-spacing: 0.3px;">ETHICAL AI GUARDRAIL & HUMAN-IN-THE-LOOP MANDATE</strong><br/>
                    <span style="color: #334155; font-size: 0.88rem; line-height: 1.5;">
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
        <div style="text-align: center; color: #64748B; font-size: 0.82rem; padding: 12px 0;">
            🔒 <strong style="color: #334155;">100% Synthetic Data Demonstration</strong> • No real students, emails, or personal identifiers • 
            <span style="color: #0D9488; font-weight: 600;">SupportLens Early-Warning Prototype</span> • For Academic Coordinator Decision Support Only
        </div>
    """, unsafe_allow_html=True)


