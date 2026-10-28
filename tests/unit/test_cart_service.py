import unittest
from unittest.mock import MagicMock
from app.infrastructure.database.models import Cart, CartItem, Product
from app.features.carts.service import calculate_cart_out

class TestCartService(unittest.TestCase):
    def test_calculate_cart_out_empty(self):
        cart = MagicMock(spec=Cart)
        cart.id = 1
        cart.status = "open"
        cart.items = []

        result = calculate_cart_out(cart)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["total"], 0.0)
        self.assertEqual(result["items"], [])

    def test_calculate_cart_out_with_items(self):
        cart = MagicMock(spec=Cart)
        cart.id = 1
        cart.status = "open"

        product1 = MagicMock(spec=Product)
        product1.title = "Coffee Mug"
        product1.description = "Ceramic 350ml mug"
        product1.currency = "USD"

        item1 = MagicMock(spec=CartItem)
        item1.id = 10
        item1.product_id = 101
        item1.product = product1
        item1.quantity = 2
        item1.unit_price_at_addition = 12.50

        product2 = MagicMock(spec=Product)
        product2.title = "Notebook"
        product2.description = ""
        product2.currency = "USD"

        item2 = MagicMock(spec=CartItem)
        item2.id = 11
        item2.product_id = 102
        item2.product = product2
        item2.quantity = 3
        item2.unit_price_at_addition = 5.00

        cart.items = [item1, item2]

        result = calculate_cart_out(cart)
        self.assertEqual(result["total"], 40.0)  # 2*12.50 + 3*5.00 = 25.0 + 15.0 = 40.0
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["subtotal"], 25.0)
        self.assertEqual(result["items"][0]["description"], "Ceramic 350ml mug")
        self.assertEqual(result["items"][1]["subtotal"], 15.0)
        self.assertEqual(result["items"][1]["description"], "")

if __name__ == "__main__":
    unittest.main()
