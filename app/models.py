# Compatibility bridge for existing models imports
from app.infrastructure.database.models import (
    User,
    Product,
    ProductImage,
    ProductEmbedding,
    Cart,
    CartItem
)

__all__ = ["User", "Product", "ProductImage", "ProductEmbedding", "Cart", "CartItem"]
