# 📄 Product Requirement Document (PRD)
## Project: News Automation Operations & Analytics Dashboard

- **Author**: Senior Product Manager
- **Stakeholder**: Revalda Putawara (@putawararevalda)
- **Target Project**: `news-automation` (Project ID: `6dd2439c-d52d-4036-b9f6-282b3a9265e1`)
- **Status**: Draft / Approved for Implementation Planning
- **Date**: 2026-11-28
- **Target Deployment**: Docker Compose / CasaOS (Port `58619`)

---

## 1. Executive Summary & Objective

`news-automation` saat ini berfungsi sebagai skrip agregasi RSS harian berbasis terminal/daemon yang memproses berita 24 jam, melakukan klusterisasi berbasis token matching, sintesis ringkasan dengan Google Gemini API, penyimpanan arsip markdown, dan siaran pesan otomatis ke Telegram.

**Tujuan PRD ini** adalah merevamp arsitektur skrip monolitik CLI menjadi **Web Operations & Analytics Dashboard** modern berbasis kontainer. Pengguna dapat memantau kesehatan feed secara visual, melakukan kurasi dan uji coba feed RSS langsung dari UI, memicu pemrosesan on-demand dengan feedback streaming real-time, mengedit draf ringkasan berita, serta mengatur siaran Telegram tanpa perlu mengedit file konfigurasi atau terminal.

---

## 2. User Persona & Problem Statement

### Persona: Independent Researcher & Information Curator (Revalda)
- Mengonsumsi dan menyebarkan ringkasan berita terkurasi lintas media setiap hari ke grup/channel Telegram.
- Mengelola server mandiri berbasis CasaOS/Docker di jaringan lokal.

### Pain Points
1. **Zero Visibility**: Sulit mengetahui artikel apa saja yang gagal di-fetch atau feed mana yang sedang error/down tanpa membaca file log mentah.
2. **Ketiadaan Human-in-the-Loop**: Seluruh siaran langsung terkirim otomatis ke Telegram; tidak ada kesempatan memeriksa atau memperbaiki draf hasil sintesis AI sebelum dipublikasikan jika diperlukan.
3. **Rigid Configuration**: Menambah feed RSS baru mengharuskan akses terminal dan edit manual berkas `config.json` dengan risiko kesalahan format.
4. **Limited Presentation**: `news-server` saat ini hanya mengandalkan `python -m http.server` bawaan untuk merender direktori file mentah.

---

## 3. High-Level Architecture & Container Topology

Sistem dibagi menjadi arsitektur multi-container yang diikat melalui satu network bridge internal:

```
                      Client / CasaOS Browser
                                │
                                ▼ Port 58619
                ┌───────────────────────────────┐
                │   Frontend Service            │
                │   (Next.js Standalone / Nginx)│
                └───────────────┬───────────────┘
                                │ /api/* (Internal Proxy)
                                ▼
                ┌───────────────────────────────┐
                │   Backend API & Worker        │
                │   (FastAPI + APScheduler)     │
                └───────────────┬───────────────┘
                                │
            ┌───────────────────┴───────────────────┐
            ▼                                       ▼
 ┌─────────────────────┐                 ┌─────────────────────┐
 │ SQLite Database     │                 │ Shared File Volumes │
 │ - feeds, articles   │                 │ - ./digests/*.md    │
 │ - digests, runs     │                 │ - ./daily-summary.md│
 └─────────────────────┘                 └─────────────────────┘
```

- **Single Entry Point**: Seluruh antarmuka web dan API diakses melalui port non-standar **`58619`**.
- **Data Persistence**:
  - `news.db` (SQLite) tersimpan di volume `./data/news.db`.
  - Berkas markdown digest tetap disimpan di `./digests/digest-YYYY-MM-DD.md` dan `./daily-summary.md` untuk menjaga backward compatibility dengan tools eksternal.

---

## 4. Key Features & Functional Requirements

### 4.1. Dashboard Overview & KPI Metrics
- **FR-01**: Menampilkan metrik ringkas: Total Feeds Aktif, Jumlah Berita Hari Ini, Total Arsip Digest, dan Status Job Terakhir (Success/Failure).
- **FR-02**: Widget "Today's Briefing" yang menampilkan hasil digest aktif terkini langsung dari database/markdown.
- **FR-03**: Quick Action Bar: Tombol *"Run Ingestion Now"* dan *"Broadcast to Telegram"*.

### 4.2. Feed Management & Live URL Tester (Mandatory)
- **FR-04**: Tabel daftar feed RSS yang memuat nama media, URL, kategori, status aktif, dan timestamp fetch terakhir.
- **FR-05**: Form Tambah/Ubah Feed RSS dengan validasi schema URL.
- **FR-06 (Live Feed Tester)**: Fitur pengujian instan sebelum menyimpan feed baru. Sistem melakukan probe fetch ke URL RSS dan menampilkan cuplikan 3 artikel terbaru untuk memastikan feed valid dan aktif.
- **FR-07**: Toggle aktif/non-aktifkan feed tanpa menghapus data historis.

### 4.3. Pipeline Orchestration & Dual-Mode Execution
- **FR-08 (Automated Schedule)**: APScheduler internal berjalan setiap pukul 06:00 pagi (dapat diubah via setting/env `CRON_SCHEDULE`). Pada mode terjadwal, pipeline mengeksekusi fetch -> cluster -> Gemini synthesis -> simpan digest -> siarkan otomatis ke Telegram.
- **FR-09 (On-Demand Manual Trigger)**: Pengguna dapat memicu pipeline kapan saja lewat tombol dashboard (dengan opsi Full Run atau Dry-Run). Hasil manual masuk ke status `draft`.
- **FR-10 (Live Progress SSE Streaming)**: Menampilkan live progress bar dan log per tahap secara real-time via Server-Sent Events (SSE) saat pipeline sedang berjalan (`Fetching -> Clustering -> Synthesizing -> Storing`).

### 4.4. Digest Explorer & Draft Editor
- **FR-11**: Halaman arsip digest dengan kalender/daftar tanggal dan paginasi.
- **FR-12**: Markdown & HTML Viewer untuk setiap digest historis.
- **FR-13 (Draft Editor)**: Kemampuan menyunting teks ringkasan digest draf sebelum memicu siaran manual ke Telegram.
- **FR-14**: Tombol *"Send to Telegram"* manual dengan indikator status terkirim dan riwayat broadcast timestamp.

### 4.5. Legacy Data Migration
- **FR-15**: Pada saat backend startup pertama kali, sistem otomatis memindai folder `./digests` dan mengimpor file markdown yang ada ke dalam tabel `digests` SQLite sebagai data historis.

---

## 5. Non-Functional Requirements

1. **Performance**: Respon API rata-rata < 150ms untuk endpoint metadata dan digest; RSS crawler menggunakan asynchronous HTTP requests (`httpx` / `aiohttp`) agar tidak blocking.
2. **Resilience**: Jika Gemini API kehabisan kuota atau bermasalah, pipeline secara otomatis fallback ke algoritma sintesis NLP lokal tanpa memutus proses eksekusi.
3. **Portability**: Dapat dijalankan di lingkungan Linux/Unix, macOS, dan Windows via Docker Compose tanpa dependensi host machine.
4. **Security**: Kredensial sensitif (`GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) tetap disimpan via `.env` atau environment variable kontainer, tidak pernah di-hardcode ke UI client atau git commit.

---

## 6. Data Model Specification (SQLite)

- **`feeds`**: `id`, `name`, `url`, `category`, `is_active`, `last_status`, `last_fetched_at`, `created_at`.
- **`articles`**: `id`, `feed_id`, `title`, `url`, `snippet`, `published_at`, `created_at`.
- **`digests`**: `id`, `date` (YYYY-MM-DD), `summary_markdown`, `summary_html`, `model_used`, `total_clusters`, `total_sources`, `status` (`draft` | `published` | `broadcasted`), `broadcasted_at`, `created_at`.
- **`pipeline_runs`**: `id` (UUID), `trigger_type` (`scheduled` | `manual`), `status` (`running` | `completed` | `failed`), `logs` (JSON), `started_at`, `completed_at`.

---

## 7. Phased Implementation Roadmap

- **Phase 1: Backend Domain Refactoring & Data Engine**
  - Modularisasi skrip `daily_news.py` menjadi modul `services/` (crawling, clustering, synthesis).
  - Setup FastAPI, SQLModel/SQLite database engine, dan script auto-sync arsip lama.
  - Endpoint CRUD feed, Live RSS Tester, dan SSE streaming pipeline.
- **Phase 2: Frontend Dashboard Development**
  - Setup Next.js + Tailwind CSS + shadcn/ui.
  - Implementasi halaman: Overview/Metrics, Feed Management (dengan modal Tester), dan Digest Explorer & Editor.
  - Komponen SSE progress tracker dialog saat pipeline dijalankan.
- **Phase 3: Containerization & Deployment Verification**
  - Pembuatan Dockerfile backend & frontend.
  - Setup docker-compose multi-service dengan reverse proxy terintegrasi ke port 58619.
  - Uji coba end-to-end pada server lokal/CasaOS.
