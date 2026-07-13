FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync
COPY . .
EXPOSE 9000
CMD ["uv", "run", "uvicorn", "router.main:app", "--host", "0.0.0.0", "--port", "9000"]
