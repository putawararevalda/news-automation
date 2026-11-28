import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import httpx
except ImportError:
    httpx = None


def markdown_to_telegram_html(content: str, date_obj: Optional[datetime] = None) -> str:
    """Convert summary markdown body to Telegram-compliant HTML message."""
    dt = date_obj or datetime.now()
    today_str = dt.strftime("%A, %d %B %Y")

    tg_header = (
        f"📰 <b>RANGKUMAN 5 BERITA UTAMA</b>\n"
        f"📅 <i>{today_str}</i>\n"
        f"<i>Diurutkan berdasarkan isu yang paling banyak diliput media hari ini:</i>\n\n"
    )

    tg_body = content
    # Replace markdown header hashes
    tg_body = re.sub(r"^#+\s*.*$", "", tg_body, flags=re.MULTILINE)
    # Convert bold **text** to <b>text</b>
    tg_body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", tg_body)
    # Convert italics *(text)* or *text*
    tg_body = re.sub(r"\*(.+?)\*", r"<i>\1</i>", tg_body)
    # Replace markdown links [Title](url) with <a href="url">Title</a>
    tg_body = re.sub(r"\[([^\]]+)\]\((https?://[^\)]+)\)", r'<a href="\2">\1</a>', tg_body)
    # Replace dividers with clean separator
    tg_body = re.sub(r"\n---+\n", r"\n\n━━━━━━━━━━━━━━━━━━━━\n\n", tg_body)
    # Clean excessive whitespace
    tg_body = re.sub(r"\n{3,}", "\n\n", tg_body).strip()

    return tg_header + tg_body


def split_message_chunks(text: str, max_len: int = 4000) -> List[str]:
    """Split long Telegram HTML messages without breaking lines."""
    lines = text.split("\n")
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_len and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    return chunks


def send_telegram_message(token: str, chat_id: str, text_html: str, timeout: int = 15) -> Dict[str, Any]:
    """Send HTML message via Telegram Bot API synchronously."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def async_send_telegram_message(token: str, chat_id: str, text_html: str, timeout: int = 15) -> Dict[str, Any]:
    """Send HTML message via Telegram Bot API asynchronously."""
    if httpx is not None:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text_html,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
    return send_telegram_message(token, chat_id, text_html, timeout=timeout)


def broadcast_digest_sync(
    token: str,
    chat_id: str,
    markdown_content: str,
    date_obj: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Broadcast full markdown content to Telegram with chunking synchronously."""
    html_text = markdown_to_telegram_html(markdown_content, date_obj)
    chunks = split_message_chunks(html_text)
    results = []
    for chunk in chunks:
        res = send_telegram_message(token, chat_id, chunk)
        results.append(res)
    return results


async def broadcast_digest_async(
    token: str,
    chat_id: str,
    markdown_content: str,
    date_obj: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Broadcast full markdown content to Telegram with chunking asynchronously."""
    html_text = markdown_to_telegram_html(markdown_content, date_obj)
    chunks = split_message_chunks(html_text)
    results = []
    for chunk in chunks:
        res = await async_send_telegram_message(token, chat_id, chunk)
        results.append(res)
    return results
