import unittest
from fastapi.testclient import TestClient
from app.main import app
from tests.api.test_db import test_engine, TestingSessionLocal

class TestApiFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_auth_and_cart_lifecycle(self):
        # 1. Register
        reg_payload = {"email": "testuser_unique@example.com", "password": "securepassword123"}
        res = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Whoami
        res_me = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.json()["email"], "testuser_unique@example.com")

        # 3. Create Cart
        res_cart = self.client.post("/api/carts", headers=headers)
        self.assertEqual(res_cart.status_code, 201)
        cart_id = res_cart.json()["id"]

        # 4. Get Cart
        res_get_cart = self.client.get(f"/api/carts/{cart_id}", headers=headers)
        self.assertEqual(res_get_cart.status_code, 200)
        self.assertEqual(res_get_cart.json()["total"], 0.0)

    def test_photo_scan_auto_confirm_and_description(self):
        from unittest.mock import patch
        import io
        from PIL import Image
        from app.infrastructure.database.models import Product

        res_u = self.client.post("/api/auth/register", json={"email": "autoscan_user@store.com", "password": "securepassword123"})
        token_u = res_u.json()["access_token"]
        user_u_id = res_u.json()["user"]["id"]
        headers = {"Authorization": f"Bearer {token_u}"}

        db = TestingSessionLocal()
        prod = Product(
            user_id=user_u_id,
            title="Premium Olive Oil 1L",
            description="Extra virgin cold-pressed olive oil",
            barcode="61110001",
            price=45.00,
            currency="MAD",
            status="ready"
        )
        db.add(prod)
        db.commit()
        prod_id = prod.id
        db.close()

        res_cart = self.client.post("/api/carts", headers=headers)
        cart_id = res_cart.json()["id"]

        img_byte_arr = io.BytesIO()
        Image.new("RGB", (320, 240), color=(120, 120, 120)).save(img_byte_arr, format="JPEG")
        img_bytes = img_byte_arr.getvalue()

        mock_detection = [
            {
                "detection_index": 0,
                "box": [10, 10, 100, 100],
                "detected_class": "bottle",
                "detector_confidence": 0.95,
                "product_id": prod_id,
                "suggested_product_id": prod_id,
                "title": "Premium Olive Oil 1L",
                "suggested_title": "Premium Olive Oil 1L",
                "description": "Extra virgin cold-pressed olive oil",
                "price": 45.00,
                "currency": "MAD",
                "similarity": 0.92,
                "barcode_detected": "61110001",
                "ocr_text_snippet": "OLIVE OIL",
                "match_method": "barcode",
                "needs_confirmation": False
            },
            {
                "detection_index": 1,
                "box": [120, 10, 210, 100],
                "detected_class": "bottle",
                "detector_confidence": 0.93,
                "product_id": prod_id,
                "suggested_product_id": prod_id,
                "title": "Premium Olive Oil 1L",
                "suggested_title": "Premium Olive Oil 1L",
                "description": "Extra virgin cold-pressed olive oil",
                "price": 45.00,
                "currency": "MAD",
                "similarity": 0.90,
                "barcode_detected": "61110001",
                "ocr_text_snippet": "OLIVE OIL",
                "match_method": "barcode",
                "needs_confirmation": False
            }
        ]

        with patch("app.features.recognition.router.run_recognition_pipeline", return_value=mock_detection):
            res_scan = self.client.post(
                f"/api/carts/{cart_id}/scan",
                headers=headers,
                files={"file": ("photo.jpg", img_bytes, "image/jpeg")}
            )
            self.assertEqual(res_scan.status_code, 200)
            data = res_scan.json()
            self.assertIsNotNone(data["cart"])
            # 2 duplicates counted: quantity = 2, total = 90.00
            self.assertEqual(data["cart"]["total"], 90.00)
            self.assertEqual(len(data["cart"]["items"]), 1)
            self.assertEqual(data["cart"]["items"][0]["quantity"], 2)
            self.assertEqual(data["cart"]["items"][0]["description"], "Extra virgin cold-pressed olive oil")
            self.assertEqual(len(data["detections"]), 2)

if __name__ == "__main__":
    unittest.main()
