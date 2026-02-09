#!/usr/bin/env sh

python3 -m pip install --no-cache-dir pipx
PIPX_GLOBAL_BIN_DIR=/usr/bin python3 -m pipx install --global uv
export UV_CACHE_DIR=.uv
uv sync
