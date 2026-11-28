import re
from typing import List, Dict, Any, Set

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
    "it", "its", "that", "this", "these", "those", "after", "before", "over", "under",
}


def extract_keywords(text: str) -> Set[str]:
    text = text.lower()
    words = re.findall(r"[a-zA-Z0-9_\-\u00C0-\u017F]{3,}", text)
    return {w for w in words if w not in STOPWORDS}


def clean_topic_title(title: str) -> str:
    # Remove hashtags and Twitter retweets
    clean = re.sub(r"RT by @\w+:\s*", "", title)
    clean = re.sub(r"#\w+\s*", "", clean)
    clean = re.sub(r"https?://\S+", "", clean)
    # Split on common separators
    for sep in ["–", "-", "—", ":", "|"]:
        if sep in clean:
            parts = clean.split(sep)
            if len(parts[0].strip().split()) >= 3:
                clean = parts[0]
                break
    clean = clean.strip().title()
    clean = re.sub(r"\s+", " ", clean)
    if len(clean) > 70:
        clean = clean[:67] + "..."
    return clean


def cluster_articles(articles: List[Dict[str, Any]], match_threshold: float = 0.35) -> List[Dict[str, Any]]:
    """
    Cluster articles with strict token matching against the primary story to prevent drift.
    Returns list of clusters sorted descending by unique news sources, then article count.
    """
    clusters: List[Dict[str, Any]] = []
    for art in articles:
        tokens = extract_keywords(art.get("title", "") + " " + art.get("description", "")[:200])
        best_cluster = None
        best_score = 0.0

        for c in clusters:
            c_tokens = c["primary_tokens"]
            intersection = tokens.intersection(c_tokens)
            if len(intersection) < 3:
                continue
            score = len(intersection) / max(len(tokens), len(c_tokens), 1)
            if score > best_score:
                best_score = score
                best_cluster = c

        if best_cluster and best_score >= match_threshold:
            best_cluster["articles"].append(art)
            best_cluster["sources"].add(art["source"])
        else:
            clusters.append({
                "articles": [art],
                "primary_tokens": set(tokens),
                "sources": {art["source"]},
            })

    # Sort clusters descending by number of distinct feeds talking about the issue, then by total article count
    clusters.sort(key=lambda c: (len(c["sources"]), len(c["articles"])), reverse=True)
    return clusters
