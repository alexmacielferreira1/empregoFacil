"""Ponto de entrada (ShardCloud, Render ou local): python main.py"""
import os
import sys
from pathlib import Path

import uvicorn

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))  # importa "app" desta pasta, nunca de uma cópia antiga
os.chdir(AQUI)

from app.main import app  # noqa: F401

if __name__ == "__main__":
    port = int(os.getenv("PORT", "80"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
