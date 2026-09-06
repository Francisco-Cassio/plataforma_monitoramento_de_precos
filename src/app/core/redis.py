import hashlib
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import redis.asyncio as aioredis
from redis.exceptions import LockError

from src.app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """Retorna a instância singleton do cliente assíncrono do Redis."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    """Fecha o pool de conexões com o Redis de forma graciosa."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def get_url_lock_key(url: str) -> str:
    """Gera uma chave determinística para o lock baseada no SHA-256 da URL."""
    url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]
    return f"lock:scrape:{url_hash}"


@asynccontextmanager
async def distributed_lock(
    name: str,
    timeout: int = 60,
) -> AsyncGenerator[bool, None]:
    """
    Context manager assíncrono para Lock Distribuído no Redis.
    
    - Tenta adquirir o lock sem bloquear (blocking=False).
    - Se adquirir: yield True e garante a liberação no finally.
    - Se já estiver em uso: yield False.
    """
    client = get_redis_client()
    lock = client.lock(name=name, timeout=timeout, blocking=False)
    acquired = await lock.acquire(blocking=False)
    
    try:
        yield acquired
    finally:
        if acquired:
            try:
                await lock.release()
            except LockError:
                # Ocorre se o lock expirou pelo TTL antes do release
                logger.warning(f"Lock {name} expirou antes da liberação.")
            except Exception as exc:
                logger.error(f"Erro inesperado ao liberar o lock {name}: {exc}")