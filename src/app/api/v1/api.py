from fastapi import APIRouter

from app.api.v1 import alerts, auth, products

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(products.router, prefix="/products", tags=["Produtos Monitorados"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alertas de Preço"])