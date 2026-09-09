"""
Classifier: answers "which media belong together?" — nothing more.
No summarization, no opinions, just clustering.

Uses sentence-transformers embeddings + cosine similarity when available.
Since that model needs a one-time download from the internet, and this
environment may not always have that, it falls back to a TF-IDF vector
space (scikit-learn) if the transformer model can't load — same
downstream clustering logic either way, just a different embedding.
"""
from __future__ import annotations
import logging
from typing import List

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from models.media import MediaItem
import config

logger = logging.getLogger(__name__)


class Classifier:
    def __init__(self, similarity_threshold: float | None = None):
        self.threshold = (
            similarity_threshold if similarity_threshold is not None
            else config.CLUSTER_SIMILARITY_THRESHOLD
        )
        self._model = self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            return SentenceTransformer(config.EMBEDDING_MODEL)
        except Exception as e:
            logger.warning(
                "Classifier: sentence-transformers unavailable (%s) — "
                "falling back to TF-IDF embeddings", e,
            )
            return None

    def _embed(self, texts: List[str]) -> np.ndarray:
        if self._model is not None:
            return np.array(self._model.encode(texts))

        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
        matrix = vectorizer.fit_transform(texts)
        return matrix.toarray()

    def cluster(self, items: List[MediaItem]) -> List[List[MediaItem]]:
        if not items:
            return []
        if len(items) == 1:
            return [items]

        texts = [f"{m.title} {m.description or ''}".strip() for m in items]
        embeddings = self._embed(texts)
        sim_matrix = cosine_similarity(embeddings)

        assigned = [False] * len(items)
        clusters: List[List[MediaItem]] = []

        # Greedy single-link clustering: good enough for an MVP's "same
        # event" grouping, and deterministic/easy to reason about.
        for i in range(len(items)):
            if assigned[i]:
                continue
            cluster_indices = [i]
            assigned[i] = True
            for j in range(i + 1, len(items)):
                if assigned[j]:
                    continue
                if sim_matrix[i][j] >= self.threshold:
                    cluster_indices.append(j)
                    assigned[j] = True
            clusters.append([items[k] for k in cluster_indices])

        logger.info(
            "Classifier: %d items -> %d clusters (threshold=%.2f, model=%s)",
            len(items), len(clusters), self.threshold,
            "sentence-transformers" if self._model else "tfidf-fallback",
        )
        clusters = self._apply_forced_links(clusters)
        return clusters

    @staticmethod
    def _apply_forced_links(clusters: List[List[MediaItem]]) -> List[List[MediaItem]]:
        """Merges clusters together when they contain items matching
        different phrases from the same FORCED_LINK_GROUPS entry —
        overrides normal similarity-based clustering for these topics."""
        for group in config.FORCED_LINK_GROUPS:
            group_lower = [g.lower() for g in group]
            matching_indices = []
            for idx, cluster in enumerate(clusters):
                text = " ".join(f"{m.title} {m.description or ''}" for m in cluster).lower()
                if any(phrase in text for phrase in group_lower):
                    matching_indices.append(idx)

            if len(matching_indices) > 1:
                merged: List[MediaItem] = []
                for idx in matching_indices:
                    merged.extend(clusters[idx])
                # remove the merged clusters (highest index first) and append the combined one
                for idx in sorted(matching_indices, reverse=True):
                    del clusters[idx]
                clusters.append(merged)
                logger.info(
                    "Classifier: forced-link group %s merged %d clusters into 1 (%d items)",
                    group, len(matching_indices), len(merged),
                )
        return clusters
