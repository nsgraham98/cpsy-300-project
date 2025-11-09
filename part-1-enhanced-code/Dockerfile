# Stage 1 - build the dependencies
FROM python:3.9-slim AS builder
WORKDIR /build

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

# Stage 2 - build the final image
FROM python:3.9-slim
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

COPY . /app

CMD ["python", "data_analysis.py"]
