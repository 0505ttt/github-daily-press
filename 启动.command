#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "请先安装 Python 3.11 或更新版本。"
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'import gh_daily, bs4, requests, pypdf, tzdata' >/dev/null 2>&1; then
  .venv/bin/python -m pip install -e .
fi
exec .venv/bin/python -m gh_daily serve --open
