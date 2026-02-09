#!/usr/bin/env bash

# Configure environment
export UV_CACHE_DIR=.uv


uv run python alembic_migration.py  # migrating base to the last change

uv run uvicorn app.main:app --host 0.0.0.0 --port 8080 --proxy-headers --timeout-keep-alive 300

