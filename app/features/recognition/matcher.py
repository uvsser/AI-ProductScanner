import numpy as np

def match_query_to_candidates(
    query_vector: np.ndarray,
    candidates: list[tuple[int, str, np.ndarray]]
) -> dict | None:
    """
    Computes cosine similarity between query_vector and each candidate embedding.
    candidates is a list of (product_id, title, vector).
    Returns dict with top match or None if candidates list is empty.
    """
    if not candidates:
        return None

    # Ensure query vector is unit normalized
    norm = np.linalg.norm(query_vector)
    if norm > 0:
        q = query_vector / norm
    else:
        q = query_vector

    scored = []
    for pid, title, vector in candidates:
        v_norm = np.linalg.norm(vector)
        v = vector / v_norm if v_norm > 0 else vector
        similarity = float(np.dot(q, v))
        scored.append((similarity, pid, title))

    best_score, best_pid, best_title = max(scored, key=lambda x: x[0])
    return {
        "product_id": best_pid,
        "title": best_title,
        "similarity": best_score
    }
