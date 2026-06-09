import json
from pathlib import Path

import numpy as np

from src.models.clustering import CentroidDistance, ClusterAssignment


class ClusterService:
    """Assigns transcripts to categories using cosine similarity against centroids."""

    def __init__(self, centroids_path: Path):
        self.centroids: dict[str, list[float]] = {}
        if centroids_path.exists():
            self.centroids = json.loads(centroids_path.read_text())

    def assign(self, transcript_id: str, feature_vector: list[float]) -> ClusterAssignment:
        """Assign a transcript to the nearest category centroid."""
        if not self.centroids:
            return ClusterAssignment(
                transcript_id=transcript_id,
                category="general",
                confidence=0.5,
                nearest_centroids=[],
            )

        vec = np.array(feature_vector)
        distances = []

        for category, centroid in self.centroids.items():
            centroid_vec = np.array(centroid)
            similarity = self._cosine_similarity(vec, centroid_vec)
            distances.append(CentroidDistance(category=category, cosine_similarity=float(similarity)))

        distances.sort(key=lambda x: x.cosine_similarity, reverse=True)
        best = distances[0]

        return ClusterAssignment(
            transcript_id=transcript_id,
            category=best.category,
            confidence=best.cosine_similarity,
            nearest_centroids=distances[:3],
        )

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
