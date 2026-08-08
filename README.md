# Retail Customer Intelligence Platform
**Stack:** Python · PostgreSQL · scikit-learn · Power BI · Git
**Dataset:** UCI Online Retail II (~1M transactions, CC BY 4.0)

## What It Does
An end-to-end analytics pipeline that turns two years of raw retail
transactions into customer intelligence: who your best customers are,
how they behave, and who is about to stop buying.

## Architecture

Raw CSV → Python cleaning → PostgreSQL (3 tables) → Python EDA + ML model
→ Power BI dashboard → GitHub

## Results
- Churn model ROC-AUC: ~0.81 (Logistic Regression)
- Churn model ROC-AUC: ~0.78 (Random Forest)
- Top churn drivers: recency, frequency
- 22% of customers drive 80% of revenue (Pareto)

## How to Run
```
git clone https://github.com/aditya-anand19/retail-customer-intelligence-platform
cd retail-customer-intelligence-platform
pip install -r requirements.txt
# Download dataset to data/raw/ from Kaggle link
# Run notebooks in order: 01 → 02 → 03 → 04
```
## Screenshots
![Executive Dashboard](powerbi\screenshots\page1_executive.png)
![Customer Analytics](powerbi\screenshots\page2_customer.png)
![Sales Analytics](powerbi\screenshots\page3_sales.png)
![Churn Insights](powerbi\screenshots\page4_churn.png)

## Dataset Citation
Chen, D. (2019). Online Retail II. UCI ML Repository (CC BY 4.0).
