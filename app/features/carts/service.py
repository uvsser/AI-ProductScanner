from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from app.infrastructure.database.models import Cart, CartItem, Product
from app.features.carts.schemas import CartOut, CartItemOut

def calculate_cart_out(cart: Cart) -> dict:
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
            "description": (it.product.description or "") if it.product else "",
            "quantity": it.quantity,
            "unit_price": round(it.unit_price_at_addition, 2),
            "subtotal": subtotal
        })

    return {
        "id": cart.id,
        "status": cart.status,
        "items": items_out,
        "total": round(total, 2),
        "currency": currency
    }

def get_user_cart_or_404(cart_id: int, user_id: int, db: Session) -> Cart:
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .filter(Cart.id == cart_id, Cart.user_id == user_id)
        .first()
    )
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found.")
    return cart

def create_cart(user_id: int, db: Session) -> dict:
    cart = Cart(user_id=user_id)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return calculate_cart_out(get_user_cart_or_404(cart.id, user_id, db))

def get_cart_details(cart_id: int, user_id: int, db: Session) -> dict:
    cart = get_user_cart_or_404(cart_id, user_id, db)
    return calculate_cart_out(cart)

def add_cart_item(cart_id: int, product_id: int, quantity: int, user_id: int, db: Session) -> dict:
    cart = db.query(Cart).filter(Cart.id == cart_id, Cart.user_id == user_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found.")

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.user_id == user_id,
        Product.status == "ready"
    ).first()
    if not product:
        raise HTTPException(404, "Product not found in your catalog.")

    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product.id
    ).first()

    if existing_item:
        new_qty = existing_item.quantity + quantity
        if new_qty > 100:
            raise HTTPException(400, "Quantity cannot exceed 100.")
        existing_item.quantity = new_qty
    else:
        db.add(CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            unit_price_at_addition=product.price
        ))

    db.commit()
    return calculate_cart_out(get_user_cart_or_404(cart.id, user_id, db))

def update_cart_item_quantity(cart_id: int, item_id: int, quantity: int, user_id: int, db: Session) -> dict:
    cart = db.query(Cart).filter(Cart.id == cart_id, Cart.user_id == user_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found.")

    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(404, "Cart item not found.")

    item.quantity = quantity
    db.commit()
    return calculate_cart_out(get_user_cart_or_404(cart.id, user_id, db))

def remove_cart_item(cart_id: int, item_id: int, user_id: int, db: Session) -> dict:
    cart = db.query(Cart).filter(Cart.id == cart_id, Cart.user_id == user_id).first()
    if not cart:
        raise HTTPException(404, "Cart not found.")

    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(404, "Cart item not found.")

    db.delete(item)
    db.commit()
    return calculate_cart_out(get_user_cart_or_404(cart.id, user_id, db))
