from datetime import datetime
from backend.app.services.clustering import cluster_articles
from backend.app.services.synthesizer import (
    generate_cluster_summary_local,
    synthesize_news,
    build_markdown_document,
)


def test_generate_cluster_summary_local():
    articles = [
        {
            "title": "KPK Sita Aset Senilai Rp 20 Miliar Terkait Kasus Korupsi",
            "link": "https://media1.com/kpk-aset",
            "description": "Komisi Pemberantasan Korupsi menyita aset berupa tanah dan bangunan senilai Rp 20 miliar dalam penyidikan kasus korupsi proyek infrastruktur.",
            "source": "Tempo",
        },
        {
            "title": "Aset Rp 20 Miliar Disita KPK dalam Perkara Korupsi",
            "link": "https://media2.com/kpk-sita",
            "description": "Penyidik KPK melakukan penyitaan aset milik tersangka korupsi infrastruktur senilai puluhan miliar rupiah.",
            "source": "Kompas",
        },
    ]

    clusters = cluster_articles(articles)
    summary = generate_cluster_summary_local(clusters)

    assert "1️⃣" in summary
    assert "Read more:" in summary
    assert "https://media1.com/kpk-aset" in summary
    assert "https://media2.com/kpk-sita" in summary


def test_synthesize_news_fallback():
    articles = [
        {
            "title": "Pertumbuhan Ekonomi Indonesia Capai 5.05 Persen",
            "link": "https://media.com/ekonomi",
            "description": "BPS mencatat pertumbuhan ekonomi Indonesia kuartal ini tumbuh sebesar 5.05 persen didorong konsumsi domestik.",
            "source": "Bisnis",
        }
    ]
    clusters = cluster_articles(articles)

    # When key is None, it should seamlessly fallback to local-nlp
    summary, model_used, total_clusters, total_sources = synthesize_news(
        all_articles=articles,
        clusters=clusters,
        gemini_api_key=None,
    )

    assert model_used == "local-nlp"
    assert total_clusters == 1
    assert total_sources == 1
    assert "Bisnis" in summary


def test_build_markdown_document():
    content = "1️⃣ **Judul Berita**\nUlasan berita terkini."
    doc = build_markdown_document(content, datetime(2026, 11, 28))
    assert "# 📰 Rangkuman 5 Berita Utama" in doc
    assert "Saturday, 28 November 2026" in doc
    assert "1️⃣ **Judul Berita**" in doc
