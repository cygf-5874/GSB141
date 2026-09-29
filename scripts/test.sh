#!/usr/bin/env bash
# 封装既有用例： python tests/run.py
set -e
cd "$(dirname "$0")/.."
python tests/run.py
