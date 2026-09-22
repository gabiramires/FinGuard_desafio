FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p reports

ENTRYPOINT ["python", "main.py"]
CMD ["--nivel", "1", "--input", "data/reclamacoes.csv", "--provider", "mock"]
