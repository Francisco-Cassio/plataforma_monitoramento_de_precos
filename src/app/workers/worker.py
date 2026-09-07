import logging
from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.redis import close_redis_client
from app.workers.tasks import check_all_products_task, scrape_single_product_task

logger = logging.getLogger("worker")


async def startup(ctx: dict) -> None:
    """Executado na inicialização do worker."""
    logger.info("Iniciando ARQ Worker de monitoramento de preços...")


async def shutdown(ctx: dict) -> None:
    """Executado no encerramento gracioso do worker."""
    logger.info("Encerrando ARQ Worker graciosamente...")
    await close_redis_client()


class WorkerSettings:
    """Configurações centrais de execução do ARQ Worker."""    
    functions = [scrape_single_product_task, check_all_products_task]

    cron_jobs = [
        cron(check_all_products_task, minute=set(range(0, 60, 5)))
    ]

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = 10