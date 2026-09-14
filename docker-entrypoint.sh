#!/bin/sh
set -e

lightpanda serve --host 127.0.0.1 --port 9222 --log-level warn &

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
