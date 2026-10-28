from pydantic import BaseModel, Field
from typing import List

class CartItemOut(BaseModel):
    id: int
    product_id: int
    title: str
    description: str = ""
    quantity: int
    unit_price: float
    subtotal: float

class CartOut(BaseModel):
    id: int
    status: str
    items: List[CartItemOut]
    total: float
    currency: str

class AddCartItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)

class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=1, le=100)
