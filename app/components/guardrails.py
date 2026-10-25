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


def apply_page_theme():
    """Injects global theme styles without rendering any visual banner."""
    inject_aesthetic_theme()


def render_guardrails_banner():
    """
    Renders the relocated ethical guardrail banner at the bottom of the page.
    Compact, responsive, subtle low-contrast styling in normal document flow.
    """
    inject_aesthetic_theme()
    st.markdown("""
        <div style="background: rgba(240, 253, 250, 0.75); border: 1px solid rgba(13, 148, 136, 0.22); border-left: 4px solid #0D9488; padding: 12px 16px; border-radius: 8px; margin: 24px 0 10px 0; box-shadow: 0 2px 10px rgba(13, 148, 136, 0.04);">
            <div style="display: flex; align-items: flex-start; gap: 10px;">
                <span style="font-size: 1.15rem; line-height: 1.2;">🛡️</span>
                <div>
                    <div style="color: #0F766E; font-size: 0.82rem; font-weight: 700; letter-spacing: 0.4px; text-transform: uppercase;">
                        Ethical AI Guardrail & Human-in-the-Loop Mandate
                    </div>
                    <div style="color: #475569; font-size: 0.82rem; line-height: 1.45; margin-top: 2px;">
                        This system is an early-warning supportive tool to help course coordinators offer timely academic assistance. 
                        <strong style="color: #0F172A;">It never makes grades, penalties, holds, or final academic decisions.</strong> 
                        Human review by an authorised staff member is strictly required before any supportive outreach is initiated.
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_footer():
    """
    Renders the bottom synthetic data disclaimer.
    """
    st.markdown("""
        <div style="text-align: center; color: #64748B; font-size: 0.78rem; padding: 6px 0 16px 0;">
            🔒 <strong style="color: #334155;">100% Synthetic Data Demonstration</strong> • Anonymised student IDs (S-0001..S-0100) • No real students or emails • 
            <span style="color: #0D9488; font-weight: 600;">SupportLens Prototype</span> • Decision Support Only
        </div>
    """, unsafe_allow_html=True)


