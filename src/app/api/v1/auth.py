from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_current_user, get_user_service
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService
from pydantic import ValidationError
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, auth_service: AuthService = Depends(get_user_service)):
    """
    Endpoint para registrar um novo usuário.
    """
    user = await auth_service.register_user(user_in)
    return user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_user_service),
):
    """
    Endpoint para autenticar um usuário e gerar tokens de acesso e atualização.
    """
    try:
        login_data = UserLogin(email=form_data.username, password=form_data.password)
    except ValidationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de email inválido.",
        )

    token = await auth_service.authenticate_user(login_data)
    return token


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Endpoint para obter informações do usuário atualmente autenticado.
    """
    return current_user