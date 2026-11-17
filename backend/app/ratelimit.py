"""Limite simples de uso: Redis se REDIS_URL existir, senão memória do processo."""
import time
from collections import defaultdict

from fastapi import HTTPException

from app.config import get_settings

_mem: dict[str, list[float]] = defaultdict(list)
_redis = None
_tentou = False


def _client():
    global _redis, _tentou
    if not _tentou:
        _tentou = True
        url = get_settings().redis_url
        if url:
            try:
                import redis

                _redis = redis.Redis.from_url(url, socket_timeout=2)
                _redis.ping()
            except Exception:  # noqa: BLE001
                _redis = None
    return _redis


def limitar(chave: str, maximo: int, janela_s: int, mensagem: str) -> None:
    r = _client()
    if r is not None:
        k = f"rl:{chave}:{int(time.time() // janela_s)}"
        n = r.incr(k)
        if n == 1:
            r.expire(k, janela_s)
        if n > maximo:
            raise HTTPException(429, mensagem)
        return
    agora = time.time()
    hist = [t for t in _mem[chave] if agora - t < janela_s]
    if len(hist) >= maximo:
        raise HTTPException(429, mensagem)
    hist.append(agora)
    _mem[chave] = hist
