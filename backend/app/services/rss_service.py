"""
RSS / Atom feed fetching and parsing service.
Modular domain service wrapper for backward compatibility and domain clarity.
"""

from backend.app.services.crawler import (
    clean_text,
    parse_date,
    fetch_feed,
    async_fetch_feed,
    parse_feed_xml,
    test_feed_url_sync,
    test_feed_url_async,
)

__all__ = [
    "clean_text",
    "parse_date",
    "fetch_feed",
    "async_fetch_feed",
    "parse_feed_xml",
    "test_feed_url_sync",
    "test_feed_url_async",
]
