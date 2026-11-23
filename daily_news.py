#!/usr/bin/env python3
"""
Daily News Aggregator & Synthesizer with Cross-Feed Ranking
Clusters news from multiple feeds by topic, ranks them by how many feeds cover the issue,
generates a ~100 word writeup per topic, selects the top 2 links, and broadcasts to Telegram.
Supports Gemini API for AI synthesis if 'gemini_api_key' is provided in config.json,
with an intelligent local NLP clusterer as fallback.
"""

import sys
import os
import json
import re
import html
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
ENV_PATH = os.path.join(SCRIPT_DIR, ".env")

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

STOPWORDS = {
    # Indonesian
    "dan", "yang", "di", "dari", "ke", "ini", "itu", "untuk", "pada", "adalah", "dengan",
    "oleh", "dalam", "akan", "juga", "bisa", "ada", "karena", "terkait", "tentang", "atas",
    "saat", "setelah", "hingga", "seperti", "bagi", "secara", "lebih", "telah", "kata", "ujar",
    "sebut", "menurut", "belum", "sudah", "tak", "tidak", "bukan", "hanya", "dapat", "ia",
    "dia", "mereka", "kita", "kami", "anda", "para", "banyak", "antara", "tersebut", "masih",
    "namun", "tetapi", "lagi", "baru", "satu", "dua", "tiga", "jadi", "hari", "kali", "resmi",
    # English
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "are", "were", "been", "be", "have", "has", "had",
    "it", "its", "that", "this", "these", "those", "after", "before", "over", "under"
}

def load_env_file(env_file):
    if not os.path.exists(env_file):
        return
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception as e:
        print(f"[WARN] Failed to load .env file: {e}", file=sys.stderr)

def load_config():
    # Load .env into os.environ if present
    load_env_file(ENV_PATH)

    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to read {CONFIG_PATH}: {e}", file=sys.stderr)
            config = {}

    # Environment variables override / fallback
    if os.environ.get("GEMINI_API_KEY"):
        config["gemini_api_key"] = os.environ.get("GEMINI_API_KEY")

    if os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_CHAT_ID"):
        tg = config.setdefault("telegram", {})
        if os.environ.get("TELEGRAM_BOT_TOKEN"):
            tg["bot_token"] = os.environ.get("TELEGRAM_BOT_TOKEN")
        if os.environ.get("TELEGRAM_CHAT_ID"):
            tg["chat_id"] = os.environ.get("TELEGRAM_CHAT_ID")

    if os.environ.get("OUTPUT_DIR"):
        config["output_dir"] = os.environ.get("OUTPUT_DIR")
    elif "output_dir" not in config:
        config["output_dir"] = os.path.join(SCRIPT_DIR, "digests")

    if os.environ.get("LATEST_SUMMARY_FILE"):
        config["latest_summary_file"] = os.environ.get("LATEST_SUMMARY_FILE")
    elif "latest_summary_file" not in config:
        config["latest_summary_file"] = os.path.join(SCRIPT_DIR, "daily-summary.md")

    # Resolve relative paths relative to SCRIPT_DIR
    if not os.path.isabs(config["output_dir"]):
        config["output_dir"] = os.path.normpath(os.path.join(SCRIPT_DIR, config["output_dir"]))
    if not os.path.isabs(config["latest_summary_file"]):
        config["latest_summary_file"] = os.path.normpath(os.path.join(SCRIPT_DIR, config["latest_summary_file"]))

    return config

def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            if fmt.endswith("Z") and date_str.endswith("Z"):
                dt = datetime.strptime(date_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    return None

def fetch_feed(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None

def parse_feed_xml(xml_bytes, feed_name, category):
    if not xml_bytes:
        return []
    entries = []
    try:
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        print(f"[WARN] XML parsing error for {feed_name}: {e}", file=sys.stderr)
        return []

    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

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
                    "category": category
                })
        return entries

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
                    "category": category
                })
    return entries

def extract_keywords(text):
    text = text.lower()
    words = re.findall(r'[a-zA-Z0-9_\-\u00C0-\u017F]{3,}', text)
    return {w for w in words if w not in STOPWORDS}

def cluster_articles(articles):
    """
    Cluster articles with strict token matching against the primary story to prevent drift.
    """
    clusters = []
    for art in articles:
        tokens = extract_keywords(art["title"] + " " + art.get("description", "")[:200])
        best_cluster = None
        best_score = 0.0

        for c in clusters:
            # Compare strictly against the primary article's tokens to avoid drift
            c_tokens = c["primary_tokens"]
            intersection = tokens.intersection(c_tokens)
            if len(intersection) < 3:
                continue
            score = len(intersection) / max(len(tokens), len(c_tokens), 1)
            if score > best_score:
                best_score = score
                best_cluster = c

        if best_cluster and best_score >= 0.35:
            best_cluster["articles"].append(art)
            best_cluster["sources"].add(art["source"])
        else:
            clusters.append({
                "articles": [art],
                "primary_tokens": set(tokens),
                "sources": {art["source"]}
            })

    # Sort clusters descending by number of distinct feeds talking about the issue,
    # then by total article count
    clusters.sort(key=lambda c: (len(c["sources"]), len(c["articles"])), reverse=True)
    return clusters

def generate_cluster_summary_llm(all_articles, api_key):
    """
    Call Gemini API to semantically cluster raw articles and generate top 5 summaries with strictly matching links.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    
    # Deduplicate articles by link and prepare concise payload
    unique_articles = []
    seen_links = set()
    for a in all_articles:
        if a["link"] not in seen_links:
            seen_links.add(a["link"])
            unique_articles.append({
                "id": len(unique_articles) + 1,
                "title": a["title"],
                "source": a["source"],
                "link": a["link"],
                "snippet": a.get("description", "")[:250]
            })

    prompt_text = (
        "You are an expert news editor compiling a daily morning briefing in Indonesian.\n"
        "Below is a list of recent news articles from multiple media outlets from the last 24 hours.\n\n"
        "TASK:\n"
        "1. Identify distinct, specific news events. Two articles belong to the same event ONLY if they describe the EXACT SAME specific incident or occurrence.\n"
        "   - STRICT RULE: Never group different events together just because they share a person, government agency (e.g. KKP, Polri, KPK), or broad theme (e.g. sports, climate).\n"
        "2. Rank the events by the number of DISTINCT news outlets reporting on that specific event (stories covered by multiple different outlets come first).\n"
        "3. Pick the TOP 5 events.\n"
        "4. For each event, write a straightforward, factual write-up (50 to 80 words, strictly 100 words or less) explaining what happened in clear Indonesian.\n"
        "5. Under 'Read more:', attach ONLY the links that DIRECTLY report on THAT SPECIFIC event (max 2 links, prioritizing two different sources if available).\n"
        "   - ABSOLUTE INTEGRITY RULE: Every attached link MUST be strictly about the event summarized. Never attach a link from an unrelated story!\n"
        "   - If only 1 source covered the event, provide only 1 link.\n"
        "6. FORMAT FOR EACH TOPIC:\n\n"
        "<Number Emoji> **Topic Title in Title Case**\n"
        "<Straightforward 50-80 word factual write-up with complete sentences ending in a period>\n"
        "Read more:\n"
        "• [Headline 1 — Source 1](url1)\n"
        "• [Headline 2 — Source 2](url2)\n\n"
        "Output only the 5 topics separated by a horizontal divider (---). Do not add any conversational preamble or sign-off.\n\n"
        "Articles:\n" + json.dumps(unique_articles, ensure_ascii=False)
    )

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.2,
            "thinkingConfig": {"thinkingBudget": 0}
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        parts = res["candidates"][0]["content"]["parts"]
        text_parts = [p["text"] for p in parts if "text" in p]
        return "\n".join(text_parts).strip()

def clean_topic_title(title):
    # Remove hashtags and Twitter retweets
    clean = re.sub(r'^(RT by @\w+:|#\w+)\s*', '', title)
    clean = re.sub(r'https?://\S+', '', clean)
    # Split on common separators
    for sep in ["–", "-", "—", ":", "|"]:
        if sep in clean:
            parts = clean.split(sep)
            if len(parts[0].strip().split()) >= 3:
                clean = parts[0]
                break
    clean = clean.strip().title()
    clean = re.sub(r'\s+', ' ', clean)
    if len(clean) > 70:
        clean = clean[:67] + "..."
    return clean

def generate_cluster_summary_local(clusters):
    """
    Pure Python synthesis for clustering when no external LLM API key is present.
    """
    output_blocks = []

    for idx, c in enumerate(clusters[:5]):
        emoji = NUMBER_EMOJIS[idx] if idx < len(NUMBER_EMOJIS) else f"{idx+1}."
        arts = c["articles"]
        
        # Pick best representative title for topic header
        best_title = max(arts, key=lambda a: len(a["title"]))["title"]
        clean_topic = clean_topic_title(best_title)

        source_count = len(c["sources"])
        source_names = ", ".join(sorted(c["sources"]))

        # Synthesize writeup from descriptions
        desc_sentences = []
        for a in arts:
            d = a.get("description", "")
            d = re.sub(r'https?://\S+', '', d)
            d = re.sub(r'#\w+\s*', '', d)
            d = re.sub(r'@\w+\s*', '', d)
            d = re.sub(r'\s+', ' ', d).strip()
            if d and d not in desc_sentences and len(d) > 25:
                desc_sentences.append(d)

        raw_text = " ".join(desc_sentences[:3])
        if not raw_text or len(raw_text) < 50:
            raw_text = f"Isu ini dilaporkan oleh {source_count} sumber ({source_names}). " + " ".join([a['title'] for a in arts[:2]])
        
        # Keep writeup under 80 words and ensure it ends on a complete sentence
        sentences = re.split(r'(?<=[.!?])\s+', raw_text)
        kept_sentences = []
        word_count = 0
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            w_len = len(s.split())
            if word_count + w_len <= 85 or not kept_sentences:
                kept_sentences.append(s)
                word_count += w_len
            else:
                break
        
        writeup = " ".join(kept_sentences)
        if not writeup.endswith((".", "!", "?")):
            writeup += "."

        # Best 2 links (prefer different news sources)
        best_links = []
        seen_urls = set()
        seen_sources = set()

        for a in arts:
            if a["link"] not in seen_urls and a["source"] not in seen_sources:
                best_links.append(f"• [{a['title']} — {a['source']}]({a['link']})")
                seen_urls.add(a["link"])
                seen_sources.add(a["source"])
                if len(best_links) >= 2:
                    break

        if len(best_links) < 2:
            for a in arts:
                if a["link"] not in seen_urls:
                    best_links.append(f"• [{a['title']} — {a['source']}]({a['link']})")
                    seen_urls.add(a["link"])
                    if len(best_links) >= 2:
                        break

        block = (
            f"{emoji} <b>{clean_topic}</b>\n"
            f"<i>(Diliput oleh {source_count} sumber: {source_names})</i>\n\n"
            f"{writeup}\n\n"
            f"<b>Read more:</b>\n" + "\n".join(best_links)
        )
        output_blocks.append(block)

    return "\n\n━━━━━━━━━━━━━━━━━━━━\n\n".join(output_blocks)

def send_telegram_message(token, chat_id, text_html):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def split_message_chunks(text, max_len=4000):
    lines = text.split("\n")
    chunks = []
    current_chunk = []
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

def main():
    dry_run = "--dry-run" in sys.argv or "--test" in sys.argv
    config = load_config()

    feeds = config.get("feeds", [])
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    all_articles = []
    print(f"[{datetime.now().isoformat()}] Fetching news from {len(feeds)} sources...")

    for feed_info in feeds:
        name = feed_info.get("name", "News")
        category = feed_info.get("category", "General")
        url = feed_info.get("url")
        print(f" - {name}...")
        xml_bytes = fetch_feed(url)
        entries = parse_feed_xml(xml_bytes, name, category)

        # Filter 24h
        recent = [e for e in entries if e["pub_date"] and e["pub_date"] >= cutoff]
        if not recent:
            recent = entries[:5]
        else:
            recent = recent[:6]
        all_articles.extend(recent)

    print(f"Total articles retrieved: {len(all_articles)}. Clustering by topic...")
    clusters = cluster_articles(all_articles)
    print(f"Formed {len(clusters)} distinct topic clusters.")

    gemini_key = config.get("gemini_api_key")
    if gemini_key:
        print("Using Gemini API for human-readable synthesis...")
        try:
            content = generate_cluster_summary_llm(all_articles, gemini_key)
        except Exception as e:
            print(f"[WARN] Gemini API synthesis failed ({e}). Falling back to local synthesizer.", file=sys.stderr)
            clusters = cluster_articles(all_articles)
            content = generate_cluster_summary_local(clusters)
    else:
        print("Using local ranking synthesizer (order by feed count)...")
        clusters = cluster_articles(all_articles)
        content = generate_cluster_summary_local(clusters)

    today_str = datetime.now().strftime("%A, %d %B %Y")
    
    # Telegram formatted message (HTML)
    tg_header = (
        f"📰 <b>RANGKUMAN 5 BERITA UTAMA</b>\n"
        f"📅 <i>{today_str}</i>\n"
        f"<i>Diurutkan berdasarkan isu yang paling banyak diliput media hari ini:</i>\n\n"
    )
    
    # Markdown formatted file
    md_header = (
        f"# 📰 Rangkuman 5 Berita Utama\n"
        f"*{today_str}*\n\n"
        f"> Diurutkan berdasarkan jumlah media yang meliput isu tersebut.\n\n"
    )

    # Convert markdown from Gemini/local synthesizer to Telegram HTML
    tg_body = content
    # Convert bold **text** to <b>text</b>
    tg_body = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', tg_body)
    # Replace markdown links [Title](url) with <a href="url">Title</a>
    tg_body = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', tg_body)
    # Replace dividers with clean separator
    tg_body = re.sub(r'\n---+\n', r'\n\n━━━━━━━━━━━━━━━━━━━━\n\n', tg_body)
    # Remove any markdown header hashes
    tg_body = re.sub(r'#+\s*', r'', tg_body)

    full_tg = tg_header + tg_body
    full_md = md_header + content

    # Save to Markdown files
    out_dir = config.get("output_dir", os.path.join(SCRIPT_DIR, "digests"))
    os.makedirs(out_dir, exist_ok=True)
    date_file = os.path.join(out_dir, f"digest-{datetime.now().strftime('%Y-%m-%d')}.md")
    latest_file = config.get("latest_summary_file", os.path.join(SCRIPT_DIR, "daily-summary.md"))

    with open(date_file, "w", encoding="utf-8") as f:
        f.write(full_md)
    with open(latest_file, "w", encoding="utf-8") as f:
        f.write(full_md)

    print(f"Saved digest to {latest_file}")

    if dry_run:
        print("[DRY RUN] Skipping Telegram send.")
        return

    tg_conf = config.get("telegram", {})
    bot_token = tg_conf.get("bot_token")
    chat_id = tg_conf.get("chat_id")

    if bot_token and chat_id:
        print(f"Sending formatted digest to Telegram...")
        chunks = split_message_chunks(full_tg)
        for i, chunk in enumerate(chunks):
            try:
                send_telegram_message(bot_token, chat_id, chunk)
                print(f"Delivered chunk {i+1}/{len(chunks)}")
            except Exception as e:
                print(f"[ERROR] Failed to send Telegram chunk {i+1}: {e}", file=sys.stderr)
        print("Telegram broadcast complete!")

if __name__ == "__main__":
    main()
