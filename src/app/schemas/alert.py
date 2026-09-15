from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertBase(BaseModel):
    target_price: Decimal = Field(
        gt=0,
        description='Preço-alvo para disparo'
    )
    condition: str = Field(
        default='<=',
        pattern="^(<=|>=|<|>)$",
        description='Condição de comparação (ex: <=, >=).'
    )


class AlertCreate(AlertBase):
    product_id: int


class AlertUpdate(BaseModel):
    target_price: Optional[Decimal] = Field(
        default=None,
        gt=0
    )
    condition: Optional[str] = None
    is_triggered: Optional[bool] = None


class AlertResponse(AlertBase):
    id: int
    product_id: int
    user_id: int
    is_triggered: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)