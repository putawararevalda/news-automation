import tempfile
from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine, select

from backend.app.db.models import Feed, Digest
from backend.app.db.migration import seed_default_feeds, import_legacy_digests


def test_seed_and_legacy_import():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        digest1 = tmp_path / "digest-2026-11-20.md"
        digest1.write_text(
            "# 📰 Rangkuman 5 Berita Utama\n*2026-11-20*\n\n1️⃣ **Uji Coba Berita**\nIsi berita disini.",
            encoding="utf-8"
        )
        digest2 = tmp_path / "digest-2026-11-21.md"
        digest2.write_text(
            "# 📰 Rangkuman 5 Berita Utama\n*2026-11-21*\n\n1️⃣ **Uji Coba Berita 2**\nIsi berita kedua.",
            encoding="utf-8"
        )

        with Session(engine) as session:
            # 1. Seed feeds
            seeded = seed_default_feeds(session)
            assert seeded >= 0

            # 2. Import digests
            imported = import_legacy_digests(session, digests_dir=tmp_path)
            assert imported == 2

            # 3. Verify in DB
            digests = session.exec(select(Digest)).all()
            assert len(digests) == 2

            # 4. Re-run to verify idempotency
            re_seeded = seed_default_feeds(session)
            re_imported = import_legacy_digests(session, digests_dir=tmp_path)
            assert re_seeded == 0
            assert re_imported == 0
