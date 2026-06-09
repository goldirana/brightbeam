from pydantic import BaseModel


class CentroidDistance(BaseModel):
    category: str
    cosine_similarity: float


class ClusterAssignment(BaseModel):
    transcript_id: str
    category: str
    confidence: float
    nearest_centroids: list[CentroidDistance] = []
