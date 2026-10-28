from typing import List
from fastapi import APIRouter, Depends, Form, File, UploadFile
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import User
from app.features.auth.dependencies import get_current_user
from app.features.products.schemas import ProductOut
from app.features.products.service import (
    list_user_products,
    create_product_with_media,
    delete_user_product
)

router = APIRouter(prefix="/api/products", tags=["products"])

@router.get("", response_model=List[ProductOut])
def list_products(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return list_user_products(user.id, db)

@router.post("", response_model=ProductOut)
def create_product(
    title: str = Form(...),
    description: str = Form(""),
    barcode: str = Form(""),
    price: float = Form(...),
    currency: str = Form("MAD"),
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_product_with_media(
        user_id=user.id,
        title=title,
        description=description,
        barcode=barcode,
        price=price,
        currency=currency,
        files=files,
        db=db
    )

@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    delete_user_product(product_id, user.id, db)
    return {"ok": True}
