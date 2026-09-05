from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProductBase(BaseModel):
    url: HttpUrl
    title: Optional[str] = None


class ProductCreate(ProductBase):
    target_price: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description='Preço-alvo opcional para alerta automático.'
    )


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    in_stock: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    user_id: int
    title: str
    url: str
    platform: str
    last_price: Optional[Decimal] = None
    in_stock: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)