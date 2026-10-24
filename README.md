# SupportLens

SupportLens is an early-warning academic support dashboard that helps course coordinators identify students who may benefit from academic assistance. The system uses synthetic data, interpretable rules, and machine learning to produce supportive recommendations. Human review is required before any outreach, and the system never issues automated academic penalties or grades.

## Key Features

- Synthetic dataset of 100 students across 12 weeks with anonymized identifiers.
- Transparent rule engine with defined concern categories (Attendance, Submission, Assessment, Compound).
- Machine learning cross-check using Logistic Regression and Shallow Decision Trees.
- Staff review panel to confirm, correct, or dismiss flags, with reasons recorded in an audit log.
- Human decision overrides: coordinator reviews always supersede system recommendations.
- Interactive multi-page Streamlit application with trajectory charts and what-if threshold simulation.
- Comprehensive evaluation against synthetic ground truth and baselines, with subgroup fairness audits.

## Requirements

- Python 3.11+
- Dependencies listed in requirements.txt (streamlit, pandas, numpy, scikit-learn, plotly, pyyaml, pytest, joblib)

## Quick Start

### 1. Set Up Virtual Environment

On Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Or on macOS / Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

Install packages:
```bash
pip install -r requirements.txt
```

### 2. Generate Synthetic Data

```bash
python -m src.data_generator --seed 42
```

Directly via virtual environment on Windows:
```powershell
.venv\Scripts\python -m src.data_generator --seed 42
```

### 3. Run the Dashboard

```bash
streamlit run app/Home.py
```

Directly via virtual environment on Windows:
```powershell
.venv\Scripts\python -m streamlit run app/Home.py
```

Open http://localhost:8501 in your browser.

### 4. Run Tests

```bash
pytest -v
```

Directly via virtual environment on Windows:
```powershell
.venv\Scripts\python -m pytest -v
```

## Repository Structure

- `app/`: Streamlit dashboard pages and reusable UI components.
- `src/`: Data generation, data quality, feature engineering, rules engine, ML models, review store, evaluation, fairness, and export modules.
- `data/`: Synthetic dataset CSV files and model artifacts.
- `tests/`: Automated unit tests for data generation, features, rules, review store, and ethical guardrails.
- `config.yaml`: Transparent rule thresholds, mitigating factors, and scoring levels.
- `DATA_CARD.md`: Dataset schema, latent student archetypes, and privacy guarantees.
- `FAIRNESS_LIMITATIONS.md`: Analysis of false positives, missing data handling, and subgroup fairness audits.

## Ethical Guardrails

- All student records use synthetic data with randomized IDs (S-0001 to S-0100).
- Demographic attributes are never used as model inputs and are restricted to fairness auditing.
- Wording across the platform is strictly supportive rather than punitive.
- Coordinators must review flags before any outreach is initiated.
