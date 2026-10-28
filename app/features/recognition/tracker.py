import time
from typing import Dict, List, Optional
from uuid import uuid4

def compute_iou(boxA: List[int], boxB: List[int]) -> float:
    # box format: [x1, y1, x2, y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])

    union = float(boxAArea + boxBArea - interArea)
    if union <= 0:
        return 0.0
    return interArea / union

class TrackedObject:
    def __init__(self, track_id: str, box: List[int], product_id: Optional[int], timestamp: float):
        self.track_id = track_id
        self.box = box
        self.product_id = product_id
        self.last_seen = timestamp
        self.confirmed_at: Optional[float] = None

class SessionTracker:
    def __init__(self, max_idle_seconds: float = 8.0, min_iou: float = 0.20):
        self.tracks: Dict[str, TrackedObject] = {}
        self.max_idle_seconds = max_idle_seconds
        self.min_iou = min_iou

    def update(self, detections: List[dict]) -> List[dict]:
        now = time.time()
        # 1. Prune stale tracks
        stale_keys = [k for k, t in self.tracks.items() if now - t.last_seen > self.max_idle_seconds]
        for k in stale_keys:
            del self.tracks[k]

        matched_tracks = set()

        for d in detections:
            box = d["box"]
            prod_id = d.get("product_id") or d.get("suggested_product_id")

            best_iou = 0.0
            best_track_id = None

            for tid, track in self.tracks.items():
                if tid in matched_tracks:
                    continue
                # If product_id matches or both are empty, prioritize
                iou = compute_iou(box, track.box)
                if prod_id is not None and track.product_id is not None:
                    if prod_id == track.product_id:
                        iou += 0.15

                if iou > best_iou and iou >= self.min_iou:
                    best_iou = iou
                    best_track_id = tid

            if best_track_id is not None:
                track = self.tracks[best_track_id]
                track.box = box
                track.product_id = prod_id
                track.last_seen = now
                matched_tracks.add(best_track_id)
                d["tracking_id"] = best_track_id
                if track.confirmed_at is not None:
                    d["status"] = "confirmed_in_session"
                else:
                    d["status"] = "candidate" if not d.get("needs_confirmation") else "uncertain"
            else:
                # Assign new tracking ID
                new_id = f"trk_{uuid4().hex[:8]}"
                self.tracks[new_id] = TrackedObject(new_id, box, prod_id, now)
                matched_tracks.add(new_id)
                d["tracking_id"] = new_id
                d["status"] = "candidate" if not d.get("needs_confirmation") else "uncertain"

        return detections

    def mark_confirmed(self, tracking_id: str):
        if tracking_id in self.tracks:
            self.tracks[tracking_id].confirmed_at = time.time()

# Global in-memory session tracker registry: session_id -> SessionTracker
_session_trackers: Dict[int, SessionTracker] = {}

def get_session_tracker(session_id: int) -> SessionTracker:
    if session_id not in _session_trackers:
        _session_trackers[session_id] = SessionTracker()
    return _session_trackers[session_id]

def clear_session_tracker(session_id: int):
    if session_id in _session_trackers:
        del _session_trackers[session_id]
