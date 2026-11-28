from datetime import datetime
from backend.app.services.broadcaster import (
    markdown_to_telegram_html,
    split_message_chunks,
)


def test_markdown_to_telegram_html():
    raw_md = (
        "1️⃣ **Operasi SAR Evakuasi Korban Longsor**\n"
        "*(Diliput oleh 2 sumber: Kompas, Tempo)*\n\n"
        "Tim SAR gabungan terus berupaya mengevakuasi korban bencana tanah longsor.\n\n"
        "Read more:\n"
        "• [Judul Artikel 1 — Kompas](https://kompas.com/art1)\n"
        "• [Judul Artikel 2 — Tempo](https://tempo.co/art2)\n\n"
        "---\n\n"
        "2️⃣ **Harga Beras Stabil**\n"
        "Pemerintah memastikan pasokan pangan nasional terkendali.\n"
    )

    html_out = markdown_to_telegram_html(raw_md, datetime(2026, 11, 28))
    assert "📰 <b>RANGKUMAN 5 BERITA UTAMA</b>" in html_out
    assert "<b>Operasi SAR Evakuasi Korban Longsor</b>" in html_out
    assert "<i>(Diliput oleh 2 sumber: Kompas, Tempo)</i>" in html_out
    assert '<a href="https://kompas.com/art1">Judul Artikel 1 — Kompas</a>' in html_out
    assert '<a href="https://tempo.co/art2">Judul Artikel 2 — Tempo</a>' in html_out
    assert "━━━━━━━━━━━━━━━━━━━━" in html_out


def test_split_message_chunks():
    line = "Paragraph text line.\n"
    long_text = line * 300  # ~6300 chars
    chunks = split_message_chunks(long_text, max_len=2000)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(c) <= 2000
