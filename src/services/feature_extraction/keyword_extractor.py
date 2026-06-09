import re

from src.config.manager import ConfigManager


def extract_keywords_tfidf(corpus: list[str], target_text: str, top_n: int | None = None) -> list[str]:
    """Extract keywords using TF-IDF from sklearn."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    cfg = ConfigManager.get()
    if top_n is None:
        top_n = cfg.top_keywords

    vectorizer = TfidfVectorizer(
        max_features=cfg.tfidf_max_features,
        stop_words="english",
        ngram_range=cfg.tfidf_ngram_range,
    )
    tfidf_matrix = vectorizer.fit_transform(corpus + [target_text])

    # Get the TF-IDF scores for the target text (last document)
    target_vector = tfidf_matrix[-1]
    feature_names = vectorizer.get_feature_names_out()

    # Sort by score
    scores = target_vector.toarray().flatten()
    top_indices = scores.argsort()[-top_n:][::-1]

    return [feature_names[i] for i in top_indices if scores[i] > 0]


def extract_keywords_rake(text: str, top_n: int | None = None) -> list[str]:
    """Extract keywords using RAKE algorithm (no external corpus needed)."""
    cfg = ConfigManager.get()
    if top_n is None:
        top_n = cfg.top_keywords

    stop_words = cfg.stop_words

    # Split into phrases using delimiters
    sentences = re.split(r"[.!?,;:\n]", text.lower())
    phrases = []
    for sentence in sentences:
        words = sentence.split()
        phrase = []
        for word in words:
            clean_word = re.sub(r"[^a-z0-9]", "", word)
            if clean_word and clean_word not in stop_words:
                phrase.append(clean_word)
            else:
                if phrase:
                    phrases.append(" ".join(phrase))
                    phrase = []
        if phrase:
            phrases.append(" ".join(phrase))

    # Score phrases by word frequency and degree
    word_freq: dict[str, int] = {}
    word_degree: dict[str, int] = {}
    for phrase in phrases:
        words = phrase.split()
        degree = len(words) - 1
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
            word_degree[word] = word_degree.get(word, 0) + degree

    word_score = {w: (word_degree[w] + word_freq[w]) / word_freq[w] for w in word_freq}

    # Score phrases
    phrase_scores: dict[str, float] = {}
    for phrase in set(phrases):
        score = sum(word_score.get(w, 0) for w in phrase.split())
        phrase_scores[phrase] = score

    sorted_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)
    return [phrase for phrase, _ in sorted_phrases[:top_n]]
