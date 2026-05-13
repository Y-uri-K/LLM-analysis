from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)


def analyze_with_llm(
    df: pd.DataFrame,
    user_prompt: str
):

    # Безопасное summary
    summary = f"""
Dataset Shape:
{df.shape}

Columns:
{list(df.columns)}

Data Types:
{df.dtypes.to_string()}

Missing Values:
{df.isnull().sum().to_dict()}

Statistical Summary:
{df.describe(include='all').fillna('').to_string()}

Sample Rows:
{df.head(5).to_markdown()}
"""

    prompt = f"""
You are a senior data analyst.

Analyze this dataset and generate a professional markdown report.

Your report should include:
- executive summary
- important trends
- anomalies
- correlations
- behavioral patterns
- business insights
- recommendations

IMPORTANT:
- Write concise and professional analysis
- Use markdown formatting
- Use headings and bullet points
- Focus on actionable insights

User Instructions:
{user_prompt}

Dataset Information:
{summary}
"""

    response = client.chat.completions.create(
        model="mimo-v2.5-pro",

        messages=[
            {
                "role": "system",
                "content": (
                    "You are MiMo, an expert AI data analyst "
                    "specialized in business intelligence, "
                    "statistics, and behavioral analytics."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.3,
        top_p=0.95,
        max_completion_tokens=2048
    )

    return response.choices[0].message.content