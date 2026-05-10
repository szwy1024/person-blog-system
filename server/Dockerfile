FROM ubuntu:20.04

WORKDIR /app

ENV TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8

COPY server/requirements.txt /app/server/requirements.txt

RUN pwd \
    && sed -i 's@/archive.ubuntu.com/@/mirrors.huaweicloud.com/@g' /etc/apt/sources.list \
    && apt-get clean \
    && apt update \
    && apt-get install -y python3 gcc python3-dev python3-pip tzdata \
    && pip install --no-cache-dir -r /app/server/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY server /app/server

ENV NAME Blogin
ENV PYTHONPATH=/app

CMD ["gunicorn", "server.wsgi:app", "-c", "server/gunicorn_conf.py"]
