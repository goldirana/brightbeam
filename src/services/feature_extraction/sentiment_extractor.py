import re

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def extract_sentiment(transcript: str) -> tuple[float, dict[str, float]]:
    """
    Extract sentiment using VADER.
    Returns: (overall_score, per_speaker_scores)
    """
    lines = transcript.strip().split("\n")
    speaker_pattern = re.compile(r"^(\w[\w\s]*?):\s*(.+)")

    speaker_scores: dict[str, list[float]] = {}
    all_scores: list[float] = []

    for line in lines:
        match = speaker_pattern.match(line)
        if match:
            speaker = match.group(1).strip()
            text = match.group(2).strip()
        else:
            text = line.strip()
            speaker = "unknown"

        if not text:
            continue

        score = _analyzer.polarity_scores(text)["compound"]
        all_scores.append(score)

        if speaker not in speaker_scores:
            speaker_scores[speaker] = []
        speaker_scores[speaker].append(score)

    overall = sum(all_scores) / len(all_scores) if all_scores else 0.0
    per_speaker = {s: sum(v) / len(v) for s, v in speaker_scores.items() if v}

    return overall, per_speaker
