from pathlib import Path
import cv2
from app.core.config import settings

def extract_frames_from_video(video_path: Path, output_dir: Path, max_frames: int = 60) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError("Cannot open video. Try a valid MP4/MOV file.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = count / fps if fps > 0 else 0

    t = 0.0
    paths: list[Path] = []
    interval = max(0.25, settings.video_frame_interval_sec)

    while t <= duration and len(paths) < max_frames:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if ok and frame.shape[0] >= 64 and frame.shape[1] >= 64:
            h, w = frame.shape[:2]
            if max(h, w) > 1280:
                scale = 1280 / max(h, w)
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
            frame_path = output_dir / f"frame_{len(paths):04d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            paths.append(frame_path)
        t += interval

    cap.release()
    if not paths:
        raise ValueError("No usable frames found in video.")
    return paths
