from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserCreate, UserLogin


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def register_user(self, user_create: UserCreate) -> User:
        existing_user = await self.user_repository.get_by_email(user_create.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado.",
            )
        hashed_password = get_password_hash(user_create.password)
        new_user = User(
            email=user_create.email,
            hashed_password=hashed_password,
            role=user_create.role,
        )
        return await self.user_repository.create(new_user)

    async def authenticate_user(self, login_data: UserLogin) -> Token:
        user = await self.user_repository.get_by_email(login_data.email)

        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo.",
            )
    
        return self.create_user_token(user)

    def create_user_token(self, user: User) -> Token:
        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))
        return Token(access_token=access_token, refresh_token=refresh_token)