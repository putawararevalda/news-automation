from datetime import datetime, timezone
from backend.app.services.crawler import (
    clean_text,
    parse_date,
    parse_feed_xml,
    probe_feed_info,
)

SAMPLE_RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample News Channel</title>
    <link>https://example.com</link>
    <description>Sample Description</description>
    <item>
      <title>&lt;b&gt;Breaking News&lt;/b&gt;: Market Surges</title>
      <link>https://example.com/market-surge</link>
      <description>Stocks &amp; commodities climbed &lt;span&gt;sharply&lt;/span&gt; today.</description>
      <pubDate>Mon, 28 Nov 2026 09:30:00 +0700</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Tech Feed</title>
  <entry>
    <title>New AI Innovation Launched</title>
    <link href="https://example.com/ai-innovation" />
    <summary>AI model achieves state-of-the-art benchmark results.</summary>
    <published>2026-11-28T02:30:00Z</published>
  </entry>
</feed>
"""


def test_clean_text():
    raw = "<b>Headline</b>: World News &amp; Updates   \n"
    assert clean_text(raw) == "Headline : World News & Updates"
    assert clean_text(None) == ""
    assert clean_text("") == ""


def test_parse_date():
    dt_rfc = parse_date("Mon, 28 Nov 2026 09:30:00 +0700")
    assert dt_rfc is not None
    assert dt_rfc.year == 2026
    assert dt_rfc.month == 11
    assert dt_rfc.day == 28

    dt_iso = parse_date("2026-11-28T02:30:00Z")
    assert dt_iso is not None
    assert dt_iso.tzinfo == timezone.utc

    assert parse_date(None) is None
    assert parse_date("invalid-date-string") is None


def test_parse_feed_rss():
    articles = parse_feed_xml(SAMPLE_RSS_XML, feed_name="Sample Source", category="Business")
    assert len(articles) == 1
    art = articles[0]
    assert art["title"] == "Breaking News : Market Surges"
    assert art["link"] == "https://example.com/market-surge"
    assert "Stocks & commodities climbed" in art["description"]
    assert art["source"] == "Sample Source"
    assert art["category"] == "Business"


def test_parse_feed_atom():
    articles = parse_feed_xml(SAMPLE_ATOM_XML, feed_name="Atom Source", category="Tech")
    assert len(articles) == 1
    art = articles[0]
    assert art["title"] == "New AI Innovation Launched"
    assert art["link"] == "https://example.com/ai-innovation"
    assert "state-of-the-art" in art["description"]
    assert art["source"] == "Atom Source"
    assert art["category"] == "Tech"


def test_probe_feed_info():
    info_rss = probe_feed_info(SAMPLE_RSS_XML)
    assert info_rss["title"] == "Sample News Channel"

    info_atom = probe_feed_info(SAMPLE_ATOM_XML)
    assert info_atom["title"] == "Atom Tech Feed"
