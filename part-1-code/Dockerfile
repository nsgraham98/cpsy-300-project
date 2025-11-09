FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir pandas matplotlib seaborn

CMD ["python", "data_analysis.py"]