from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from app.services.llm_analyzer import analyze_with_llm, answer_question_with_llm

import pandas as pd
import io
import uuid

router = APIRouter()
DATASET_STORE: dict[str, pd.DataFrame] = {}

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


class AskRequest(BaseModel):
    dataset_id: str
    question: str


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    prompt: str = Form("")
):

    if not is_prompt_safe(prompt):
        raise HTTPException(
            status_code=400,
            detail="Unsafe prompt detected"
        )

    content = await file.read()

    try:

        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))

        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))

        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format"
            )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse file: {str(e)}"
        )

    MAX_ROWS = 10000

    if len(df) > MAX_ROWS:
        df = df.head(MAX_ROWS)

    try:
        report, charts = analyze_with_llm(
            df=df,
            user_prompt=prompt
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM analysis failed: {str(e)}"
        )

    dataset_id = uuid.uuid4().hex
    DATASET_STORE[dataset_id] = df.copy()

    return {
        "dataset_id": dataset_id,
        "report": report,
        "metadata": {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": list(df.columns),
            "file_name": file.filename
        },
        "charts": charts
    }


@router.post("/ask")
async def ask_question(payload: AskRequest):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    if not is_prompt_safe(payload.question):
        raise HTTPException(status_code=400, detail="Unsafe prompt detected")

    dataset = DATASET_STORE.get(payload.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset session not found")

    try:
        answer, charts = answer_question_with_llm(
            df=dataset,
            user_question=payload.question.strip()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM Q&A failed: {str(e)}"
        )

    return {
        "answer": answer,
        "charts": charts,
    }