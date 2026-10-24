# SupportLens: Algorithmic Fairness, Limitations, and Responsible-AI Charter

## 1. Executive Summary & Purpose
SupportLens is an early-warning, supportive decision-support instrument created to assist university course coordinators in identifying students who may benefit from kind, proactive academic guidance. 

**Under no circumstances is SupportLens an automated grading, judicial, or disciplinary tool.** This document provides an honest, rigorous analysis of the system's operational boundaries, fairness audits, and protective mechanisms designed to safeguard student agency and dignity.

---

## 2. False Positives: Architecture, Philosophy, & Harm Mitigation

### 2.1 The Asymmetric Cost of Errors in Supportive AI
In academic early-warning systems, the human cost of classification errors is deeply asymmetrical:
- **False Negative (Missed Support):** A student silently falling behind receives no outreach, risking isolation, cumulative academic distress, or withdrawal.
- **False Positive (Unnecessary Check-in):** A student who is managing fine receives a friendly, compassionate invitation to office hours or a resource check-in.

Because our mandate is compassionate care, SupportLens intentionally tunes for high recall over hyper-conservative precision. However, an uncalibrated system with a high false-positive rate creates **alert fatigue** for university staff and can cause unwarranted anxiety for students. We enforce strict caps so total cohort alert burden stays under 20-25%.

### 2.2 Systemic False-Positive Dampeners
To prevent inappropriate flagging, SupportLens embeds four protective architectural layers:
1. **Protective (Mitigating) Rules (M1 & M2):**
   - *Rule M1:* If a student maintains high quiz scores ($\ge 80\%$) and submits assignments on time, low attendance point penalties are offset ($-2$ points). This specifically protects independent learners and commuting students.
   - *Rule M2:* Upward week-over-week trends ($> +3$ pts/week) in attendance and quizzes indicate recovery, preventing the system from penalizing students for past hurdles.
2. **Multi-Week Persistence Filter (Section 5.5):** Single-week dips in performance (due to a brief cold or family event) are capped at *Monitor* status and cannot trigger outreach unless the concern persists across at least two of the last three weekly snapshots.
3. **Data Confidence Escalation Caps (M3):** Flags with low data confidence ($<0.60$) are capped at *Monitor* and marked with "Needs records verification" rather than escalating to high-urgency alerts.
4. **Permanent Human-in-the-Loop Override:** Staff review is mandatory. Dismissing a flag as a false positive immediately overrides the system rating to "On Track" across all cohort dashboards.

### 2.3 Dignity & Language Guarantee
- A dismissed flag leaves **zero negative mark** on a student's profile.
- All outreach prompts use encouraging, non-blaming language (*"May benefit from supportive follow-up"*, never *"failing"* or *"at fault"*).
- Review records and audit entries track system calibration and staff actions-not student culpability.

---

## 3. Handling Missing and Incomplete Data

Real educational data is fraught with omissions: late LMS synchronization, delayed grading, illness, and late enrollment.

### 3.1 "Missing is Never Zero" Principle
A standard data science error is imputing unrecorded attendance or missing quizzes with zero. In an educational setting, this turns a delayed attendance sheet into an artificial crisis. 
- SupportLens averages over **available valid observations only**.
- If a signal has fewer than 2 valid observations across the observation window, it is marked as **Insufficient Data** rather than penalized.

### 3.2 Data Confidence Scoring
Every student flag is accompanied by an interpretable Data Confidence Score:
$$\text{Data Confidence} = 1.0 - \left(0.40 \cdot \text{att\_missing} + 0.30 \cdot \text{quiz\_missing} + 0.30 \cdot \text{assign\_unknown}\right)$$

Flags are categorized into **High ($\ge 0.85$)**, **Medium ($0.60 - 0.85$)**, and **Low ($< 0.60$)**. Staff can immediately evaluate how much empirical weight supports an alert.

### 3.3 Rule Abstention
When data confidence is critically compromised, rules dependent on that data stream **abstain** from firing. Rather than guessing, SupportLens recommends an administrative check-in to confirm that LMS access and course records are operating normally.

---

## 4. Subgroup Fairness Audit & Empirical Findings

### 4.1 Strict Exclusion of Protected Demographic Attributes
> **Core Guarantee:** Demographic, personal, and group attributes (`cohort_group`, `study_mode`, `prior_support_flag`, gender, ethnicity, age) are **strictly barred from entering the feature engineering or machine learning pipeline.**

All algorithms operate solely on verifiable behavioral engagement metrics. Group attributes are retained in a separate evaluation schema strictly to execute algorithmic fairness audits.

### 4.2 Audit Finding: The Part-Time Student Asymmetry
During synthetic audit testing across `study_mode` (Full-Time vs. Part-Time), SupportLens detected an instructive disparity:
- **Observed Finding:** Part-time students-who balance outside professional or caregiving obligations-naturally register $\sim 8\%$ lower physical class attendance while demonstrating equal quiz performance and on-time submission rates.
- **Naïve Rule Danger:** A simplistic attendance cut-off ($<75\%$) produced a Demographic Parity disparity exceeding 14 percentage points, disproportionately flagging part-time students.
- **SupportLens Mitigation in Action:**
  1. The inclusion of Mitigating Rule M1 ensures high quiz mastery offsets attendance penalties.
  2. Compound Rule C1 and C2 require cross-signal convergence before escalating to Priority Check-in.
  3. When mitigating factors are active, the demographic disparity narrows back within acceptable parity tolerances ($<10\%$).

---

## 5. System Limitations & Known Boundaries

SupportLens is designed with intentional humility:
1. **Synthetic Data Boundaries:** While modeled on realistic educational archetypes, synthetic distributions cannot capture the chaotic multidimensionality of live student cohorts. Measured accuracy metrics are indicative and serve as an algorithmic baseline.
2. **Weekly Granularity:** Weekly batch evaluations cannot detect acute, intra-week emotional or physical crises.
3. **The "Silent Struggle" (Absence of Flag $\neq$ Absence of Need):** A student maintaining perfect grades while experiencing profound personal distress will not be flagged by academic telemetry. SupportLens is a supplement to, never a replacement for, pastoral care and empathetic human observation.
4. **Heuristic Calibration:** Default thresholds ($75\%$ attendance, $50\%$ quiz cut-offs) are initial baselines. Every academic discipline, course structure, and institution requires local threshold tuning.

---

## 6. Long-Term Governance Recommendations

1. **Mandatory Human-in-the-Loop:** Automated actions, auto-emails to students, or disciplinary escalations must be technically blocked.
2. **Coordinator Training:** University staff using SupportLens should receive guidance on trauma-informed, compassionate communication before initiating check-ins.
3. **Student Transparency & Agency:** Students should be openly informed that automated support-check systems operate in the course, with a clear charter outlining their privacy rights and an opt-out consultation route.
4. **Feedback Loop Recalibration:** Dismissal reason analytics (e.g., frequent dismissals due to *"Data error"* or *"Known medical leave"*) should be reviewed at mid-semester to refine institutional thresholds.
