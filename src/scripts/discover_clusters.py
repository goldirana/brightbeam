"""Build cluster centroids from training examples."""

import json

from src.config.manager import ConfigManager
from src.services.clustering.category_store import compute_domain_signals


def build_centroids(cfg: ConfigManager) -> None:
    """Discover clusters from training examples and save centroids."""
    examples_dir = cfg.examples_dir
    output_path = cfg.centroids_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load all training transcripts
    transcripts: dict[str, str] = {}
    for f in sorted(examples_dir.glob("*-transcript.txt")):
        tid = f.stem.replace("-transcript", "")
        transcripts[tid] = f.read_text(encoding="utf-8")

    if not transcripts:
        print(f"No transcripts found in {examples_dir}")
        return

    print(f"Processing {len(transcripts)} training transcripts...")

    # Compute domain signals for each transcript
    category_vectors: dict[str, list[list[float]]] = {}

    for tid, text in transcripts.items():
        signals = compute_domain_signals(text)
        best_category = max(signals, key=signals.get)
        vector = list(signals.values())

        if best_category not in category_vectors:
            category_vectors[best_category] = []
        category_vectors[best_category].append(vector)

        print(f"  {tid} -> {best_category} (score: {signals[best_category]:.2f})")

    # Compute centroids (mean of each category's vectors)
    centroids: dict[str, list[float]] = {}
    for category, vectors in category_vectors.items():
        n = len(vectors)
        dim = len(vectors[0])
        centroid = [sum(v[i] for v in vectors) / n for i in range(dim)]
        centroids[category] = centroid
        print(f"  Centroid [{category}]: {n} examples")

    # Save centroids
    output_path.write_text(json.dumps(centroids, indent=2), encoding="utf-8")
    print(f"\nCentroids saved to {output_path}")
