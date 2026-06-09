import re

from src.models.features import Entity
from src.models.validation import EntityMismatch, FactualCheck


def validate_facts(
    transcript_id: str,
    transcript_entities: list[Entity],
    summary_text: str,
) -> FactualCheck:
    """Cross-check entities found in transcript against the summary text."""
    # Extract entities from summary using same patterns
    from src.services.feature_extraction.ner_extractor import extract_entities_regex

    summary_entities = extract_entities_regex(summary_text)

    transcript_texts = {e.text.lower().strip() for e in transcript_entities}
    summary_texts = {e.text.lower().strip() for e in summary_entities}

    # Hallucinated: in summary but not in transcript
    hallucinated = [e for e in summary_entities if e.text.lower().strip() not in transcript_texts]

    # Missing critical: in transcript but not in summary (only critical types)
    critical_types = {"MONEY", "REF_NUMBER", "PHONE", "EMAIL", "IBAN"}
    missing = [
        e for e in transcript_entities
        if e.label in critical_types and e.text.lower().strip() not in summary_texts
    ]

    # Score
    total_checks = len(summary_entities) + len([e for e in transcript_entities if e.label in critical_types])
    errors = len(hallucinated) + len(missing)
    factual_score = max(0.0, 1.0 - (errors / total_checks)) if total_checks > 0 else 1.0

    return FactualCheck(
        transcript_id=transcript_id,
        entities_in_transcript=transcript_entities,
        entities_in_summary=summary_entities,
        hallucinated_entities=hallucinated,
        missing_critical_entities=missing,
        mismatched_values=[],
        factual_score=factual_score,
    )
