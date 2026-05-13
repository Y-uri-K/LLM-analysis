#  LLM Analyst

Web-приложение для анализа датасетов с помощью LLM.  
Пользователь загружает CSV/XLSX файл, получает автоматический аналитический отчёт, графики и может задавать дополнительные вопросы по данным.

#  https://llm-analysis-gules.vercel.app/ 
---

## Возможности

- Загрузка CSV / Excel датасетов
- Автоматический анализ данных через LLM
- Генерация графиков
- Чат с датасетом (follow-up вопросы)

---

## Архитектура проекта

### 1. Frontend (Next.js)
- React + TypeScript
- TailwindCSS
- Vercel https://vercel.com/ 

### 2. Backend (FastAPI)
- Python + FastAPI
- Анализ данных через LLM (Xiaomi mimo 2.5 pro)
- Генерация графиков (matplotlib / seaborn)
- Обработка CSV/XLSX
- REST API:
  - `POST /analyze`
  - `POST /ask`
- Railway https://railway.app/
---

## Основная структура проекта

```
LLM ANALYSIS/
│
├── frontend/
│ ├── app/
│ │ └── page.tsx
│ │ └── layout.tsx
│ │ └── globals.css
│ ├── Dockerfile
│ ├── package.json
│ └── package.json
│
├── backend/
│ ├── app/
│ │ ├── main.py
│ │ ├── routes/
│ │ │ └── analyze.py
│ │ ├── services/
│ │ │ └── llm_analyzer.py
│ │ └── __init__.py
│ ├── pyproject.toml
│ ├── .python-version
│ ├── uv.lock
│ └── Dockerfile
│
├── .env.example
├── docker-compose.yml
├── vercel.json
└── README.md
```

# Локальный запуск через Docker

### Требования

- Docker
- Docker Compose

---

## 1. Клонировать проект

```bash
git clone https://github.com/your-repo/llm-analyst.git
cd llm-analyst
```
## 2. Настроить environment variables

 `MIMO_API_KEY=your_key`

## 3. Запуск через Docker Compose

``` 
docker-compose up --build
```

## 4. Доступ к приложению

```
Frontend: http://localhost:3000

Backend: http://localhost:8000/docs
```

