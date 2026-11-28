"""
Gemini AI and local NLP news synthesis service.
Modular domain service wrapper for backward compatibility and domain clarity.
"""

from backend.app.services.synthesizer import (
    generate_cluster_summary_llm,
    generate_cluster_summary_local,
    synthesize_news,
    build_markdown_document,
)

__all__ = [
    "generate_cluster_summary_llm",
    "generate_cluster_summary_local",
    "synthesize_news",
    "build_markdown_document",
]
