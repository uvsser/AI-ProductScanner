from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from app.infrastructure.database.models import Cart, CartItem, Product
from app.features.carts.session_schemas import ShoppingSessionOut, SessionItemOut
from app.features.recognition.tracker import get_session_tracker, clear_session_tracker

def calculate_session_out(cart: Cart) -> dict:
    items_out = []
    total = 0.0
    currency = "MAD"

    for it in cart.items:
        subtotal = round(it.quantity * it.unit_price_at_addition, 2)
        total += subtotal
        if it.product and it.product.currency:
            currency = it.product.currency

        items_out.append({
            "id": it.id,
            "product_id": it.product_id,
            "title": it.product.title if it.product else "Unknown Product",
            "description": it.product.description if it.product else "",
            "quantity": it.quantity,
            "unit_price": round(it.unit_price_at_addition, 2),
            "subtotal": subtotal
        })

    return {
        "id": cart.id,
        "user_id": cart.user_id,
        "status": cart.status,
        "items": items_out,
        "total": round(total, 2),
        "currency": currency
    }

def get_authorized_session_or_404(session_id: int, user_id: int, db: Session) -> Cart:
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .filter(Cart.id == session_id, Cart.user_id == user_id)
        .first()
    )
    if not cart:
        raise HTTPException(status_code=404, detail="Shopping session not found or unauthorized.")
    return cart

def create_shopping_session(user_id: int, db: Session) -> dict:
    cart = Cart(user_id=user_id, status="open")
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return calculate_session_out(get_authorized_session_or_404(cart.id, user_id, db))

def get_shopping_session_details(session_id: int, user_id: int, db: Session) -> dict:
    cart = get_authorized_session_or_404(session_id, user_id, db)
    return calculate_session_out(cart)

def confirm_session_item(
    session_id: int,
    product_id: int,
    quantity: int,
    tracking_id: str | None,
    user_id: int,
    db: Session
) -> dict:
    cart = get_authorized_session_or_404(session_id, user_id, db)
    if cart.status != "open":
        raise HTTPException(status_code=400, detail=f"Cannot add items to a {cart.status} session.")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == user_id,
        Product.status == "ready"
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found in this store catalog.")

    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product.id
    ).first()

    if existing_item:
        new_qty = existing_item.quantity + quantity
        if new_qty > 100:
            raise HTTPException(status_code=400, detail="Quantity cannot exceed 100 units.")
        existing_item.quantity = new_qty
    else:
        db.add(CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            unit_price_at_addition=product.price
        ))

    db.commit()

    # Mark object tracking ID as confirmed in session tracker
    if tracking_id:
        tracker = get_session_tracker(session_id)
        tracker.mark_confirmed(tracking_id)

    return calculate_session_out(get_authorized_session_or_404(session_id, user_id, db))

def update_session_item_quantity(
    session_id: int,
    item_id: int,
    quantity: int,
    user_id: int,
    db: Session
) -> dict:
    cart = get_authorized_session_or_404(session_id, user_id, db)
    if cart.status != "open":
        raise HTTPException(status_code=400, detail=f"Cannot modify items in a {cart.status} session.")

    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Session item not found.")

    item.quantity = quantity
    db.commit()
    return calculate_session_out(get_authorized_session_or_404(session_id, user_id, db))

def remove_session_item(
    session_id: int,
    item_id: int,
    user_id: int,
    db: Session
) -> dict:
    cart = get_authorized_session_or_404(session_id, user_id, db)
    if cart.status != "open":
        raise HTTPException(status_code=400, detail=f"Cannot remove items from a {cart.status} session.")

    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Session item not found.")

    db.delete(item)
    db.commit()
    return calculate_session_out(get_authorized_session_or_404(session_id, user_id, db))

def finalize_shopping_session(session_id: int, user_id: int, db: Session) -> dict:
    cart = get_authorized_session_or_404(session_id, user_id, db)
    if cart.status != "open":
        raise HTTPException(status_code=400, detail=f"Session is already {cart.status}.")

    cart.status = "finalized"
    db.commit()
    clear_session_tracker(session_id)
    return calculate_session_out(get_authorized_session_or_404(session_id, user_id, db))

def cancel_shopping_session(session_id: int, user_id: int, db: Session) -> dict:
    cart = get_authorized_session_or_404(session_id, user_id, db)
    cart.status = "cancelled"
    db.commit()
    clear_session_tracker(session_id)
    return calculate_session_out(get_authorized_session_or_404(session_id, user_id, db))
