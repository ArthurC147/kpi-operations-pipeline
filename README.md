# KPI Operations Pipeline

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=flat-square&logo=powerbi&logoColor=black)
![Power Automate](https://img.shields.io/badge/Power%20Automate-0066FF?style=flat-square&logo=microsoftpowerautomate&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

> End-to-end automated pipeline that collects, processes, and visualizes Customer Success KPIs — eliminating manual consolidation and enabling real-time executive dashboards.

---

## Business context

Customer Success teams in enterprise telecom environments track dozens of KPIs across multiple systems (CRM, ticketing, billing). Without automation, analysts spend hours each week manually downloading reports, consolidating spreadsheets, and reformatting data — work that adds no analytical value.

This project replicates that problem using a real-world public dataset and solves it with an automated Python pipeline feeding a Power BI dashboard.

**Outcome modeled after real implementation:** a similar pipeline at Telefônica Vivo reduced manual processing time by **30%** and eliminated consolidation errors across the Customer Success team.

---

## Problem → Solution → Result

| | |
|---|---|
| **Problem** | KPI reports built manually from 3+ data sources; 3–4 hours/week of analyst time wasted on data wrangling |
| **Solution** | Python pipeline (Pandas) that ingests raw CSVs, cleans and transforms data, outputs a single structured file; Power BI DAX measures for real-time KPI calculation |
| **Result** | −30% processing time · zero consolidation errors · dashboard refreshes automatically |

---

## Dataset

**Source:** [Customer Support Ticket Dataset — Kaggle](https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset)

This dataset contains ~8,000 customer support tickets with fields including ticket type, status, resolution time, customer satisfaction score, and product category — a realistic proxy for enterprise telecom support KPIs.

```
data/
├── raw/
│   └── customer_support_tickets.csv     ← original Kaggle file (unmodified)
└── processed/
    └── kpi_processed.csv                ← output from the pipeline
```

> **Privacy note:** all data is publicly available from Kaggle. No real customer data is used.

---

## Pipeline architecture

```
[Raw CSV] → [01_coleta.ipynb] → [02_tratamento.ipynb] → [03_analise.ipynb] → [kpi_processed.csv] → [Power BI Dashboard]
```

Each notebook handles one stage:

| Notebook | What it does |
|---|---|
| `01_coleta.ipynb` | Loads raw data, inspects shape/types/nulls, produces a first diagnostic |
| `02_tratamento.ipynb` | Cleans nulls, standardizes columns, engineers KPI features (MTTR, CSAT bins, SLA flag) |
| `03_analise.ipynb` | Aggregates KPIs by product, channel, and period; exports `kpi_processed.csv` |
| `scripts/main.py` | Runs the full pipeline end-to-end from the command line |

---

## Key KPIs computed

- **MTTR** (Mean Time to Resolution) — average hours to close a ticket
- **CSAT** (Customer Satisfaction Score) — average rating per product/channel
- **SLA Compliance Rate** — % of tickets resolved within the SLA threshold
- **Volume Trend** — ticket volume by week/month for capacity planning
- **Resolution Rate** — % of open vs closed tickets

---

## Project structure

```
kpi-operations-pipeline/
├── data/
│   ├── raw/
│   │   └── customer_support_tickets.csv
│   └── processed/
│       └── kpi_processed.csv
├── notebooks/
│   ├── 01_coleta.ipynb
│   ├── 02_tratamento.ipynb
│   └── 03_analise.ipynb
├── scripts/
│   └── main.py
├── dashboard/
│   └── kpi_dashboard.pbix
├── docs/
│   └── screenshots/
│       ├── dashboard_overview.png
│       └── pipeline_output.png
├── requirements.txt
└── README.md
```

---

## How to run

### 1. Clone the repository

```bash
git clone https://github.com/ArthurC147/kpi-operations-pipeline.git
cd kpi-operations-pipeline
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Download the dataset

Go to [this Kaggle page](https://www.kaggle.com/datasets/suraj520/customer-support-ticket-dataset), download `customer_support_tickets.csv`, and place it in `data/raw/`.

### 4. Run the pipeline

**Option A — notebooks (recommended for learning):**
```bash
jupyter notebook
# Open notebooks in order: 01 → 02 → 03
```

**Option B — full pipeline via script:**
```bash
python scripts/main.py
```

The output file `data/processed/kpi_processed.csv` will be ready to connect to Power BI.

### 5. Open the dashboard

Open `dashboard/kpi_dashboard.pbix` in Power BI Desktop and point the data source to `data/processed/kpi_processed.csv`.

---

## Dependencies

```
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
openpyxl>=3.1.0
jupyter>=1.0.0
```

---

## What I learned

- Structuring a data pipeline with clear stage separation (ingest → clean → analyze) makes debugging and iteration much faster
- DAX calculated measures in Power BI are more maintainable than pre-aggregating everything in Python — keep aggregation logic in the BI layer when the audience will filter interactively
- Engineering a "SLA flag" column at the transformation stage (rather than computing it in DAX) reduces dashboard query time significantly
- Documenting each transformation decision in the notebook (with comments explaining *why*, not just *what*) made it much easier to revisit the project weeks later

---

## Author

**Arthur Cardoso** — Industrial Engineering @ UFPR

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/arthur-cardoso-b3b1ba1ab)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)](https://github.com/ArthurC147)
