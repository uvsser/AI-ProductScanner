import unittest
from app.features.recognition.tracker import SessionTracker, compute_iou

class TestTracker(unittest.TestCase):
    def test_compute_iou_overlap(self):
        boxA = [10, 10, 100, 100]
        boxB = [10, 10, 100, 100]
        self.assertAlmostEqual(compute_iou(boxA, boxB), 1.0)

        boxC = [50, 50, 150, 150]
        iou = compute_iou(boxA, boxC)
        self.assertGreater(iou, 0.1)
        self.assertLess(iou, 0.5)

        boxD = [200, 200, 300, 300]
        self.assertEqual(compute_iou(boxA, boxD), 0.0)

    def test_tracker_preserves_id_across_frames(self):
        tracker = SessionTracker(max_idle_seconds=2.0, min_iou=0.3)

        # Frame 1
        f1_dets = [{
            "box": [50, 50, 200, 200],
            "product_id": 10,
            "detected_class": "bottle",
            "needs_confirmation": False
        }]
        res1 = tracker.update(f1_dets)
        track_id = res1[0]["tracking_id"]
        self.assertTrue(track_id.startswith("trk_"))
        self.assertEqual(res1[0]["status"], "candidate")

        # Frame 2 (slightly moved bounding box of the same object)
        f2_dets = [{
            "box": [55, 52, 205, 202],
            "product_id": 10,
            "detected_class": "bottle",
            "needs_confirmation": False
        }]
        res2 = tracker.update(f2_dets)
        self.assertEqual(res2[0]["tracking_id"], track_id)

        # Confirm the track
        tracker.mark_confirmed(track_id)

        # Frame 3 (same object still visible)
        f3_dets = [{
            "box": [58, 54, 208, 204],
            "product_id": 10,
            "detected_class": "bottle",
            "needs_confirmation": False
        }]
        res3 = tracker.update(f3_dets)
        self.assertEqual(res3[0]["tracking_id"], track_id)
        self.assertEqual(res3[0]["status"], "confirmed_in_session")

    def test_tracker_differentiates_new_object(self):
        tracker = SessionTracker(max_idle_seconds=2.0, min_iou=0.3)

        f1 = [{"box": [10, 10, 50, 50], "product_id": 1}]
        f2 = [{"box": [300, 300, 400, 400], "product_id": 2}]

        r1 = tracker.update(f1)
        r2 = tracker.update(f2)

        self.assertNotEqual(r1[0]["tracking_id"], r2[0]["tracking_id"])

if __name__ == "__main__":
    unittest.main()
