# SupportLens: Judge Q&A & Defensibility Guide

This document contains authoritative, concise answers to anticipated judge questions regarding algorithmic ethics, technical design decisions, and system validation.

---

### Q1: "Isn't evaluating your model on synthetic data overly optimistic?"
**Answer:**  
Yes, and we state this transparently in our **Label-Circularity Honesty Check** on the Evaluation page and in Section 5 of [FAIRNESS_LIMITATIONS.md](../FAIRNESS_LIMITATIONS.md).  
In our synthetic generator:
- Ground-truth labels derive from latent behavioral archetypes (and a small probability tied to realized low values for "Average/variable"), **never from rule thresholds**.
- However, simulated data lacks the full chaos, social factors, and multi-modal noise of real universities.
- Therefore, our measured accuracy metrics (F1 ~0.88 across 5 random seeds) represent an upper bound. The multi-seed evaluation and missing-data stress tests demonstrate stability under perturbation, but local calibration on institutional data is mandatory before live deployment.

---

### Q2: "How does SupportLens technically prevent punitive or disciplinary use?"
**Answer:**  
Through multi-layered technical, architectural, and data safeguards:
1. **No Automated Enforcement:** There is zero code path capable of modifying a student's grade, enrollment status, financial aid, or academic standing.
2. **Prohibited Decisions Blocked:** Any attempt to enter punitive terms (`penalise`, `fail`, `punish`, `misconduct`, `disciplinary`, `drop student`) in code, explanations, review decisions, or action forms raises an immediate error.
3. **Mandatory Human-in-the-Loop:** Automated emails or notifications to students are completely blocked. Flags are only visible to coordinators as recommendations for supportive outreach.
4. **Permanent Guardrail Banner:** A non-dismissible banner reminding staff of ethical non-punitive bounds is permanently displayed on every single screen.

---

### Q3: "How does the system handle missing data without penalizing students?"
**Answer:**  
By enforcing our core principle: **"Missing is Never Zero."**
1. **No Zero Imputation:** When attendance or quiz records are blank, standard systems often impute zero, manufacturing artificial crises. SupportLens averages strictly over available valid observations.
2. **Data Confidence Scoring:** Every student receives a continuous data confidence score ($0.0$ to $1.0$). If records are sparse ($<0.60$), the engine caps the support level at **Monitor** with an **Insufficient Data** advisory rather than escalating to high-urgency alerts.
3. **Graceful Degradation:** In our Phase C stress test, injecting up to 30% synthetic missing data caused the Insufficient Data share to expand gracefully while the false positive rate remained bounded below 1.5%, proving the system abstains rather than inventing spurious flags.

---

### Q4: "How do you handle false positives and avoid coordinator alert fatigue?"
**Answer:**  
Through five deliberate architectural dampeners:
1. **Mitigating Rule M1 (Mastery Dampener):** High quiz scores ($\ge 80\%$) offset attendance penalties by $-2$ points, protecting independent learners.
2. **Mitigating Rule M2 (Positive Trajectory):** Positive upward momentum in recent weeks offsets historical deficits.
3. **Multi-Week Persistence:** A single-week dip is capped at `Monitor` ("Watching: single-week signal"). Escalation to `Suggest Outreach` requires concern across at least 2 of the last 3 weekly snapshots.
4. **Staff Review Override:** A coordinator can dismiss a false positive with one click. Their decision immediately overrides the system across all cohort dashboards and resets effective status to `On Track`.
5. **Continuous Feedback Loop:** Dismissal analytics track per-rule false alarm rates; any rule dismissed in $>30\%$ of reviews triggers a threshold recalibration notice.

---

### Q5: "Why did you choose a dual Rules + ML architecture instead of pure deep learning?"
**Answer:**  
Because high-stakes educational decisions require **interpretability and trust**:
1. **Explainability First:** Pure neural networks cannot provide legally and ethically defensible plain-English explanations. Our rules engine allows coordinators to see the exact thresholds and numbers that triggered a signal.
2. **ML as a Cross-Check:** We use a balanced Logistic Regression model not to drive the primary flag, but to provide a secondary sanity check and agreement badge.
3. **Disagreement Triage:** The Review Queue highlights "Worth a Second Look" cases where Rules and ML diverge, prompting coordinators to spend their limited time on ambiguous borderline cases.

---

### Q6: "What fairness disparities did your audit uncover, and how did you mitigate them?"
**Answer:**  
During subgroup audits across `study_mode`, we discovered that **part-time students naturally exhibit lower physical attendance** because they balance off-campus employment and caregiving, despite demonstrating equal quiz scores and submission rates.
- Under a naive attendance threshold ($<75\%$), part-time students suffered a **25.8 percentage point flag-rate disparity**.
- SupportLens mitigating rules (M1 mastery and M2 trajectory) successfully cut this demographic parity gap down to **13.0%** (a 12.8 point reduction).
- Group attributes are strictly barred from ML training and feature engineering to ensure algorithms operate purely on behavioral engagement telemetry.
