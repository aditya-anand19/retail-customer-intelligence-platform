

import os
import sys
import pandas as pd
from google import genai


API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    sys.exit(
        "GEMINI_API_KEY is not set.\n\n"
        "Windows PowerShell:  $env:GEMINI_API_KEY = \"AIza...\"\n"
        "Mac/Linux:           export GEMINI_API_KEY=\"AIza...\"\n\n"
        "Get a free key at https://aistudio.google.com/"
    )

client = genai.Client(api_key=API_KEY)

MODEL = "gemini-3.5-flash"   # if this errors, see the troubleshooting note below

print("Loading analysis results...")

churn = pd.read_csv("data/processed/churn_scores.csv")
feats = pd.read_csv("data/processed/customer_features.csv")

# Auto-detect columns (same logic as the Excel script)
risk_col = next((c for c in ["risk_band", "riskband", "risk", "band"]
                 if c in churn.columns), None)
money_col = next((c for c in ["monetary", "total_spend", "spend", "revenue"]
                  if c in feats.columns), None)

if risk_col is None or money_col is None:
    sys.exit(f"Column detection failed.\n"
             f"churn cols: {churn.columns.tolist()}\n"
             f"feats cols: {feats.columns.tolist()}")

merged = churn.merge(feats[["customer_id", money_col]], on="customer_id", how="left")
merged[money_col] = merged[money_col].fillna(0)

total_customers = len(merged)
high = merged[merged[risk_col].astype(str).str.lower() == "high"]
high_n   = len(high)
high_pct = high_n / total_customers if total_customers else 0
high_rev = float(high[money_col].sum())
high_avg = float(high[money_col].mean()) if high_n else 0.0
total_rev = float(merged[money_col].sum())
rev_at_risk_pct = high_rev / total_rev if total_rev else 0


facts = f"""
ANALYSIS CONTEXT
Dataset: UK e-commerce transaction history, approximately 1 million transactions
over a two-year period. Customer-level features engineered from transaction data.

MODEL
Random Forest classifier predicting customer churn, benchmarked against a
Logistic Regression baseline. Churn defined behaviourally as no purchase in the
final 90 days of the observation window. Features computed only from data before
the cutoff date to prevent leakage.

RESULTS
- Customers scored: {total_customers:,}
- High-risk customers (churn probability above 0.70): {high_n:,} ({high_pct:.1%} of base)
- Historical revenue represented by the high-risk cohort: {high_rev:,.0f}
- Average historical spend per high-risk customer: {high_avg:,.0f}
- Share of total customer revenue sitting in the high-risk cohort: {rev_at_risk_pct:.1%}
- Strongest churn predictors by feature importance: recency (days since last
  purchase), followed by purchase frequency
"""


system_instruction = (
    "You are a senior analytics consultant writing for a retail client's marketing "
    "leadership. Write in plain, direct business English. Reference specific numbers "
    "from the analysis. Do not use bullet points, headers, or markdown formatting. "
    "Do not hedge — the client needs a clear point of view. Do not invent any figure "
    "that is not present in the data provided."
)

prompt = f"""
Write a three-paragraph executive summary of the customer churn analysis below.

Paragraph 1 (Situation): What the analysis found, at a high level. State the size
of the at-risk cohort and the revenue it represents.

Paragraph 2 (Insight): Why these customers are at risk, based on the model's
feature importance. Explain what recency being the dominant predictor means in
practical terms for how the client should think about their customer base.

Paragraph 3 (Recommendation): What the client should do next, and what would need
to be true for that action to be worth taking.

Each paragraph should be four to five sentences. Total length under 350 words.

{facts}
"""


print(f"Calling {MODEL}...")

try:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "system_instruction": system_instruction,
            "temperature": 0.3,        # low = consistent, factual
            "max_output_tokens": 800,
        },
    )
    summary = response.text
except Exception as e:
    sys.exit(
        f"\nAPI call failed: {e}\n\n"
        "Common causes:\n"
        "  1. Model name not available on your key. Run list_models.py (below) to check.\n"
        "  2. API key invalid or not yet active — wait 60s after creating it.\n"
        "  3. No internet / firewall blocking generativelanguage.googleapis.com\n"
    )


os.makedirs("reports", exist_ok=True)
with open("reports/executive_summary.txt", "w", encoding="utf-8") as f:
    f.write(summary)

print("\n" + "=" * 70)
print("EXECUTIVE SUMMARY")
print("=" * 70)
print(summary)
print("=" * 70)
print("\nSaved to reports/executive_summary.txt")