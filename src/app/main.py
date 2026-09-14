from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import ProductAccessDeniedError, ProductNotFoundError
from app.core.redis import close_redis_client
from app.web.router import router as web_router

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="8" fill="#121215"/>
  <circle cx="16" cy="16" r="10" stroke="#34d399" stroke-width="2.5" fill="none"/>
  <circle cx="16" cy="16" r="5" fill="#34d399"/>
</svg>"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis_client()
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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


@app.exception_handler(ProductNotFoundError)
async def product_not_found_handler(request: Request, exc: ProductNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message},
    )


@app.exception_handler(ProductAccessDeniedError)
async def product_access_denied_handler(request: Request, exc: ProductAccessDeniedError):
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message},
    )