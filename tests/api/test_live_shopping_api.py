import io
import unittest
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.infrastructure.database.models import User, Product
from tests.api.test_db import test_engine, TestingSessionLocal

class TestLiveShoppingFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_session_lifecycle_and_cross_store_isolation(self):
        # Create dedicated store users for this test
        res_a = self.client.post("/api/auth/register", json={"email": "store_alpha@storefront.com", "password": "password123"})
        token_a = res_a.json()["access_token"]
        user_a_id = res_a.json()["user"]["id"]

        res_b = self.client.post("/api/auth/register", json={"email": "store_beta@storefront.com", "password": "password123"})
        token_b = res_b.json()["access_token"]

        # Insert a ready product for Store A
        db = TestingSessionLocal()
        prod_a = Product(
            user_id=user_a_id,
            title="Orange Juice 1L",
            barcode="61110001",
            price=15.50,
            currency="MAD",
            status="ready"
        )
        db.add(prod_a)
        db.commit()
        product_a_id = prod_a.id
        db.close()

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 1. Store A opens a shopping session
        res_sess = self.client.post("/api/v1/sessions", headers=headers_a)
        self.assertEqual(res_sess.status_code, 201)
        sess_a_id = res_sess.json()["id"]
        self.assertEqual(res_sess.json()["status"], "open")

        # 2. Store B attempts unauthorized access to Store A's session -> 404/Unauthorized
        res_unauth = self.client.get(f"/api/v1/sessions/{sess_a_id}", headers=headers_b)
        self.assertEqual(res_unauth.status_code, 404)

        # 3. Store A confirms product into shopping list
        res_add = self.client.post(
            f"/api/v1/sessions/{sess_a_id}/items",
            headers=headers_a,
            json={"product_id": product_a_id, "quantity": 2, "tracking_id": "trk_test123"}
        )
        self.assertEqual(res_add.status_code, 200)
        cart_data = res_add.json()
        self.assertEqual(len(cart_data["items"]), 1)
        self.assertEqual(cart_data["items"][0]["quantity"], 2)
        self.assertEqual(cart_data["total"], 31.00)  # 2 * 15.50

        # 4. Finalize session
        res_fin = self.client.post(f"/api/v1/sessions/{sess_a_id}/finalize", headers=headers_a)
        self.assertEqual(res_fin.status_code, 200)
        self.assertEqual(res_fin.json()["session"]["status"], "finalized")

        # 5. Cannot add item to finalized session
        res_closed = self.client.post(
            f"/api/v1/sessions/{sess_a_id}/items",
            headers=headers_a,
            json={"product_id": product_a_id, "quantity": 1}
        )
        self.assertEqual(res_closed.status_code, 400)

    @patch("app.features.recognition.live_router.run_recognition_pipeline")
    def test_live_frame_scan_endpoint(self, mock_pipeline):
        res_u = self.client.post("/api/auth/register", json={"email": "store_gamma@storefront.com", "password": "password123"})
        token_u = res_u.json()["access_token"]
        user_u_id = res_u.json()["user"]["id"]

        db = TestingSessionLocal()
        prod = Product(
            user_id=user_u_id,
            title="Sparkling Water",
            barcode="62220002",
            price=8.00,
            currency="MAD",
            status="ready"
        )
        db.add(prod)
        db.commit()
        prod_id = prod.id
        db.close()

        headers = {"Authorization": f"Bearer {token_u}"}

        # Open session
        res_sess = self.client.post("/api/v1/sessions", headers=headers)
        session_id = res_sess.json()["id"]

        # Mock recognition output
        mock_pipeline.return_value = [{
            "detection_index": 0,
            "box": [20, 20, 180, 180],
            "detected_class": "bottle",
            "detector_confidence": 0.92,
            "product_id": prod_id,
            "suggested_product_id": prod_id,
            "title": "Sparkling Water",
            "suggested_title": "Sparkling Water",
            "price": 8.00,
            "currency": "MAD",
            "similarity": 0.88,
            "barcode_detected": "62220002",
            "ocr_text_snippet": "SPARKLING",
            "match_method": "barcode",
            "needs_confirmation": False
        }]

        # Create dummy JPEG image
        img_byte_arr = io.BytesIO()
        Image.new("RGB", (320, 240), color=(100, 100, 100)).save(img_byte_arr, format="JPEG")
        img_bytes = img_byte_arr.getvalue()

        # Send frame
        res_frame = self.client.post(
            f"/api/v1/live-scan/{session_id}/frame",
            headers=headers,
            files={"file": ("frame.jpg", img_bytes, "image/jpeg")},
            data={"frame_timestamp_ms": 123456}
        )
        self.assertEqual(res_frame.status_code, 200)
        data = res_frame.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(len(data["detections"]), 1)
        self.assertTrue(data["detections"][0]["tracking_id"].startswith("trk_"))
        self.assertEqual(data["detections"][0]["status"], "confirmed_in_session")
        self.assertIsNotNone(data["session"])
        self.assertEqual(data["session"]["total"], 8.00)
        self.assertEqual(len(data["session"]["items"]), 1)

    @patch("app.features.recognition.live_router.run_recognition_pipeline")
    def test_live_frame_empty_fallback_does_not_add_to_cart(self, mock_pipeline):
        res_u = self.client.post("/api/auth/register", json={"email": "store_delta@storefront.com", "password": "password123"})
        token_u = res_u.json()["access_token"]
        headers = {"Authorization": f"Bearer {token_u}"}

        res_sess = self.client.post("/api/v1/sessions", headers=headers)
        session_id = res_sess.json()["id"]

        # Mock fallback detection (empty frame with no objects)
        mock_pipeline.return_value = [{
            "detection_index": 0,
            "box": [0, 0, 320, 240],
            "detected_class": "whole_image_fallback",
            "detector_confidence": 0.0,
            "product_id": 99,
            "suggested_product_id": 99,
            "title": "Unidentified object",
            "price": 2.00,
            "currency": "MAD",
            "similarity": 0.50,
            "barcode_detected": "",
            "ocr_text_snippet": "",
            "match_method": "visual",
            "needs_confirmation": True
        }]

        img_byte_arr = io.BytesIO()
        Image.new("RGB", (320, 240), color=(200, 200, 200)).save(img_byte_arr, format="JPEG")

        res_frame = self.client.post(
            f"/api/v1/live-scan/{session_id}/frame",
            headers=headers,
            files={"file": ("frame.jpg", img_byte_arr.getvalue(), "image/jpeg")},
            data={"frame_timestamp_ms": 123456}
        )
        self.assertEqual(res_frame.status_code, 200)
        data = res_frame.json()
        self.assertIsNotNone(data["session"])
        # Session items must remain 0! Nothing hallucinated or auto-added from blank frame!
        self.assertEqual(len(data["session"]["items"]), 0)
        self.assertEqual(data["session"]["total"], 0.0)

if __name__ == "__main__":
    unittest.main()
