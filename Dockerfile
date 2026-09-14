FROM lightpanda/browser:nightly AS lightpanda

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=lightpanda /bin/lightpanda /usr/local/bin/lightpanda

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY docker-entrypoint.sh .

EXPOSE 8000
CMD ["./docker-entrypoint.sh"]
