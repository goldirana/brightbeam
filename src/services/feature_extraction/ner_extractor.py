from src.config.manager import ConfigManager
from src.models.features import Entity


def extract_entities_regex(transcript: str) -> list[Entity]:
    """Extract entities using regex patterns from config (fast, no model dependency)."""
    cfg = ConfigManager.get()
    patterns = cfg.ner_patterns
    entities = []

    for label, pattern in patterns.items():
        for match in pattern.finditer(transcript):
            entities.append(Entity(text=match.group().strip(), label=label, confidence=0.9))

    return entities


def extract_entities_spacy(transcript: str) -> list[Entity]:
    """Extract entities using spaCy NER (higher accuracy, requires model)."""
    try:
        import spacy
    except ImportError:
        print("=="*20+"\nSpacy not installed: Fallback to regex for entities extraction\n"+ "=="*20)
        return extract_entities_regex(transcript)

    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Model not downloaded - attempt to download it
        print("=="*20+"\nSpacy model 'en_core_web_sm' not found. Downloading...\n"+ "=="*20)
        try:
            from spacy.cli import download
            download("en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"=="*20+f"\nFailed to download spacy model: {e}. Fallback to regex.\n"+ "=="*20)
            return extract_entities_regex(transcript)

    doc = nlp(transcript)
    entities = []
    for ent in doc.ents:
        if ent.label_ in ("PERSON", "ORG", "MONEY", "DATE", "GPE"):
            entities.append(Entity(text=ent.text, label=ent.label_, confidence=0.85))

    # Also run regex for domain-specific patterns spaCy misses
    regex_entities = extract_entities_regex(transcript)
    seen_texts = {e.text for e in entities}
    for e in regex_entities:
        if e.text not in seen_texts:
            entities.append(e)

    return entities
