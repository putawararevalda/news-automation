"""
Telegram Bot broadcasting service with HTML formatting and chunking logic.
Modular domain service wrapper for backward compatibility and domain clarity.
"""

from backend.app.services.broadcaster import (
    markdown_to_telegram_html,
    split_message_chunks,
    send_telegram_message,
    async_send_telegram_message,
    broadcast_digest_sync,
    broadcast_digest_async,
)

__all__ = [
    "markdown_to_telegram_html",
    "split_message_chunks",
    "send_telegram_message",
    "async_send_telegram_message",
    "broadcast_digest_sync",
    "broadcast_digest_async",
]
