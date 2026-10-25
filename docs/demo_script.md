# SupportLens: 5-Minute Live Demonstration Script

This script is structured for an exact 5-minute live competition demonstration to judges. It emphasizes non-punitive ethics, interpretable explainability, human oversight, algorithmic stability, and procedural fairness.

---

## ⏱️ Timeline Overview (Exact 300 Seconds)

1. **0:00 - 0:30 (30s):** The Problem & Mandatory Ethical Guardrails
2. **0:30 - 1:15 (45s):** Home Page, 100% Synthetic Data & Ingestion Telemetry
3. **1:15 - 2:15 (60s):** Cohort Dashboard, Longitudinal Trends & Live What-If Tuning
4. **2:15 - 3:30 (75s):** Student Deep-Dive: Gradual Decliner (`S-0084`) & Trajectories
5. **3:30 - 4:30 (60s):** Correct False Alarm (`S-0031`), Record Action & View Append-Only Audit Log
6. **4:30 - 5:00 (30s):** Evaluation Integrity: Multi-Seed Stability, Earliness & Baselines
7. **5:00 - 5:30 (30s):** Subgroup Fairness Audit & Missing-Data Stress Test

---

## 🎬 Step-by-Step Spoken Script & Actions

### 1. Problem & Ethical Guardrails Banner (0:00 - 0:30 | 30s)
- **Screen:** `app/Home.py`
- **Spoken:**
  > *"Judges, university course coordinators track weekly engagement for hundreds of students across attendance, quizzes, and assignments. They want to identify students who may need academic support early—before small hurdles compound into withdrawal.*
  >
  > *Here is our foundational ground rule: **SupportLens is strictly supportive, never punitive.** Look at the prominent blue banner at the top of every screen: SupportLens is legally and technically barred from issuing automated penalties, grading deductions, holds, or disciplinary actions. It provides decision support; authorized staff review is mandatory."*

---

### 2. Home Page & Data Quality Ingestion (0:30 - 1:15 | 45s)
- **Screen:** `app/Home.py`
- **Spoken:**
  > *"Every student record here is **100% synthetic**, indexed with anonymized IDs from `S-0001` to `S-0100`. No real names, emails, or personal identifiers exist in this system.*
  >
  > *Look at our **Data Quality Telemetry** tiles: Real educational data is noisy. Upon ingestion, SupportLens automatically sanitized duplicated submissions and clamped sensor errors without human intervention. Crucially: **'Missing is never zero'.** When attendance sheets are delayed, we never impute zero or drop students. Instead, our Data Confidence Score tells staff immediately whether an alert is grounded in dense data or sparse records."*

---

### 3. Cohort Dashboard & What-If Tuning (1:15 - 2:15 | 60s)
- **Screen:** `app/pages/1_Cohort_Dashboard.py`
- **Actions:** Adjust the Attendance Cut-off slider in What-If Tuning from 75% to 70%. Point out Cohort Action Effectiveness KPI tiles.
- **Spoken:**
  > *"On the Cohort Dashboard, coordinators see the entire cohort at a glance. Every status badge uses dual encoding—both color and distinct icons—to guarantee full accessibility.*
  >
  > *Notice our **What-If Threshold Tuning Panel**: If a coordinator wants to simulate what happens if we adjust the attendance cut-off from 75% down to 70%, they simply move the slider. The entire cohort recalculates dynamically in-memory with zero disk lookahead.
  >
  > *Below the roster, see our **Cohort-Level Action Effectiveness** tiles: We track the completion and perceived helpfulness of supportive actions in aggregate. To prevent student stigmatization, individual students are never evaluated or ranked by action feedback, and category breakdowns require at least 3 ratings."*

---

### 4. Student Deep-Dive: Gradual Decliner `S-0084` (2:15 - 3:30 | 75s)
- **Screen:** `app/Home.py` -> Click **"Inspect S-0084"** under Guided Demo (opens `app/pages/2_Student_Detail.py`).
- **Actions:** Scroll through trajectory small-multiples, "Why This Flag", and "What's Going Well".
- **Spoken:**
  > *"Let's click student **S-0084**, a Gradual Decliner.*
  >
  > *Observe the 3 small-multiples trajectory charts: weekly attendance against the 75% threshold line, the discrete assignment submission strip, and weekly quiz scores.*
  >
  > *Look at **'Why This Flag'**: There is zero black-box obscurity. Every triggered rule is stated in plain English: 'Recent attendance (68.0%) is below 75%'. Notice our **Persistence Rule**: Single-week dips are capped at Monitor; `S-0084` reached Suggest Outreach only because their concern held in 2 of the last 3 weekly snapshots.*
  >
  > *Beside it, see **'What's Going Well'**: We always emphasize student strengths. And our interpretable Logistic Regression model acts as a transparent cross-check, displaying its top-3 contributing factors in plain English."*

---

### 5. Correct False Alarm (`S-0031`), Record Action & View Audit (3:30 - 4:30 | 60s)
- **Screen:** Select **`S-0031`** (Strong-but-Irregular false positive trap).
- **Actions:** In the Staff Review panel, select Decision: `Dismissed`, Reason Code: `Strong performance elsewhere`, Reason Note: `High quiz scores; working full-time job`. Submit. Then open `app/pages/7_Audit_Log.py`.
- **Spoken:**
  > *"Now let's examine student **S-0031**, our classic false-positive trap: A student with irregular attendance but stellar quiz scores. Notice how Mitigating Rule M1 automatically protected them.*
  >
  > *Suppose a coordinator reviews this student. In the Staff Review panel, they select 'Dismissed (False Positive)' with reason code 'Strong performance elsewhere' and save.*
  >
  > *Immediately, **the coordinator's decision overrides the system across all pages**, resetting effective status to On Track!*
  >
  > *Now navigate to **7_Audit_Log**: Every single review, action, and export is permanently logged in an append-only ledger. We installed SQLite triggers that abort any UPDATE or DELETE statement. The audit trail is technically immutable."*

---

### 6. Evaluation Integrity & Earliness (4:30 - 5:00 | 30s)
- **Screen:** `app/pages/4_Evaluation.py`
- **Actions:** Point out the Multi-Seed Stability table, Earliness histogram, and Ablation Study.
- **Spoken:**
  > *"On our Evaluation page, we don't rely on a single lucky split. Our **Multi-Seed Stability** table evaluates 5 distinct synthetic seeds: SupportLens achieves a stable F1 of ~0.88 while capping alert burden under 22%, outperforming naive baselines.*
  >
  > *Look at the **Earliness Histogram**: Because we log true decline weeks in our ground-truth data, we measure that true-need students are detected on average **2.5 weeks before midterms**, providing ample window for supportive intervention.*
  >
  > *Our **Ablation Study** proves that removing Rule M1 or Persistence surges false positives by over 30%."*

---

### 7. Subgroup Fairness & Missing-Data Stress Test (5:00 - 5:30 | 30s)
- **Screen:** `app/pages/5_Fairness_and_Limits.py`
- **Actions:** Point to Full-time vs Part-time comparison and Missing Data Stress Test chart.
- **Spoken:**
  > *"Finally, on Fairness & Limits: Demographic attributes (`study_mode`, `cohort_group`) are strictly segregated from ML features and evaluated only here.*
  >
  > *We discovered that part-time students naturally register lower attendance due to jobs. A naive rule produces a 25.8% disparity gap. SupportLens's mitigating rules cut this gap down to 13.0%!*
  >
  > *And in our **Missing-Data Stress Test**, as missingness increases from 5% to 30%, the system never invents phantom alerts; it gracefully expands the Insufficient Data share and safely abstains.*
  >
  > *Thank you. We welcome your questions."*
