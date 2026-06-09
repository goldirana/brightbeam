import re
from collections import Counter

from src.models.features import StructuralMetrics


def extract_structural_metrics(transcript: str) -> StructuralMetrics:
    """Extract structural features from raw transcript text."""
    lines = [line.strip() for line in transcript.split("\n") if line.strip()]
    word_count = len(transcript.split())
    turn_count = len(lines)

    # Count speaker turns
    speaker_pattern = re.compile(r"^(\w[\w\s]*?):", re.MULTILINE)
    speakers = speaker_pattern.findall(transcript)
    speaker_counts = Counter(speakers)

    # Speaker ratio: most frequent (likely agent) vs rest
    if len(speaker_counts) >= 2:
        sorted_speakers = speaker_counts.most_common()
        agent_turns = sorted_speakers[0][1]
        total_turns = sum(speaker_counts.values())
        speaker_ratio = agent_turns / total_turns if total_turns > 0 else 0.5
    else:
        speaker_ratio = 1.0

    # Question density
    questions = len(re.findall(r"\?", transcript))
    question_density = questions / turn_count if turn_count > 0 else 0.0

    return StructuralMetrics(
        word_count=word_count,
        turn_count=turn_count,
        speaker_ratio=speaker_ratio,
        question_density=question_density,
    )
