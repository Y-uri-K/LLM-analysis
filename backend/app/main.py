import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routes.analyze import router
from pathlib import Path

app = FastAPI()

_cors_raw = os.environ.get(
    "NEXT_PUBLIC_API_URL",
    "http://localhost:3000",
)
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

static_dir = Path(__file__).resolve().parent / "static"
charts_dir = static_dir / "charts"
charts_dir.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=charts_dir), name="charts")


@app.get("/")
def root():
    return {
        "message": "LLM Analytics Backend Running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }