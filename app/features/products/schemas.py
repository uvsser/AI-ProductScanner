from pydantic import BaseModel, Field
from typing import Optional

class ProductCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    barcode: str = ""
    price: float = Field(ge=0.0)
    currency: str = Field(default="MAD", max_length=8)

class ProductOut(BaseModel):
    id: int
    title: str
    description: str
    barcode: Optional[str] = ""
    price: float
    currency: str
    status: str
    image_count: int
    thumbnail_url: Optional[str] = None
    preview_urls: list[str] = []

    model_config = {"from_attributes": True}
