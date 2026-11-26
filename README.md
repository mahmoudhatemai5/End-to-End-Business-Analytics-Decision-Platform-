<div align="center">

# 🛒 End-to-End Business Analytics & Decision Platform

### From raw SQL to a deployed decision-support system, built on the Olist Brazilian E-Commerce dataset

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![SQL](https://img.shields.io/badge/SQL-PostgreSQL-336791?logo=postgresql&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-Dashboards-F2C811?logo=powerbi&logoColor=black)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

</div>

---

## 📑 Table of Contents

1. [Project Overview](#-project-overview)
2. [Business Problem & Objectives](#-business-problem--objectives)
3. [Dataset](#-dataset)
4. [System Architecture](#-system-architecture)
5. [Project Phases](#-project-phases)
6. [Tech Stack](#-tech-stack)
7. [Repository Structure](#-repository-structure)
8. [Getting Started](#-getting-started)
9. [Key Business Questions](#-key-business-questions)
10. [Deep Learning Components](#-deep-learning-components)
11. [Dashboards](#-dashboards)
12. [Deployment](#-deployment)
13. [Results & Key Insights](#-results--key-insights)
14. [Team](#-team)
15. [Roadmap](#-roadmap)
16. [License & Acknowledgements](#-license--acknowledgements)

---

## 📌 Project Overview

This is our **graduation project**: a complete analytics platform that follows the real-world data lifecycle end to end, starting from **raw CSV files and SQL database design** and finishing with a **deployed, containerized decision-support application**.

Instead of stopping at charts, the platform turns e-commerce data into **actionable decisions** for sellers, operations, and management: where revenue comes from, why deliveries are late, which customers are about to churn, and what drives customer satisfaction.

**What makes this project end-to-end:**

| Layer | What we build |
|---|---|
| 🗄️ Data Engineering | Relational schema, data loading, ETL, data warehouse (star schema) |
| 🔍 Analytics | SQL analysis, EDA, KPI definitions |
| 🤖 Deep Learning | Neural networks for prediction, forecasting & NLP |
| 📊 Business Intelligence | Interactive Power BI dashboards |
| 🚀 Deployment | API + web app, Docker, CI/CD |

---

## 🎯 Business Problem & Objectives

Olist is a Brazilian marketplace connecting small merchants to customers through a single storefront. Like any marketplace, it must balance **revenue growth, delivery performance, seller quality, and customer satisfaction**.

**Objectives**

- Build a clean, reliable **data foundation** from the raw Olist tables.
- Measure business performance through well-defined **KPIs** (revenue, AOV, delivery time, review score, repeat rate).
- Identify **root causes** of late deliveries and low review scores.
- **Segment customers** to support targeted marketing and retention.
- **Predict** delivery delays and customer satisfaction before they hurt the business.
- Deliver insights through **dashboards and a deployed app** that non-technical stakeholders can use.

---

## 📊 Dataset

**Source:** [Brazilian E-Commerce Public Dataset by Olist (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

The dataset contains information on about **100,000 orders placed between 2016 and 2018** across multiple Brazilian marketplaces. It covers the full order lifecycle: purchase, payment, shipping, delivery, and customer review. All data is anonymized.

### Tables

| File | Description | Key columns |
|---|---|---|
| `olist_orders_dataset.csv` | Core orders table with status and timestamps | `order_id`, `customer_id`, `order_status`, purchase / approved / delivered / estimated delivery dates |
| `olist_order_items_dataset.csv` | Items within each order | `order_id`, `product_id`, `seller_id`, `price`, `freight_value` |
| `olist_order_payments_dataset.csv` | Payment details | `order_id`, `payment_type`, `payment_installments`, `payment_value` |
| `olist_order_reviews_dataset.csv` | Customer reviews | `review_id`, `order_id`, `review_score`, `review_comment_message` |
| `olist_customers_dataset.csv` | Customer information | `customer_id`, `customer_unique_id`, `customer_city`, `customer_state` |
| `olist_sellers_dataset.csv` | Seller information | `seller_id`, `seller_city`, `seller_state` |
| `olist_products_dataset.csv` | Product attributes | `product_id`, `product_category_name`, weight, dimensions |
| `olist_geolocation_dataset.csv` | Brazilian zip codes with coordinates | `geolocation_zip_code_prefix`, `lat`, `lng` |
| `product_category_name_translation.csv` | Portuguese → English category names | `product_category_name`, `product_category_name_english` |

### Entity Relationship (high level)

```
customers ──< orders >── order_payments
                │
                ├──< order_items >── products ── category_translation
                │          │
                │          └────── sellers
                └──< order_reviews

customers / sellers ── geolocation (via zip code prefix)
```

> **Note:** `customer_id` is unique per order, while `customer_unique_id` identifies the actual person. Repeat-purchase analysis must use `customer_unique_id`.

> Raw data is **not committed** to this repository because of size. Download it from Kaggle and place it in `data/raw/` (see [Getting Started](#-getting-started)).

---

## 🏗️ System Architecture

```
┌──────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────┐
│  Raw CSVs    │──▶│  Staging DB  │──▶│  Data Warehouse│──▶│ Analytics &  │
│  (Kaggle)    │   │  (SQL)       │   │  (Star Schema) │   │ DL Features  │
└──────────────┘   └──────────────┘   └────────────────┘   └──────┬───────┘
                      ETL (Python)                                  │
                                                  ┌─────────────────┼─────────────────┐
                                                  ▼                 ▼                 ▼
                                           ┌────────────┐   ┌─────────────┐   ┌─────────────┐
                                           │ Power BI   │   │ DL Models   │   │ REST API    │
                                           │ Dashboards │   │ (Training)  │   │ (FastAPI)   │
                                           └────────────┘   └─────────────┘   └──────┬──────┘
                                                                                     ▼
                                                                             ┌──────────────┐
                                                                             │ Web App      │
                                                                             │ (Streamlit)  │
                                                                             └──────────────┘
                                         Docker  ·  GitHub Actions CI/CD  ·  Cloud Deployment
```

---

## 🧭 Project Phases

### Phase 1: Database Design & SQL
- Design the relational schema with primary and foreign keys.
- Load all nine CSV files into the database.
- Data quality checks: nulls, duplicates, orphan keys, invalid timestamps.
- Core analytical SQL: joins, CTEs, window functions, aggregations.

### Phase 2: ETL & Data Warehouse
- Python ETL pipeline: extract → clean → transform → load.
- Handle missing values, fix data types, standardize category names (using the translation table).
- Feature engineering: delivery time, delay days, order value, freight ratio, review sentiment.
- Build a **star schema**: `fact_orders`, `fact_order_items`, with `dim_customer`, `dim_seller`, `dim_product`, `dim_date`, `dim_payment`, `dim_geo`.

### Phase 3: Exploratory Data Analysis
- Univariate, bivariate, and time-series analysis.
- Seasonality, geography, category, and payment behavior.
- Delivery and review relationship analysis.

### Phase 4: Deep Learning
- Three simple neural networks: delivery delay prediction, review score prediction, and sales forecasting (see [DL section](#-deep-learning-components)).

### Phase 5: Business Intelligence
- KPI definitions and DAX measures.
- Multi-page interactive Power BI dashboards.

### Phase 6: Deployment
- Serve models through a REST API.
- Streamlit app for end users.
- Containerize with Docker and automate with CI/CD.

---

## 🛠️ Tech Stack

| Area | Tools |
|---|---|
| **Database** | PostgreSQL (or MySQL), SQLAlchemy |
| **ETL & Data Processing** | Python, Pandas, NumPy |
| **Analysis & Visualization** | Jupyter, Matplotlib, Seaborn, Plotly |
| **Deep Learning** | TensorFlow / Keras |
| **ML Utilities** | Scikit-learn (preprocessing, baselines, evaluation metrics) |
| **Business Intelligence** | Power BI (DAX, Power Query) |
| **API & App** | FastAPI, Streamlit |
| **DevOps** | Docker, Docker Compose, GitHub Actions |
| **Version Control** | Git & GitHub |

---

## 📁 Repository Structure

What is in this repository today:

```
End-to-End-Business-Analytics-Decision-Platform-/
│
├── app/
│   └── streamlit_app_all_problems.py      # Streamlit app (4 problems, one tab each)
├── notebooks/
│   ├── olist_all_problems_mlflow.ipynb    # Full modelling notebook (MLflow tracking)
│   └── mlflow.db                          # MLflow tracking database (SQLite)
├── artifacts/
│   ├── app_extra.joblib                   # Extra lookup data used by the app
│   └── v2/                                # Trained models + preprocessing used by the app
│       ├── prep_v2.py
│       ├── preprocess_v2.joblib
│       ├── delay_v2.joblib
│       ├── freight_v2.joblib
│       ├── days_v2.joblib
│       ├── satisfaction_v2.joblib
│       └── review_text_model.joblib
├── dashboards/
│   └── DEPI FINAL PROJECT POWER done1.pbix   # Power BI dashboard
├── requirements.txt
├── .gitignore
└── README.md
```

The raw Olist CSVs are **not** stored in this repo. Download them from Kaggle (see below) into `data/raw/`, which is git-ignored.

> The sections above (SQL, ETL, API, Docker, CI/CD) describe the planned full platform. The folders in the tree above are what is actually included.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ (or MySQL 8+)
- Docker & Docker Compose (optional, recommended)
- Power BI Desktop (to open the dashboards)

### 1. Clone the repository

```bash
git clone https://github.com/mahmoudhatemai5/End-to-End-Business-Analytics-Decision-Platform-.git
cd End-to-End-Business-Analytics-Decision-Platform-
```

### 2. Set up the environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Download the data

Download the dataset from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and extract all CSV files into `data/raw/`.

Or with the Kaggle CLI:

```bash
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
```

### 4. Run the Streamlit app

Run from the repository root (the app loads the models from `artifacts/v2` relative to the working directory):

```bash
streamlit run app/streamlit_app_all_problems.py
```

The app has one tab per problem: delivery delay, freight cost, delivery days, customer satisfaction and customer segments. The satisfaction tab uses post-delivery inputs. The models were saved with scikit-learn 1.7.2, so keep that version (it is pinned in `requirements.txt`).

### 5. Run the notebook

Open `notebooks/olist_all_problems_mlflow.ipynb` in Jupyter or VS Code and run the cells in order. It needs the Olist CSVs downloaded in step 3. Check the data paths in the first cells and point them to your local `data/raw/` folder.

Model results (from the notebook):

| Problem | Best model | Metric |
|---|---|---|
| Delivery delay (classification) | HistGradientBoosting | AUC 0.810 (XGBoost 0.805, RandomForest 0.769) |
| Freight cost (regression) | HistGradientBoosting | MAE 3.46 (RandomForest 4.12) |
| Delivery days (regression) | HistGradientBoosting | MAE 4.26 (RandomForest 4.65) |
| Customer satisfaction (classification) | HistGradientBoosting | AUC 0.716 (RandomForest 0.714) |

---

## ❓ Key Business Questions

**Sales & Revenue**
- How do revenue and order volume trend over time? Is there seasonality?
- Which product categories and states drive the most revenue?
- What is the average order value and how does it vary by category and payment type?

**Delivery & Logistics**
- What is the average delivery time and how often do orders arrive late?
- Which states and sellers have the worst delivery performance?
- How does freight cost relate to distance and order value?

**Customer Behavior**
- What is the repeat purchase rate?
- Who are our most valuable customers (RFM)?
- How do customers prefer to pay (credit card, boleto, installments)?

**Satisfaction & Quality**
- What drives low review scores? How much does late delivery hurt ratings?
- Which categories and sellers receive the best and worst reviews?

**Sellers**
- Which sellers generate the most revenue, and which hurt customer experience?

---

## 🤖 Deep Learning Components

| Model | Type | Goal | Business Value |
|---|---|---|---|
| **Delivery Delay Prediction** | Simple neural network (MLP) | Predict whether an order will arrive late | Proactive customer communication |
| **Review Score Prediction** | Simple neural network (MLP) | Predict low-satisfaction orders | Early intervention to protect ratings |
| **Sales Forecasting** | Simple LSTM | Forecast monthly revenue and orders | Inventory and capacity planning |

> Customer segmentation (RFM + K-Means) is done as part of the analysis phase, without deep learning.

**Approach:** Keep the models small and easy to explain: 2 to 3 dense layers with dropout and early stopping, built with Keras. Features are prepared with Scikit-learn, and each model is compared with a simple baseline (e.g., Logistic Regression).

**Evaluation:** F1 and ROC-AUC for classification; RMSE and MAE for forecasting.

---

## 📊 Dashboards

Power BI dashboards are organized into pages:

1. **Executive Overview**: revenue, orders, AOV, customers, review score, on-time delivery rate.
2. **Sales Analysis**: trends, category performance, geographic distribution.
3. **Customer Analysis**: segments, repeat rate, payment behavior.
4. **Delivery & Logistics**: delivery time, delays by state, freight analysis.
5. **Seller Performance**: top and bottom sellers, ratings, delays.

> 📸 Screenshots will be added to `dashboards/screenshots/` and embedded here.

<!-- ![Executive Overview](dashboards/screenshots/overview.png) -->

---

## ☁️ Deployment

- **Model serving:** FastAPI endpoints for predictions (e.g., `/predict/delivery-delay`).
- **Web app:** Streamlit interface for exploring KPIs and running predictions.
- **Containerization:** Docker and Docker Compose for reproducible environments.
- **CI/CD:** GitHub Actions runs linting and tests on every push, and builds the image on merge to `main`.
- **Hosting:** *To be finalized (Render / Railway / Azure / AWS).*

**Live demo (Streamlit Community Cloud):** LIVE_URL_HERE

---

## 📈 Results & Key Insights

> This section will be filled in as the analysis progresses. Planned format:

| Finding | Evidence | Recommended Action |
|---|---|---|
| _e.g., Late deliveries sharply lower review scores_ | _average score on-time vs late_ | _Improve carrier SLAs for affected regions_ |
| _..._ | _..._ | _..._ |

**Model performance summary**

| Model | Metric | Score |
|---|---|---|
| Delivery Delay Classifier | F1 / ROC-AUC | _TBD_ |
| Review Score Model | F1 / ROC-AUC | _TBD_ |
| Sales Forecast | MAPE | _TBD_ |

---

## 👥 Team

| Name | Role | GitHub / LinkedIn |
|---|---|---|
| Mahmoud Hatem | Machine Learning / Deep Learning Engineer | [@mahmoudhatemai5](https://github.com/mahmoudhatemai5) |
| _Member 2_ | _e.g., Data Analyst_ | _link_ |
| _Member 3_ | _e.g., Data Engineer_ | _link_ |
| _Member 4_ | _e.g., BI Developer_ | _link_ |
| _Member 5_ | _e.g., MLOps / Deployment_ | _link_ |

**Supervisor:** _Name_  ·  **University / Program:** _Name_  ·  **Year:** 2026

### Contribution Workflow

- `main` is the stable branch; work happens on feature branches (`feature/<name>`).
- Changes are merged through Pull Requests with at least one reviewer.
- Commit messages follow the convention: `feat:`, `fix:`, `docs:`, `refactor:`.

---

## 🗺️ Roadmap

- [x] Project setup & dataset selection
- [ ] Database schema & data loading
- [ ] Data quality checks
- [ ] ETL pipeline
- [ ] Data warehouse (star schema)
- [ ] EDA & KPI definitions
- [ ] Deep learning models
- [ ] Power BI dashboards
- [ ] REST API & Streamlit app
- [ ] Docker & CI/CD
- [ ] Cloud deployment
- [ ] Final report & presentation

**Future ideas:** real-time streaming ingestion, automated model retraining, Portuguese NLP for review text, recommendation system.

---

## 📄 License & Acknowledgements

- Code is released under the **MIT License** (see `LICENSE`).
- Dataset: *Brazilian E-Commerce Public Dataset by Olist*, released on Kaggle under **CC BY-NC-SA 4.0**. All credit for the data goes to Olist and the Kaggle community. The dataset is used here for **educational, non-commercial purposes only**.

---

<div align="center">

⭐ If you find this project useful, please give it a star!

</div>
