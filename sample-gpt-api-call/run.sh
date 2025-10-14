#!/bin/bash
cd "$(dirname "$0")"
export $(cat .env | xargs)
uv run python test_openai.py "$@"
