# 🔐 Datathon Anonymizer

> Local and portable tool for preparing anonymized clinical datasets for health datathons.

**[🇪🇸 Castellano](docs/README.es.md) · [🇨🇦 Català](docs/README.ca.md)**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What is it?

A web application **deployable locally with a single Docker command** that allows any healthcare centre to:

1. Upload a clinical CSV in standard long format
2. Classify variables as quasi-identifiers or non-identifying
3. Define generalizations for each quasi-identifier
4. Apply **k-anonymity** with suppression of non-conforming records
5. Download the anonymized dataset and a **complete report** for the Data Protection Officer

No data leaves the server. Everything runs locally, with no dependency on external services.

---

## Quick start

```bash
# 1. Clone the repository
git clone https://github.com/PepICS/datathon-anonymizer.git
cd datathon-anonymizer

# 2. Start the application
docker compose up --build -d

# 3. Open your browser
# → http://localhost:8000
```

To stop:

```bash
docker compose down
```

> **Custom port**: edit the left-hand port in `docker-compose.yml` (e.g. `"8092:8000"`)

---

## Input CSV format

The file must have **exactly 4 columns** in long format:

| Column | Accepted names | Description |
|--------|---------------|-------------|
| `pacient` | `patient_id`, `pacient_id`, `nhc`, `pid` | Unique patient identifier |
| `data` | `date`, `fecha`, `datetime`, `timestamp` | Visit or observation date |
| `item` | `variable`, `var`, `field`, `measure` | Clinical variable name |
| `valor` | `value`, `val`, `resultat`, `result` | Observed value |

The application automatically detects column name variants and normalises them internally.

### Example rows

```csv
patient_id,data,variable,valor
P0001,2023-02-15,estado_cognitivo,deterioro_leve
P0001,2023-02-15,edad,67
P0001,2023-02-15,fragilidad,fragil
P0001,2023-03-28,estado_cognitivo,deterioro_moderado
```

---

## Application flow

```
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐
│  1. Upload   │───▶│ 2. Classification│───▶│ 3. Generalization│───▶│ 4. K-anon.  │
│  CSV + profile│   │ QI / non-ID      │    │ bins / categories│    │ + results   │
└──────────────┘    └──────────────────┘    └──────────────────┘    └──────────────┘
```

### Phase 1 — Upload and profiling

- Accepts UTF-8, Latin-1, CP1252 encodings
- Automatically detects variable type (numeric vs. categorical)
- Shows statistics, value distribution and data preview

### Phase 2 — Variable classification

For each variable, the user indicates its role:

| Role | Automatic treatment |
|------|---------------------|
| 🔑 Direct identifier (`pacient`) | Irreversible SHA-256 hash (prefix `H-`) |
| 📅 Date (`data`) | Integer delta: days since each patient's first visit |
| 🔍 Quasi-identifier | User-defined generalization + k-anonymity |
| ✅ Non-identifying | No changes |

### Phase 3 — Generalizations

For each quasi-identifier, the user defines how to group values:

- **Numeric variables** → custom intervals (e.g. age → `0-17`, `18-39`, `40-64`, `65+`)
- **Categorical variables** → mapping of original values to broader groups

Missing values (NaN) are automatically imputed:
- Categorical → `Desconocido`
- Numeric → median of the observed set

### Phase 4 — K-anonymity and results

- **Preview simulation**: shows the impact of k=2, 3, 4, 5 before running
- **Parameter k**: every quasi-identifier combination must appear in ≥ k patients
- **Suppression**: patients in groups below k are removed from the final dataset
- **Metrics**: patient flow, equivalence class distribution, suppressed groups

---

## Security guarantees

The protection offered by this process rests on **three independent and complementary layers**:

### Layer 1 — Technical (applied transformations)

| Transformation | Protection |
|---------------|------------|
| SHA-256 hash on patient ID | Irreversible pseudonymisation |
| Date → integer delta | Absolute dates destroyed |
| Quasi-identifier generalization | Cross-linkage granularity eliminated |
| K-anonymity | Mathematical impossibility of singling out |

### Layer 2 — Statistical (sampling uncertainty)

The datathon dataset is a **random sample** of a much larger population. A potential attacker cannot know a priori whether a specific individual is in the dataset at all. This uncertainty — recognised by ENISA and the Article 29 Working Party as a re-identification risk mitigating factor — makes any re-identification attempt speculative and unreliable, regardless of the attacker's background knowledge.

### Layer 3 — Organizational (datathon environment)

- **Accredited participants**: access restricted to a pre-selected, registered group
- **Data Use Agreement**: all participants sign a binding commitment prohibiting any re-identification attempt
- **Secure infrastructure**: event hosted on **Instituto de Salud Carlos III (Madrid)** servers, managed by qualified ISCIII staff
- **Closed environment**: data cannot be extracted outside the controlled systems

> The combination of these three layers provides protection **substantially above** what GDPR and ENISA guidelines require for health research data.

---

## Generated outputs

| File | Format | For |
|------|--------|-----|
| `*_anonymized.csv` | CSV | Datathon participants |
| `*_report.html` | Styled HTML | DPO (printable as PDF from browser) |
| `*_report.md` | Markdown | Repository / technical documentation |
| `anonymization_report.json` | JSON | Audit and traceability |

### DPO report

The HTML report (printable as PDF via Ctrl+P) includes:

1. Executive summary with key metrics
2. Original dataset description
3. Applicable legal framework (GDPR, LOPDGDD, Art. 29 WP Opinion 05/2014)
4. Description of all applied transformations
5. Results and equivalence class distribution
6. Three-layer security guarantee analysis
7. Technical certification checklist

---

## Repository structure

```
datathon-anonymizer/
│
├── app/
│   ├── main.py                    # FastAPI: endpoints and session management
│   └── modules/
│       ├── anonymizer.py          # All anonymization logic
│       ├── report_md.py           # Markdown report generation (ca/es/en)
│       └── report_html.py         # Markdown → styled HTML conversion
│
├── static/
│   ├── index.html                 # 4-phase wizard interface
│   ├── css/styles.css             # Styles (clinical dark mode)
│   └── js/
│       ├── app.js                 # Frontend logic (vanilla JS)
│       └── i18n.js                # Translations: Catalan, Spanish, English
│
├── docs/
│   ├── README.es.md               # Spanish README
│   └── README.ca.md               # Catalan README
│
├── sample_data/
│   ├── dataset_500p.csv           # Synthetic dataset — 500 patients
│   ├── dataset_2000p.csv          # Synthetic dataset — 2,000 patients
│   └── Cataluña_Unificado.xlsx    # Reference clinical variables Excel
│
├── generate_synthetic.py          # Script to regenerate synthetic datasets
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Technical architecture

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Pure HTML/CSS/JS (no frameworks) |
| Container | Docker + Docker Compose |
| Python dependencies | pandas, numpy, fastapi, uvicorn, markdown |
| Session state | In-memory (not persisted) |
| Communication | REST JSON API |

The application has no database, uses no tracking cookies, and generates no persistent logs containing uploaded file data.

---

## Multilingual

The interface is available in **Catalan**, **Spanish** and **English**. Language is selected with the sidebar buttons and affects both the interface and the generated reports.

---

## Synthetic dataset generation

The `generate_synthetic.py` script generates test datasets by reading variables directly from the reference Excel:

```bash
# From inside the Docker container:
docker exec datathon-anonymizer python3 generate_synthetic.py

# Or locally with Python:
python3 generate_synthetic.py
```

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/) ≥ 24.0
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.0
- No other dependencies on the host

---

## Legal framework

This project supports compliance with:

- **GDPR (EU Regulation 2016/679)** — Art. 89 and Recital 26 on processing for research
- **LOPDGDD (LO 3/2018)** — Spanish transposition of GDPR
- **Article 29 Working Party Opinion 05/2014** — k-anonymity as a recognised technique
- **ENISA guidelines** on health data anonymization

> ⚠️ This tool facilitates the technical process, but responsibility for variable classification and report validation rests with the centre's Data Protection Officer.

---

## Licence

MIT — Free for use, modification and distribution. Attribution appreciated.

---

## Contributions

Pull requests welcome. For major changes, please open an issue first.

---

*Built for healthcare centres wishing to participate in datathons while protecting their patients' privacy.*
