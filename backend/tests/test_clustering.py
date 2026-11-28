from backend.app.services.clustering import (
    extract_keywords,
    clean_topic_title,
    cluster_articles,
)


def test_extract_keywords():
    text = "Presiden meresmikan jembatan baru di Jawa Barat dengan kementerian terkait."
    tokens = extract_keywords(text)
    # Stopwords like 'di', 'dengan', 'terkait', 'baru' should be filtered out
    assert "di" not in tokens
    assert "dengan" not in tokens
    assert "presiden" in tokens
    assert "meresmikan" in tokens
    assert "jembatan" in tokens


def test_clean_topic_title():
    raw1 = "Gempa Bumi Magnitudo 6.2 Guncang Jayapura – Ini Kata BMKG"
    cleaned1 = clean_topic_title(raw1)
    assert cleaned1 == "Gempa Bumi Magnitudo 6.2 Guncang Jayapura"

    raw2 = "RT by @news: #BreakingNews Operasi Tangkap Tangan KPK di Jakarta"
    cleaned2 = clean_topic_title(raw2)
    assert "Rt By" not in cleaned2
    assert "Breakingnews" not in cleaned2
    assert "Operasi Tangkap Tangan Kpk Di Jakarta" in cleaned2


def test_cluster_articles_grouping():
    articles = [
        {
            "title": "Banjir bandang menerjang wilayah Padang Pariaman Sumatera Barat",
            "link": "https://source1.com/banjir-padang",
            "description": "Banjir bandang bandang melanda pemukiman warga di Padang Pariaman akibat curah hujan tinggi.",
            "source": "Media Indonesia",
        },
        {
            "title": "Banjir Padang Pariaman rendam puluhan rumah warga",
            "link": "https://source2.com/banjir-padang",
            "description": "Bencana banjir di wilayah Padang Pariaman Sumatera Barat menyebabkan puluhan keluarga mengungsi.",
            "source": "Antara News",
        },
        {
            "title": "Harga emas Antam naik tipis hari ini",
            "link": "https://source3.com/emas-naik",
            "description": "Harga pecahan emas batangan Antam tercatat naik di angka Rp 1.500.000 per gram.",
            "source": "CNBC",
        },
    ]

    clusters = cluster_articles(articles)
    assert len(clusters) == 2

    # Cluster 1 should be the flood news because it's covered by 2 distinct sources
    top_cluster = clusters[0]
    assert len(top_cluster["sources"]) == 2
    assert len(top_cluster["articles"]) == 2
    assert "Media Indonesia" in top_cluster["sources"]
    assert "Antara News" in top_cluster["sources"]

    # Cluster 2 is gold price with 1 source
    second_cluster = clusters[1]
    assert len(second_cluster["sources"]) == 1
