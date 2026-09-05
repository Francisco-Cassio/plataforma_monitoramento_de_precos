from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import PriceAlert


class AlertRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, alert_id: int) -> Optional[PriceAlert]:
        query = select(PriceAlert).where(PriceAlert.id == alert_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> List[PriceAlert]:
        query = select(PriceAlert).where(PriceAlert.user_id == user_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_product(self, product_id: int) -> List[PriceAlert]:
        query = select(PriceAlert).where(PriceAlert.product_id == product_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, alert: PriceAlert) -> PriceAlert:
        self.session.add(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def update(self, alert: PriceAlert) -> PriceAlert:
        await self.session.commit()
        await self.session.refresh(alert)
        return alert

    async def delete(self, alert: PriceAlert) -> None:
        await self.session.delete(alert)
        await self.session.commit()