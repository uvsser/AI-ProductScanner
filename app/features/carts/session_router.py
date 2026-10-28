from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import User
from app.features.auth.dependencies import get_current_user
from app.features.carts.session_schemas import (
    ShoppingSessionOut,
    AddSessionItemRequest,
    UpdateSessionItemRequest,
    SessionActionResponse
)
from app.features.carts.session_service import (
    create_shopping_session,
    get_shopping_session_details,
    confirm_session_item,
    update_session_item_quantity,
    remove_session_item,
    finalize_shopping_session,
    cancel_shopping_session
)

router = APIRouter(prefix="/api/v1/sessions", tags=["shopping-sessions"])

@router.post("", response_model=ShoppingSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_shopping_session(user.id, db)

@router.get("/{session_id}", response_model=ShoppingSessionOut)
def get_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_shopping_session_details(session_id, user.id, db)

@router.post("/{session_id}/items", response_model=ShoppingSessionOut)
def confirm_item(
    session_id: int,
    payload: AddSessionItemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return confirm_session_item(
        session_id=session_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        tracking_id=payload.tracking_id,
        user_id=user.id,
        db=db
    )

@router.patch("/{session_id}/items/{item_id}", response_model=ShoppingSessionOut)
def update_item_quantity(
    session_id: int,
    item_id: int,
    payload: UpdateSessionItemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_session_item_quantity(
        session_id=session_id,
        item_id=item_id,
        quantity=payload.quantity,
        user_id=user.id,
        db=db
    )

@router.delete("/{session_id}/items/{item_id}", response_model=ShoppingSessionOut)
def delete_item(
    session_id: int,
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return remove_session_item(
        session_id=session_id,
        item_id=item_id,
        user_id=user.id,
        db=db
    )

@router.post("/{session_id}/finalize", response_model=SessionActionResponse)
def finalize_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_data = finalize_shopping_session(session_id, user.id, db)
    return {"message": "Shopping session finalized successfully.", "session": session_data}

@router.post("/{session_id}/cancel", response_model=SessionActionResponse)
def cancel_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session_data = cancel_shopping_session(session_id, user.id, db)
    return {"message": "Shopping session cancelled.", "session": session_data}
