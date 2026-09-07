import asyncio
import logging
from random import uniform
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.redis import distributed_lock, get_url_lock_key
from app.models.alert import PriceAlert
from app.models.price_history import PriceHistory
from app.models.product import MonitoredProduct
from app.services.notification_service import NotificationService
from app.services.scraper_service import ScraperService, ScrapingError

logger = logging.getLogger("worker.tasks")

scraper_service = ScraperService()
notification_service = NotificationService()


async def scrape_single_product_task(ctx: Dict[str, Any], product_id: int) -> bool:
    """
    Executa a coleta de preço de um único produto com:
    - Lock distribuído no Redis por URL (evita concorrência e duplicidade)
    - Persistência de histórico imutável
    - Avaliação e disparo de alertas com anti-spam
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(MonitoredProduct)
            .options(
                selectinload(MonitoredProduct.alerts).selectinload(PriceAlert.user)
            )
            .where(MonitoredProduct.id == product_id)
        )
        result = await session.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning(f"Produto #{product_id} não foi encontrado no banco.")
            return False

        lock_key = get_url_lock_key(product.url)

        async with distributed_lock(lock_key, timeout=60) as acquired:
            if not acquired:
                logger.info(
                    f"Coleta para a URL '{product.url}' já está em execução por outro worker. Pulando..."
                )
                return False

            await asyncio.sleep(uniform(0.5, 1.5))

            try:
                scraped_data = await scraper_service.scrape_product(product.url)

                history = PriceHistory(
                    product_id=product.id,
                    price=scraped_data.price,
                    in_stock=scraped_data.in_stock,
                )
                session.add(history)

                product.last_price = scraped_data.price
                product.in_stock = scraped_data.in_stock
                if scraped_data.title and (not product.title or product.title == product.url):
                    product.title = scraped_data.title

                if product.alerts:
                    await notification_service.process_product_alerts(
                        product=product,
                        current_price=scraped_data.price,
                        alerts=product.alerts,
                    )

                await session.commit()
                logger.info(
                    f"Sucesso na coleta do Produto #{product.id} ('{product.title}'): "
                    f"R$ {scraped_data.price:.2f} (Em estoque: {scraped_data.in_stock})"
                )
                return True

            except ScrapingError as exc:
                await session.rollback()
                logger.warning(f"Erro de scraping no Produto #{product.id} ({product.url}): {exc}")
                return False
            except Exception as exc:
                await session.rollback()
                logger.error(
                    f"Erro inesperado ao processar Produto #{product.id}: {exc}",
                    exc_info=True,
                )
                return False


async def check_all_products_task(ctx: Dict[str, Any]) -> int:
    """
    Cron Job periódico: Busca todos os produtos cadastrados e enfileira
    um job individual para cada um no Redis (Fan-out Pattern).
    """
    logger.info("Iniciando ciclo de verificação periódica de produtos...")

    async with AsyncSessionLocal() as session:
        query = select(MonitoredProduct.id)
        result = await session.execute(query)
        product_ids = result.scalars().all()

    if not product_ids:
        logger.info("Nenhum produto cadastrado para monitoramento.")
        return 0

    arq_redis = ctx.get("redis")
    enqueued_count = 0

    for pid in product_ids:
        if arq_redis:
            await arq_redis.enqueue_job("scrape_single_product_task", pid)
            enqueued_count += 1
        else:
            asyncio.create_task(scrape_single_product_task(ctx, pid))
            enqueued_count += 1

    logger.info(f"🚀 {enqueued_count} produtos enfileirados para coleta assíncrona.")
    return enqueued_count