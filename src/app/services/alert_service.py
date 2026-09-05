from typing import List, Optional
from fastapi import HTTPException, status

from app.models.alert import PriceAlert
from app.repositories.alert_repository import AlertRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.alert import AlertCreate, AlertUpdate


class AlertService:
    def __init__(self, alert_repo: AlertRepository, product_repo: ProductRepository):
        self.alert_repo = alert_repo
        self.product_repo = product_repo

    async def create_alert(self, alert_in: AlertCreate, user_id: int) -> PriceAlert:
        product = await self.product_repo.get_by_id(alert_in.product_id)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Produto não encontrado.',
            )
        if product.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Você não tem permissão para criar alerta para este produto.',
            )

        new_alert = PriceAlert(
            product_id=alert_in.product_id,
            user_id=user_id,
            target_price=alert_in.target_price,
            condition=alert_in.condition,
        )
        return await self.alert_repo.create(new_alert)

    async def list_alerts(self, user_id: int) -> List[PriceAlert]:
        return await self.alert_repo.list_by_user(user_id)

    async def delete_alert(self, alert_id: int, user_id: int) -> None:
        alert = await self.alert_repo.get_by_id(alert_id)

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Alerta não encontrado.',
            )
        if alert.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Este alerta não pertence ao usuário.',
            )
        await self.alert_repo.delete(alert)