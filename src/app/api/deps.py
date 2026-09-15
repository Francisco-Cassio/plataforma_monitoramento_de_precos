import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.repositories.alert_repository import AlertRepository
from app.repositories.product_repository import ProductRepository
from app.services.alert_service import AlertService
from app.services.product_service import ProductService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_user_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_raw: str = payload.get("sub")
        token_type: str = payload.get("type")

        if user_id_raw is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou tipo incorreto.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = int(user_id_raw)
    
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo.",
        )

    return user

async def get_current_active_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Usuário não é administrador.",
        )
    return current_user

def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    product_repo = ProductRepository(db)
    alert_repo = AlertRepository(db)
    return ProductService(product_repo, alert_repo)

def get_alert_service(db: AsyncSession = Depends(get_db)) -> AlertService:
    alert_repo = AlertRepository(db)
    product_repo = ProductRepository(db)
    return AlertService(alert_repo, product_repo)