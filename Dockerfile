FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY app ./app
COPY main.py ./main.py

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "main.py", "start"]
