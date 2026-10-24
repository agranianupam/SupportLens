from typing import Optional
LEVEL_STYLES = {'On Track': {'bg': '#DEF7EC', 'text': '#03543F', 'border': '#31C48D', 'icon': '🟢'}, 'Monitor': {'bg': '#FEF08A', 'text': '#713F12', 'border': '#FACC15', 'icon': '🟡'}, 'Suggest Outreach': {'bg': '#FFEDD5', 'text': '#9A3412', 'border': '#FB923C', 'icon': '🟠'}, 'Priority Check-in': {'bg': '#FEE2E2', 'text': '#991B1B', 'border': '#F87171', 'icon': '🔴'}, 'Insufficient Data': {'bg': '#F3F4F6', 'text': '#374151', 'border': '#9CA3AF', 'icon': '⚪'}}
CONFIDENCE_STYLES = {'High': {'bg': '#E0F2FE', 'text': '#075985', 'border': '#38BDF8', 'icon': '📶'}, 'Medium': {'bg': '#FEF3C7', 'text': '#92400E', 'border': '#FBBF24', 'icon': '📳'}, 'Low': {'bg': '#F3E8FF', 'text': '#6B21A8', 'border': '#C084FC', 'icon': '⚠️'}}

def support_level_badge(level: str) -> str:
    cfg = LEVEL_STYLES.get(level, LEVEL_STYLES['On Track'])
    return f"""<span style="\n        display: inline-flex;\n        align-items: center;\n        gap: 5px;\n        background-color: {cfg['bg']};\n        color: {cfg['text']};\n        border: 1px solid {cfg['border']};\n        border-radius: 14px;\n        padding: 3px 10px;\n        font-size: 0.82rem;\n        font-weight: 600;\n        white-space: nowrap;\n    ">{cfg['icon']} {level}</span>"""

def confidence_badge(level: str, score: Optional[float]=None) -> str:
    cfg = CONFIDENCE_STYLES.get(level, CONFIDENCE_STYLES['High'])
    score_txt = f' ({score:.2f})' if score is not None else ''
    return f"""<span style="\n        display: inline-flex;\n        align-items: center;\n        gap: 5px;\n        background-color: {cfg['bg']};\n        color: {cfg['text']};\n        border: 1px solid {cfg['border']};\n        border-radius: 14px;\n        padding: 2px 8px;\n        font-size: 0.78rem;\n        font-weight: 600;\n    ">{cfg['icon']} {level} Conf{score_txt}</span>"""

def agreement_badge(agreement_dict: dict) -> str:
    atype = agreement_dict.get('type', 'both_ontrack')
    icon = agreement_dict.get('icon', '✅')
    badge_txt = agreement_dict.get('badge', 'Agreement')
    if atype in ['both_support', 'both_ontrack']:
        bg = '#F0FDF4'
        text = '#166534'
        border = '#86EFAC'
    else:
        bg = '#FFFBEB'
        text = '#B45309'
        border = '#FCD34D'
    return f'<span style="\n        display: inline-flex;\n        align-items: center;\n        gap: 5px;\n        background-color: {bg};\n        color: {text};\n        border: 1px solid {border};\n        border-radius: 14px;\n        padding: 2px 8px;\n        font-size: 0.78rem;\n        font-weight: 600;\n    ">{icon} {badge_txt}</span>'

def review_status_badge(decision: str) -> str:
    if 'Confirmed' in decision:
        bg, text, border, icon = ('#E0F2FE', '#0369A1', '#7DD3FC', '✓')
    elif 'Corrected' in decision:
        bg, text, border, icon = ('#EDE9FE', '#6D28D9', '#C4B5FD', '✏️')
    elif 'Dismissed' in decision:
        bg, text, border, icon = ('#F1F5F9', '#475569', '#CBD5E1', '✕')
    elif 'Deferred' in decision:
        bg, text, border, icon = ('#FEF3C7', '#B45309', '#FCD34D', '⏳')
    else:
        bg, text, border, icon = ('#F8FAFC', '#64748B', '#E2E8F0', '○')
    return f'<span style="\n        display: inline-flex;\n        align-items: center;\n        gap: 4px;\n        background-color: {bg};\n        color: {text};\n        border: 1px solid {border};\n        border-radius: 12px;\n        padding: 2px 7px;\n        font-size: 0.75rem;\n        font-weight: 500;\n    ">{icon} {decision}</span>'
