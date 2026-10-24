# SupportLens Dataset Card

## 1. Overview and Intended Use
SupportLens is a prototype academic early-warning and supportive outreach system designed for course coordinators. 
The accompanying dataset is **100% synthetic**, designed strictly for demonstration, evaluation, and algorithmic auditing.

- **Primary Purpose:** Enable staff to identify students experiencing academic difficulty early in a semester so compassionate, supportive check-ins can be initiated.
- **Explicit Non-Goals:** 
  - **No automated punishments, penalties, or disciplinary actions.**
  - **No automated grading, academic standing alterations, or course drops.**
  - **No personal identification or profiling.**

---

## 2. Privacy & Data Ethics Policy
> **Strict Privacy Guarantee:** No real student data, names, emails, phone numbers, addresses, institutional IDs, IP addresses, gender, ethnicity, or real-world demographic records were used or generated.

- All student identifiers follow a randomly shuffled synthetic format (`S-0001` to `S-0100`).
- Any categorical groupings (`cohort_group`: Section A, Section B, Section C; `study_mode`: Full-time, Part-time) are synthetic attributes provided exclusively for fairness auditing and subgroup sensitivity testing.
- The `ground_truth_support_need` labels exist purely for offline evaluation and algorithmic verification. In a real deployment, no such oracle labels exist; coordinator review decisions provide the human-in-the-loop feedback signal.

---

## 3. Data Schema

### 3.1 `students.csv` (100 rows)
| Column Name | Type | Description |
|---|---|---|
| `student_id` | String | Anonymised unique identifier (e.g., `S-0042`), randomly permuted. |
| `cohort_group` | Categorical | Neutral section assignment (`Section A`, `Section B`, `Section C`). Used only for fairness auditing. |
| `study_mode` | Categorical | Synthetic study mode (`Full-time`, `Part-time`). Used for fairness checks. |
| `prior_support_flag` | Boolean | Synthetic indicator of prior campus service usage. Never input to scoring models. |

### 3.2 `weekly_records.csv` (1,200 rows)
One record per student per week (Weeks 1 to 12).
| Column Name | Type | Description |
|---|---|---|
| `student_id` | String | References `students.csv`. |
| `week` | Integer | Week number (1 to 12). |
| `attendance_pct` | Float | Percentage attendance in scheduled sessions (0.0 to 100.0%). |
| `assignment_status` | Categorical | One of `Submitted`, `Late`, `Missing`, or `Not Due`. |
| `quiz_score` | Float / Null | Percentage score on weekly quizzes (0.0 to 100.0) or `null` if no quiz or missed. |
| `quiz_taken` | Boolean | Indicates whether the student attempted the quiz that week. |

### 3.3 `ground_truth_support_need.csv` (100 rows)
| Column Name | Type | Description |
|---|---|---|
| `student_id` | String | References `students.csv`. |
| `archetype` | String | Latent archetype driving generation (hidden from predictive algorithms). |
| `needs_support` | Binary (0/1) | Synthetic ground truth flag used strictly for model evaluation and test comparisons. |

---

## 4. Latent Student Archetypes
To ensure realistic behavioral trajectories while keeping individual records synthetic, data is simulated using seven behavioral archetypes:

1. **Steady Performer (50%):** Consistently high attendance (88-98%), timely submissions, quiz averages 75-90%.
2. **Average / Variable (20%):** Moderate attendance (75-90%), occasional late submissions, quiz averages 60-75%.
3. **Gradual Decliner (10%):** Strong start with noticeable downward drift in attendance and quiz scores starting weeks 4-6.
4. **Chronic Low Engagement (8%):** Low baseline attendance (40-65%), frequent missing assignments, depressed quiz scores.
5. **Sudden Dropper (5%):** Normal engagement until weeks 7-8, followed by a precipitous drop in attendance and missed deliverables.
6. **Strong but Irregular (4%):** Low attendance due to independent study or conflicting schedules, but excellent quiz performance and on-time submissions. (*Serves as an essential false-positive test case*).
7. **Recovering (3%):** Disengaged early in the term, followed by marked improvement from week 5 onwards. (*Serves as a test case against over-flagging recovered students*).

---

## 5. Realistic Data Messiness & Injected Anomalies
Real educational data is imperfect. The synthetic generator explicitly injects:
- **~5% missing attendance records** across the semester.
- **~8% unrecorded quiz scores** in weeks where quizzes took place.
- **Extended absence gaps:** 4 students with 3+ consecutive weeks of missing data.
- **Late enrolments:** 3 students who joined the course after week 3.
- **Injected data anomalies:** Out-of-bounds values (attendance > 100%, quiz < 0%) and duplicated rows to demonstrate data cleaning, sanitization, and automated quality reporting.

---

## 6. Reproducibility
The dataset can be deterministically reproduced using:
```bash
python -m src.data_generator --seed 42 --output_dir data
```
All random number generators in NumPy and Python's random library are fixed to seed `42`.
