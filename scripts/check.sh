#!/usr/bin/env bash
# 封装固定件： python check/check.py "$@"
set -e
cd "$(dirname "$0")/.."
python check/check.py "$@"
