from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Localização da pasta de templates
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Router web (oculto da documentação do Swagger para não poluir os endpoints da API)
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Renderiza a página principal do Dashboard."""
    return templates.TemplateResponse(request=request, name="dashboard.html")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Renderiza a página de Login e Cadastro."""
    return templates.TemplateResponse(request=request, name="login.html")

