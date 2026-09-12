from typing import List
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_product_service
from app.models.user import User
from app.services.product_service import ProductService
from app.schemas.product import PriceHistoryResponse, ProductCreate, ProductResponse

router = APIRouter()


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar produto para monitoramento",
)
async def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    """
    Cadastra uma nova URL para ser monitorada pelo usuário autenticado.
    Se informado o 'target_price', cria automaticamente um alerta vinculado.
    """
    return await service.create_product(product_in=product_in, user_id=current_user.id)


@router.get(
    "/",
    response_model=List[ProductResponse],
    summary="Listar meus produtos monitorados",
)
async def list_my_products(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    """
    Lista todos os produtos monitorados pelo usuário logado com paginação.
    """
    return await service.list_products(user_id=current_user.id, skip=skip, limit=limit)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Obter detalhes de um produto",
)
async def get_product_details(
    product_id: int,
    current_user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    """
    Obtém os detalhes de um produto monitorado específico.
    """
    return await service.get_product(product_id=product_id, user_id=current_user.id)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover produto monitorado",
)
async def delete_monitored_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    """
    Remove um produto da lista de monitoramento do usuário.
    """
    await service.delete_product(product_id=product_id, user_id=current_user.id)


@router.get(
    "/{product_id}/history",
    response_model=List[PriceHistoryResponse],
    summary="Obter histórico de preços de um produto",
)
async def get_product_history(
    product_id: int,
    current_user: User = Depends(get_current_user),
    service: ProductService = Depends(get_product_service),
):
    """
    Retorna o histórico cronológico de preços para exibição em gráficos.
    """
    return await service.get_product_history(product_id=product_id, user_id=current_user.id)