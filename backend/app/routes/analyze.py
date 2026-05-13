from fastapi import APIRouter, UploadFile, File, Form
from app.services.llm_analyzer import analyze_with_llm

import pandas as pd
import io

router = APIRouter()


# Простая защита от prompt injection
BLOCKED_PATTERNS = [
    "ignore previous instructions",
    "system prompt",
    "reveal prompt",
    "developer message",
    "execute code",
    "os.system",
    "subprocess",
]


def is_prompt_safe(prompt: str) -> bool:
    prompt_lower = prompt.lower()

    for pattern in BLOCKED_PATTERNS:
        if pattern in prompt_lower:
            return False

    return True


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    prompt: str = Form("")
):

    # Проверка prompt injection
    if not is_prompt_safe(prompt):
        return {
            "error": "Unsafe prompt detected"
        }

    # Читаем файл
    content = await file.read()

    try:

        # CSV
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))

        # Excel
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))

        else:
            return {
                "error": "Unsupported file format"
            }

    except Exception as e:
        return {
            "error": f"Failed to parse file: {str(e)}"
        }

    # Ограничение размера dataset
    MAX_ROWS = 10000

    if len(df) > MAX_ROWS:
        df = df.head(MAX_ROWS)

    try:

        # AI-анализ
        report = analyze_with_llm(
            df=df,
            user_prompt=prompt
        )

    except Exception as e:
        return {
            "error": f"LLM analysis failed: {str(e)}"
        }

    return {
        "report": report,
        "metadata": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": list(df.columns),
            "file_name": file.filename
        },
        "charts": []
    }