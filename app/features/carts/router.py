from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import User
from app.features.auth.dependencies import get_current_user
from app.features.carts.schemas import (
    CartOut,
    AddCartItemRequest,
    UpdateCartItemRequest
)
from app.features.carts.service import (
    create_cart,
    get_cart_details,
    add_cart_item,
    update_cart_item_quantity,
    remove_cart_item
)

router = APIRouter(prefix="/api/carts", tags=["carts"])

@router.post("", response_model=CartOut, status_code=status.HTTP_201_CREATED)
def new_cart(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_cart(user.id, db)

@router.get("/{cart_id}", response_model=CartOut)
def get_cart(
    cart_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_cart_details(cart_id, user.id, db)

@router.post("/{cart_id}/items", response_model=CartOut)
def add_item(
    cart_id: int,
    payload: AddCartItemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return add_cart_item(cart_id, payload.product_id, payload.quantity, user.id, db)

@router.patch("/{cart_id}/items/{item_id}", response_model=CartOut)
def update_item(
    cart_id: int,
    item_id: int,
    payload: UpdateCartItemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_cart_item_quantity(cart_id, item_id, payload.quantity, user.id, db)

@router.delete("/{cart_id}/items/{item_id}", response_model=CartOut)
def remove_item(
    cart_id: int,
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return remove_cart_item(cart_id, item_id, user.id, db)
