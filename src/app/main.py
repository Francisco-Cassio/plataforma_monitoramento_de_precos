from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.v1.api import api_router
from app.core.config import settings
from app.web.router import router as web_router

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="8" fill="#121215"/>
  <circle cx="16" cy="16" r="10" stroke="#34d399" stroke-width="2.5" fill="none"/>
  <circle cx="16" cy="16" r="5" fill="#34d399"/>
</svg>"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(web_router)


@app.get("/health", tags=["Saúde da API"], summary="Checagem de integridade da API")
async def health_check():
    """Endpoint de checagem de saúde da aplicação"""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon oficial do Vigia em formato SVG"""
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")
