FROM python:3.11-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y curl

# install uv
RUN pip install uv

# copy dependency files
COPY pyproject.toml uv.lock ./

# install deps
RUN uv sync

# copy project
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]