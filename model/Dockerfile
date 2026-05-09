FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_ARTIFACTS_DIR=/app/artifacts \
    MODEL_TYPE=bilstm

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY app.py inference.py model_defs.py preprocess.py /app/

EXPOSE 9000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:9000", "--workers", "1", "--threads", "2", "--timeout", "120"]
