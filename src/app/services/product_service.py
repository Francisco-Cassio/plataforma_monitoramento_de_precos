from typing import List, Optional
from fastapi import HTTPException, status

from app.models.alert import PriceAlert
from app.models.product import MonitoredProduct
from app.repositories.alert_repository import AlertRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate
from app.models.price_history import PriceHistory


class ProductService:
    def __init__(
        self,
        product_repo: ProductRepository,
        alert_repo: Optional[AlertRepository] = None,
    ):
        self.product_repo = product_repo
        self.alert_repo = alert_repo

    def detect_platform(self, url: str) -> str:
        url_lower = str(url).lower()
        if "amazon" in url_lower:
            return "amazon"
        elif "mercadolivre" in url_lower or "mercadolibre" in url_lower:
            return "mercadolivre"
        elif "magazineluiza" in url_lower or "magalu" in url_lower:
            return "magalu"
        elif "kabum" in url_lower:
            return "kabum"
        elif "shopee" in url_lower:
            return "shopee"
        return "custom"

    async def create_product(self, product_in: ProductCreate, user_id: int) -> MonitoredProduct:
        existing = await self.product_repo.get_by_url_and_user(str(product_in.url), user_id)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Você já está monitorando este produto.'
            )

        platform = self.detect_platform(str(product_in.url))
        product = MonitoredProduct(
            user_id=user_id,
            url=str(product_in.url),
            title=product_in.title or "Aguardando coleta...",
            platform=platform,
        )
        product = await self.product_repo.create(product)

        if self.alert_repo and product_in.target_price:
            alert = PriceAlert(
                product_id=product.id,
                user_id=user_id,
                target_price=product_in.target_price,
                condition='<=',
            )
            await self.alert_repo.create(alert)

        return product

    async def get_product(self, product_id: int, user_id: int) -> MonitoredProduct:
        product = await self.product_repo.get_by_id(product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Produto não encontrado.',
            )
        if product.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Você não tem permissão para acessar este produto.'
            )
        return product
        
    async def list_products(self, user_id: int, skip: int = 0, limit: int = 50) -> List[MonitoredProduct]:
        return await self.product_repo.list_by_user(user_id=user_id, skip=skip, limit=limit)

    async def delete_product(self, product_id: int, user_id: int) -> None:
        product = await self.get_product(product_id, user_id)
        await self.product_repo.delete(product)

    async def get_product_history(self, product_id: int, user_id: int) -> List[PriceHistory]:
        await self.get_product(product_id, user_id)
        return await self.product_repo.get_price_history(product_id)