FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY itplus/ /app/itplus/
COPY run_itplus.py /app/run_itplus.py
COPY itplus/scripts/ /app/itplus/scripts/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/uploads

EXPOSE 8000

CMD ["uvicorn", "run_itplus:app", "--host", "0.0.0.0", "--port", "8000"]
