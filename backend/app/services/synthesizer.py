import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from backend.app.services.clustering import NUMBER_EMOJIS, clean_topic_title

try:
    import httpx
except ImportError:
    httpx = None


def generate_cluster_summary_llm(
    all_articles: List[Dict[str, Any]],
    api_key: str,
    model: str = "gemini-3.8-flash",
    timeout: int = 90
) -> str:
    """
    Call Gemini API to semantically cluster raw articles and generate top 5 summaries with strictly matching links.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Deduplicate articles by link and prepare concise payload
    unique_articles = []
    seen_links = set()
    for a in all_articles:
        link = a.get("link", "")
        if link not in seen_links:
            seen_links.add(link)
            unique_articles.append({
                "id": len(unique_articles) + 1,
                "title": a.get("title", ""),
                "source": a.get("source", ""),
                "link": link,
                "snippet": a.get("description", "")[:250],
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
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        parts = res["candidates"][0]["content"]["parts"]
        text_parts = [p["text"] for p in parts if "text" in p]
        return "\n".join(text_parts).strip()


def generate_cluster_summary_local(clusters: List[Dict[str, Any]], top_n: int = 5) -> str:
    """
    Pure Python synthesis for clustering when no external LLM API key is present or on API failure.
    """
    output_blocks = []

    for idx, c in enumerate(clusters[:top_n]):
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
            d = re.sub(r"https?://\S+", "", d)
            d = re.sub(r"#\w+\s*", "", d)
            d = re.sub(r"@\w+\s*", "", d)
            d = re.sub(r"\s+", " ", d).strip()
            if d and d not in desc_sentences and len(d) > 25:
                desc_sentences.append(d)

        raw_text = " ".join(desc_sentences[:3])
        if not raw_text or len(raw_text) < 50:
            raw_text = f"Isu ini dilaporkan oleh {source_count} sumber ({source_names}). " + " ".join([a["title"] for a in arts[:2]])

        # Keep writeup under 80 words and ensure it ends on a complete sentence
        sentences = re.split(r"(?<=[.!?])\s+", raw_text)
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
            f"{emoji} **{clean_topic}**\n"
            f"*(Diliput oleh {source_count} sumber: {source_names})*\n\n"
            f"{writeup}\n\n"
            f"Read more:\n" + "\n".join(best_links)
        )
        output_blocks.append(block)

    return "\n\n---\n\n".join(output_blocks)


def synthesize_news(
    all_articles: List[Dict[str, Any]],
    clusters: List[Dict[str, Any]],
    gemini_api_key: Optional[str] = None,
    preferred_model: str = "gemini-3.8-flash"
) -> Tuple[str, str, int, int]:
    """
    Synthesize clustered news articles using Gemini API if key is available,
    falling back to local NLP synthesis on failure or absence of key.
    Returns: (raw_summary_body, model_used, total_clusters, total_sources)
    """
    total_clusters = len(clusters)
    distinct_sources = set()
    for c in clusters:
        distinct_sources.update(c.get("sources", []))
    total_sources = len(distinct_sources)

    if gemini_api_key:
        try:
            summary = generate_cluster_summary_llm(all_articles, gemini_api_key, model=preferred_model)
            if summary and len(summary.strip()) > 50:
                return summary, preferred_model, total_clusters, total_sources
        except Exception as e:
            print(f"[WARN] Gemini API synthesis failed ({e}). Falling back to local NLP.", file=sys.stderr)

    # Fallback
    summary = generate_cluster_summary_local(clusters)
    return summary, "local-nlp", total_clusters, total_sources


def build_markdown_document(content: str, date_obj: Optional[datetime] = None) -> str:
    """Format full markdown document with header matching AGENTS.md format."""
    dt = date_obj or datetime.now()
    today_str = dt.strftime("%A, %d %B %Y")
    header = (
        f"# 📰 Rangkuman 5 Berita Utama\n"
        f"*{today_str}*\n\n"
        f"> Diurutkan berdasarkan jumlah media yang meliput isu tersebut.\n\n"
    )
    return header + content.strip() + "\n"
