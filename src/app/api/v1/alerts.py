from typing import List
from fastapi import APIRouter, Depends, status

from app.api.deps import get_alert_service, get_current_user
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertResponse
from app.services.alert_service import AlertService

router = APIRouter()


@router.post(
    "/",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar alerta de preço para um produto",
)
async def create_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """
    Cria uma nova regra de alerta de preço para um produto do usuário.
    """
    return await service.create_alert(alert_in=alert_in, user_id=current_user.id)


@router.get(
    "/",
    response_model=List[AlertResponse],
    summary="Listar meus alertas de preço",
)
async def list_my_alerts(
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """
    Lista todos os alertas de preço configurados pelo usuário logado.
    """
    return await service.list_alerts(user_id=current_user.id)


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover alerta de preço",
)
async def delete_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """
    Remove uma regra de alerta de preço.
    """
    await service.delete_alert(alert_id=alert_id, user_id=current_user.id)


@router.delete(
    "/product/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover alerta de preço associado a um produto",
)
async def delete_alert_by_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    service: AlertService = Depends(get_alert_service),
):
    """
    Remove o alerta de preço configurado para o produto especificado.
    """
    await service.delete_alert_by_product(product_id=product_id, user_id=current_user.id)