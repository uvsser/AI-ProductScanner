from pydantic import BaseModel, Field
from typing import List, Optional

class SessionItemOut(BaseModel):
    id: int
    product_id: int
    title: str
    description: Optional[str] = ""
    quantity: int
    unit_price: float
    subtotal: float

class ShoppingSessionOut(BaseModel):
    id: int
    user_id: int
    status: str  # "open", "finalized", "cancelled"
    items: List[SessionItemOut]
    total: float
    currency: str

class AddSessionItemRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)
    tracking_id: Optional[str] = None  # To mark as confirmed in tracker

class UpdateSessionItemRequest(BaseModel):
    quantity: int = Field(ge=1, le=100)

class SessionActionResponse(BaseModel):
    message: str
    session: ShoppingSessionOut
