"""
Topic clustering and cross-feed ranking service.
Modular domain service wrapper for backward compatibility and domain clarity.
"""

from backend.app.services.clustering import (
    extract_keywords,
    cluster_articles,
    clean_topic_title,
    STOPWORDS,
    NUMBER_EMOJIS,
)

__all__ = [
    "extract_keywords",
    "cluster_articles",
    "clean_topic_title",
    "STOPWORDS",
    "NUMBER_EMOJIS",
]
