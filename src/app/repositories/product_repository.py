from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import MonitoredProduct


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, product_id: int) -> Optional[MonitoredProduct]:
        query = select(MonitoredProduct).where(MonitoredProduct.id == product_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_url_and_user(self, url: str, user_id: int) -> Optional[MonitoredProduct]:
        query = select(MonitoredProduct).where(
            MonitoredProduct.url == url,
            MonitoredProduct.user_id == user_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int, skip: int = 0, limit: int = 50) -> List[MonitoredProduct]:
        query = (
            select(MonitoredProduct)
            .where(MonitoredProduct.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, product: MonitoredProduct) -> MonitoredProduct:
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update(self, product: MonitoredProduct) -> MonitoredProduct:
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete(self, product: MonitoredProduct) -> None:
        await self.session.delete(product)
        await self.session.commit()

    async def list_all(self) -> List[MonitoredProduct]:
        query = select(MonitoredProduct)
        result = await self.session.execute(query)
        return list(result.scalars().all())