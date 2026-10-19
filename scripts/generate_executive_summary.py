

import os
import re
import sys
import pandas as pd
from google import genai

# Load GEMINI_API_KEY from a .env file in the repo root (the file is git-ignored)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass  # fall back to an environment variable set in the terminal

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    sys.exit(
        "GEMINI_API_KEY is not set.\n\n"
        "Easiest: create a file named .env in the repo root containing one line:\n"
        "  GEMINI_API_KEY=your-key\n\n"
        "Or set it for this terminal only:\n"
        "Windows Command Prompt:  set GEMINI_API_KEY=AIza...\n"
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
Logistic Regression classifier predicting customer churn (test ROC-AUC 0.81),
chosen over a Random Forest (ROC-AUC 0.78). Churn defined behaviourally as no
purchase in the final 90 days of the observation window. Features computed only
from data before the cutoff date to prevent leakage.

RESULTS
- Customers scored: {total_customers:,}
- High-risk customers (churn probability above 0.70): {high_n:,} ({high_pct:.1%} of base)
- Historical revenue represented by the high-risk cohort: {high_rev:,.0f}
- Average historical spend per high-risk customer: {high_avg:,.0f}
- Share of total customer revenue sitting in the high-risk cohort: {rev_at_risk_pct:.1%}
- Strongest churn predictors (model coefficients): recency (days since last
  purchase) raises churn risk most; higher purchase frequency and buying a wider
  range of products lower it
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
coefficients. Explain what recency being the dominant predictor means in
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
            "max_output_tokens": 4096,  # room for the full three paragraphs
        },
    )
    summary = (response.text or "").strip()
    finish = str(response.candidates[0].finish_reason) if response.candidates else "UNKNOWN"
except Exception as e:
    sys.exit(
        f"\nAPI call failed: {e}\n\n"
        "Common causes:\n"
        "  1. Model name not available on your key. Run list_models.py (below) to check.\n"
        "  2. API key invalid or not yet active — wait 60s after creating it.\n"
        "  3. No internet / firewall blocking generativelanguage.googleapis.com\n"
    )


# ---------- Validation: never publish an incomplete or unverified summary ----------
problems = []

# 1. Did the model finish, or was it cut off?
if "STOP" not in finish:
    problems.append(f"Response did not finish normally (finish_reason={finish}).")
if summary.count("\n\n") < 2 and len(summary.split()) < 150:
    problems.append("Summary looks truncated (fewer than three paragraphs).")

# 2. Every number in the summary must appear in the facts we gave the model.
def numbers_in(text):
    found = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    return {float(n.replace(",", "").rstrip(".")) for n in found}

# Accept the same figure written in rounded forms: 29.04% -> 29%, 1,234,567 -> 1.2 (million) or 1,235 (thousand)
allowed = set()
for v in numbers_in(facts):
    for scaled in (v, v / 1e3, v / 1e6):
        for d in (0, 1, 2):
            allowed.add(round(scaled, d))

unverified = sorted(n for n in numbers_in(summary)
                    if round(n, 2) not in allowed and n not in {1, 2, 3})
if unverified:
    problems.append("Figures not found in the source data: "
                    + ", ".join(f"{n:g}" for n in unverified))

os.makedirs("reports", exist_ok=True)
if problems:
    out_path = "reports/executive_summary_UNVERIFIED.txt"
    print("\nVALIDATION FAILED - review before using:")
    for p in problems:
        print("  -", p)
else:
    out_path = "reports/executive_summary.txt"
    print("\nValidation passed: complete response, every figure matches the source data.")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(summary)

print("\n" + "=" * 70)
print("EXECUTIVE SUMMARY")
print("=" * 70)
print(summary)
print("=" * 70)
print(f"\nSaved to {out_path}")