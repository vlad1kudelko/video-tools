FROM lightpanda/browser:nightly AS lightpanda

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=lightpanda /bin/lightpanda /usr/local/bin/lightpanda

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium + its apt runtime deps are the single heaviest thing in this image
# (~1.5-2GB) and only "Запись экрана" needs them. Default off so `docker
# compose up` stays light; opt in with `WITH_BROWSER=true docker compose up
# -d --build` when that tab is actually needed.
ARG WITH_BROWSER=false
ENV WITH_BROWSER=$WITH_BROWSER
RUN if [ "$WITH_BROWSER" = "true" ]; then python -m playwright install --with-deps chromium; fi

COPY app ./app

EXPOSE 8000
CMD ["sh", "-c", "lightpanda serve --host 127.0.0.1 --port 9222 --log-level warn & exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
