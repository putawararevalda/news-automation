import html
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Optional

try:
    import httpx
except ImportError:
    httpx = None

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
ACCEPT_HEADER = "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"


def clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    date_str = date_str.strip()
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ):
        try:
            if fmt.endswith("Z") and date_str.endswith("Z"):
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    return None


def fetch_feed(url: str, timeout: int = 15) -> Optional[bytes]:
    """Synchronous feed fetcher using urllib (zero external dependency)."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT_HEADER,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


async def async_fetch_feed(url: str, timeout: int = 15) -> Optional[bytes]:
    """Asynchronous feed fetcher using httpx when available, fallback to fetch_feed."""
    if httpx is not None:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT, "Accept": ACCEPT_HEADER},
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            print(f"[WARN] Failed to fetch async {url}: {e}", file=sys.stderr)
            return None
    return fetch_feed(url, timeout=timeout)


def parse_feed_xml(
    xml_bytes: Optional[bytes],
    feed_name: str = "News",
    category: str = "General"
) -> List[Dict[str, Any]]:
    """Parse RSS 2.0 or Atom XML bytes into list of article dicts."""
    if not xml_bytes:
        return []
    entries: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        print(f"[WARN] XML parsing error for {feed_name}: {e}", file=sys.stderr)
        return []

    # Strip XML namespaces for simplified XPath queries
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    # Handle RSS items
    items = root.findall(".//item")
    if items:
        for item in items:
            title = clean_text(item.findtext("title", ""))
            link = clean_text(item.findtext("link", ""))
            desc = clean_text(item.findtext("description", ""))
            pub_date_str = clean_text(item.findtext("pubDate", ""))
            pub_date = parse_date(pub_date_str)
            if title and link:
                entries.append({
                    "title": title,
                    "link": link,
                    "description": desc,
                    "pub_date": pub_date,
                    "source": feed_name,
                    "category": category,
                })
        return entries

    # Handle Atom entries
    atom_entries = root.findall(".//entry")
    if atom_entries:
        for entry in atom_entries:
            title = clean_text(entry.findtext("title", ""))
            link_elem = entry.find("link")
            link = link_elem.get("href", "") if link_elem is not None else ""
            if not link:
                link = clean_text(entry.findtext("link", ""))
            summary = clean_text(entry.findtext("summary", "")) or clean_text(entry.findtext("content", ""))
            pub_date_str = clean_text(entry.findtext("published", "")) or clean_text(entry.findtext("updated", ""))
            pub_date = parse_date(pub_date_str)
            if title and link:
                entries.append({
                    "title": title,
                    "link": link,
                    "description": summary,
                    "pub_date": pub_date,
                    "source": feed_name,
                    "category": category,
                })
    return entries


def probe_feed_info(xml_bytes: Optional[bytes]) -> Dict[str, Any]:
    """Extract feed-level title and description from XML."""
    if not xml_bytes:
        return {"title": "", "description": ""}
    try:
        root = ET.fromstring(xml_bytes)
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]
        channel = root.find(".//channel")
        if channel is not None:
            title = clean_text(channel.findtext("title", ""))
            desc = clean_text(channel.findtext("description", ""))
            return {"title": title, "description": desc}
        title = clean_text(root.findtext("title", ""))
        desc = clean_text(root.findtext("subtitle", ""))
        return {"title": title, "description": desc}
    except Exception:
        return {"title": "", "description": ""}


def test_feed_url_sync(url: str, limit: int = 3) -> Dict[str, Any]:
    """Test RSS feed probe synchronously."""
    xml_bytes = fetch_feed(url, timeout=10)
    if not xml_bytes:
        return {
            "status": "error",
            "message": f"Unable to reach or fetch content from {url}",
            "feed_title": None,
            "total_articles": 0,
            "preview_articles": [],
        }

    info = probe_feed_info(xml_bytes)
    articles = parse_feed_xml(xml_bytes, feed_name=info["title"] or "Feed Probe", category="Probe")
    if not articles:
        return {
            "status": "error",
            "message": "Feed content retrieved but no valid RSS/Atom articles found.",
            "feed_title": info.get("title"),
            "total_articles": 0,
            "preview_articles": [],
        }

    preview = [
        {
            "title": a["title"],
            "link": a["link"],
            "snippet": a.get("description", "")[:200],
            "published_at": a["pub_date"].isoformat() if a.get("pub_date") else None,
        }
        for a in articles[:limit]
    ]

    return {
        "status": "ok",
        "message": f"Successfully parsed {len(articles)} articles.",
        "feed_title": info.get("title") or url,
        "total_articles": len(articles),
        "preview_articles": preview,
    }


async def test_feed_url_async(url: str, limit: int = 3) -> Dict[str, Any]:
    """Test RSS feed probe asynchronously for FastAPI endpoints."""
    xml_bytes = await async_fetch_feed(url, timeout=10)
    if not xml_bytes:
        return {
            "status": "error",
            "message": f"Unable to reach or fetch content from {url}",
            "feed_title": None,
            "total_articles": 0,
            "preview_articles": [],
        }

    info = probe_feed_info(xml_bytes)
    articles = parse_feed_xml(xml_bytes, feed_name=info["title"] or "Feed Probe", category="Probe")
    if not articles:
        return {
            "status": "error",
            "message": "Feed content retrieved but no valid RSS/Atom articles found.",
            "feed_title": info.get("title"),
            "total_articles": 0,
            "preview_articles": [],
        }

    preview = [
        {
            "title": a["title"],
            "link": a["link"],
            "snippet": a.get("description", "")[:200],
            "published_at": a["pub_date"].isoformat() if a.get("pub_date") else None,
        }
        for a in articles[:limit]
    ]

    return {
        "status": "ok",
        "message": f"Successfully parsed {len(articles)} articles.",
        "feed_title": info.get("title") or url,
        "total_articles": len(articles),
        "preview_articles": preview,
    }
