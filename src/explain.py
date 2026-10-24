from typing import Dict, Any, List, Optional
import numpy as np
BANNED_WORDS = {'fail', 'failing', 'failure', 'lazy', 'punish', 'punitive', 'penalty', 'at fault', 'blame', 'delinquent', 'problem student', 'disciplinary', 'misconduct', 'expel', 'terminate', 'probation'}
ACTION_TEMPLATES = {'Attendance Concern': ['Friendly check-in email about course pacing and lecture recordings', 'Ask about timetable or transport barriers impacting class attendance', 'Offer flexible catch-up resources and office hour appointments'], 'Submission Concern': ['Offer proactive extension discussion for upcoming assignment', 'Share assignment planning guide and rubric walkthrough', 'Connect with academic writing and study-skills workshop'], 'Assessment Concern': ['Invite to peer tutoring or coordinator office hours', 'Share supplementary practice quizzes with solution guides', 'Suggest joining a collaborative peer study group'], 'Engagement Drop (Compound)': ['Warm one-to-one wellbeing and workload conversation', 'Refer to student support services or academic advising (with student consent)', 'Review overall academic workload and establish milestone schedule'], 'Insufficient Data': ['Confirm student enrollment records and course registry are accurate', 'Reach out to verify active LMS participation and platform access'], 'On Track': ['Encouraging note acknowledging steady consistency and engagement', 'Invite to explore advanced optional topics or peer mentoring opportunities']}

def verify_text_safety(text: str):
    words = text.lower().replace('.', '').replace(',', '').replace('!', '').split()
    for w in words:
        if w in BANNED_WORDS:
            raise ValueError(f"CRITICAL GUARDRAIL VIOLATION: Punitive/blaming term '{w}' detected in generated text!")

def generate_explanation(flag_result: Dict[str, Any], features: Optional[Dict[str, Any]]=None) -> Dict[str, Any]:
    level = flag_result.get('support_level', 'On Track')
    categories = flag_result.get('categories', [])
    fired_rules = flag_result.get('fired_rules', [])
    mitigating_rules = flag_result.get('mitigating_rules', [])
    confidence = flag_result.get('data_confidence', 'High')
    bullets = []
    for r in fired_rules:
        desc = r.get('description', '')
        bullets.append(desc)
    if level == 'Insufficient Data':
        summary = 'Available student participation records are currently limited or incomplete. A coordinator check-in is recommended to verify enrollment details and ensure the student has unhindered access to learning materials.'
    elif level == 'On Track':
        summary = 'This student demonstrates consistent academic engagement across attendance, assignments, and assessments. Current records show no indicators of required outreach.'
    elif level == 'Monitor':
        category_phrase = ' and '.join([c.replace(' Concern', '').lower() for c in categories]) if categories else 'routine engagement'
        summary = f'This student shows a gentle Monitor pattern, primarily relating to {category_phrase}. A casual check-in or shared reminder can help sustain their momentum. Data confidence is {confidence}.'
    elif level == 'Suggest Outreach':
        primary_concerns = ', '.join([c.replace(' Concern', '') for c in categories])
        summary = f'This student is recommended for supportive outreach due to noticeable shifts in {primary_concerns}. Early compassionate engagement can help address developing hurdles before they grow. Data confidence is {confidence}.'
    else:
        summary = f'This student exhibits multi-signal engagement changes across multiple indicators. A timely, supportive conversation is recommended to explore potential academic or personal barriers and offer tailored support resources. Data confidence is {confidence}.'
    strengths = []
    if mitigating_rules:
        for m in mitigating_rules:
            if m.get('id') == 'M1':
                strengths.append('Assessment mastery remains solid, demonstrating strong conceptual understanding despite attendance gaps.')
            elif m.get('id') == 'M2':
                strengths.append('Recent trajectory shows positive week-over-week recovery in attendance and assessment participation.')
    if features:
        q_mean = features.get('quiz_mean_recent')
        sub_rate = features.get('submission_rate_overall')
        att_mean = features.get('att_mean_recent')
        if q_mean is not None and (not np.isnan(q_mean)) and (q_mean >= 75):
            strengths.append(f'Recent quiz scores are positive, averaging {q_mean:.1f}%.')
        if sub_rate is not None and (not np.isnan(sub_rate)) and (sub_rate >= 0.85):
            strengths.append(f'High overall assignment submission rate of {sub_rate * 100:.0f}%.')
        if att_mean is not None and (not np.isnan(att_mean)) and (att_mean >= 85):
            strengths.append(f'Strong class presence with {att_mean:.1f}% recent attendance.')
    if not strengths:
        strengths.append('The student continues active enrollment in the course.')
    strengths_line = ' '.join(strengths[:2])
    suggested_actions = []
    if level == 'Insufficient Data':
        suggested_actions.extend(ACTION_TEMPLATES['Insufficient Data'])
    elif level == 'On Track':
        suggested_actions.extend(ACTION_TEMPLATES['On Track'])
    else:
        for cat in categories:
            if cat in ACTION_TEMPLATES:
                suggested_actions.extend(ACTION_TEMPLATES[cat])
    unique_actions = list(dict.fromkeys(suggested_actions))
    verify_text_safety(summary)
    verify_text_safety(strengths_line)
    for b in bullets:
        verify_text_safety(b)
    return {'summary': summary, 'bullets': bullets, 'strengths': strengths_line, 'suggested_actions': unique_actions}
