"""Ponto de entrada alternativo (a ShardCloud pode estar configurada para iniciar por run.py).

Faz exatamente o mesmo que main.py: sobe a API + o frontend do Emprego Fácil.
"""
import os
import sys
from pathlib import Path

import uvicorn

# garante que "app" seja importado DESTA pasta, e não de uma cópia antiga em outro lugar
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
os.chdir(AQUI)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "80"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
