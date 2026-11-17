#!/usr/bin/env bash
# Gera dist/empregofacil-shard.zip pronto para subir na ShardCloud (Linux/Mac/Git Bash).
set -euo pipefail
cd "$(dirname "$0")"

echo ">> Compilando o frontend para backend/static"
(cd frontend && npm install --no-audit --no-fund && npm run build)

echo ">> Montando o pacote"
rm -rf dist && mkdir -p dist
(cd backend && zip -rq ../dist/empregofacil-shard.zip . \
  -x "__pycache__/*" "*/__pycache__/*" "*.pyc" "*.db" ".env" "tests/*" ".pytest_cache/*" "venv/*" ".venv/*" "Dockerfile")

echo ">> Pronto: dist/empregofacil-shard.zip"
