from pydantic import BaseModel


class Entity(BaseModel):
    text: str
    label: str  # PERSON, MONEY, DATE, ORG, REF_NUMBER
    confidence: float = 1.0


class SentimentProfile(BaseModel):
    overall: float
    per_speaker: dict[str, float] = {}


class ExtractedFeatures(BaseModel):
    transcript_id: str
    keywords: list[str] = []
    entities: list[Entity] = []
    sentiment: SentimentProfile
    domain_signals: dict[str, float] = {}
