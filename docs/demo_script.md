# SupportLens: 5-Minute Competition Presentation & Demo Script

This script is designed for a concise, compelling 5-minute live demonstration of SupportLens to competition judges. It emphasizes ethics, transparent explainability, human oversight, and algorithmic rigor.

---

## ⏱️ Timeline Overview
- **0:00 - 0:30 (30s):** The Problem & Mandatory Ethical Guardrail
- **0:30 - 1:15 (45s):** Home Page, Synthetic Data, & Data Quality Telemetry
- **1:15 - 2:15 (60s):** Cohort Dashboard, Multi-Week Trends & Live What-If Tuning
- **2:15 - 3:30 (75s):** Student Deep-Dive (Gradual Decliner): Trajectory Small Multiples & Plain-English Explanations
- **3:30 - 4:15 (45s):** Human-in-the-Loop Override (Strong but Irregular) & Audit Log
- **4:15 - 4:45 (30s):** Test Evaluation: Beating Naïve Baselines & Controlled Alert Burden
- **4:45 - 5:15 (30s):** Subgroup Fairness (The Part-Time Disparity) & Responsible AI Charter

---

## 🎭 Step-by-Step Spoken Script

### 1. The Problem & Guardrails Banner (0:00 - 0:30)
> *"Hello judges. Course coordinators manage weekly data for hundreds of students: attendance, quiz scores, and assignments. They want to identify students who may need academic support early-before small setbacks turn into withdrawal.*  
> 
> *Here is the golden rule of **SupportLens**: **The system never makes academic decisions, penalties, holds, or grade changes.** Look at the permanent blue banner at the top of every screen: SupportLens is strictly a human-in-the-loop decision-support tool. It produces supportive follow-up suggestions that an authorized staff member must review."*

---

### 2. Home Page & Data Quality Ingestion (0:30 - 1:15)
> *"On the Home page, all data is **100% synthetic**. There are no real student names, emails, or personal identifiers-every student has an anonymized ID like `S-0042`.*  
> 
> *Notice our **Data Quality Telemetry**: Real educational data is messy. Ingestion sanitized 2 duplicates and clamped 2 out-of-range sensor errors to NaN. In SupportLens, **missing data is never treated as zero, and students are never silently dropped.** Our Data Confidence Score tells staff immediately whether an alert is grounded in dense data or sparse records."*

---

### 3. Cohort Dashboard & What-If Sliders (1:15 - 2:15)
*(Navigate to **1_Cohort_Dashboard**)*
> *"On the Cohort Dashboard, the coordinator has a complete multi-week overview. Notice our accessible badges: On Track, Monitor, Suggest Outreach, and Priority Check-in.*  
> 
> *Look at the **What-If Threshold Tuning Panel**: If the coordinator wants to see what happens if we tighten the attendance cut-off from 75% to 70%, they simply drag the slider. The entire cohort recalculates dynamically in-memory. This allows coordinators to test policy sensitivity without modifying underlying code."*

---

### 4. Student Deep-Dive: Gradual Decliner (2:15 - 3:30)
*(Navigate to **2_Student_Detail**, select Demo Case: 'Gradual Decliner')*
> *"Let's open a student exhibiting a **Gradual Decliner** pattern.*  
> 
> *Look at the three trajectory small-multiples: attendance against the 75% dashed line, the discrete assignment status strip, and weekly quiz scores.*  
> 
> *Now, look at the **'Why This Flag'** panel: There is zero black-box mysticism. Every triggered rule is stated in plain English with observed metrics compared directly against thresholds: 'Recent attendance (68.0%) is below 75%'.*  
> 
> *Beside it, look at **'What's Going Well'**: We always highlight student strengths, such as strong early-term presence or solid quiz scores. And our interpretable Logistic Regression model acts as a secondary cross-check, with top contributing factors displayed in plain English."*

---

### 5. Staff Review & Decision Override (3:30 - 4:15)
*(Select Demo Case: 'Strong but Irregular (False Positive Trap)')*
> *"Now let's examine our false-positive trap: A student with low attendance but stellar 88% quiz scores. Our mitigating rule M1 automatically cushioned them.*  
> 
> *Staff can now open the **Staff Review Panel**: They select 'Dismissed (False Positive)' with reason code 'Strong performance elsewhere', and record a supportive note. When saved, **the coordinator's decision immediately overrides the system status to 'On Track' across all dashboards**!*  
> 
> *Every single review is committed to an immutable SQLite audit log-creating full institutional accountability."*

---

### 6. Test Evaluation & Baselines (4:15 - 4:45)
*(Navigate to **4_Evaluation**)*
> *"On the Evaluation page, we benchmarked SupportLens against two industry baselines: 'Attendance < 75% only' and 'Quiz < 50% only'.*  
> 
> *The single-signal baselines produce terrible alert fatigue. SupportLens achieves an **F1 score of 0.88** while capping total cohort alert burden at **19%**. And our **Earliness Metric** shows true-need students are detected by **Week 5.8**-weeks before midterms."*

---

### 7. Fairness & Limitations (4:45 - 5:15)
*(Navigate to **5_Fairness_and_Limits**)*
> *"Finally, our **Subgroup Fairness Audit**: Part-time students naturally register lower physical attendance due to work commitments. A naive attendance cut-off produces a 14% demographic disparity. Our mitigating rules and compound persistence bring this back within a fair 5% parity window.*  
> 
> *Our charter in `FAIRNESS_LIMITATIONS.md` documents what the tool can and cannot do: it does not measure private emotional health, and absence of a flag does not replace compassionate human pastoral care.*  
> 
> *SupportLens gives course coordinators the clarity of AI, backed by the compassion of human oversight. Thank you."*
