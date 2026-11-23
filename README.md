# 📰 News Automation

> **Daily News Aggregator & AI-Powered Synthesizer with Cross-Feed Ranking**  
> Otomasi agregasi berita harian multi-sumber via RSS feeds, klusterisasi topik berbasis kata kunci, pemeringkatan lintas media (*cross-feed ranking*), sintesis ringkasan berita menggunakan Google Gemini API (dengan fallback cerdas ke NLP lokal), pembuatan arsip berkas digest harian (Markdown), serta siaran berkala ke Telegram.

---

## 📑 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Arsitektur & Alur Kerja](#-arsitektur--alur-kerja)
- [Prasyarat & Lingkungan Runtime](#-prasyarat--lingkungan-runtime)
- [Panduan Konfigurasi](#-panduan-konfigurasi)
  - [1. Konfigurasi melalui `.env`](#1-konfigurasi-melalui-env-disarankan)
  - [2. Konfigurasi melalui `config.json`](#2-konfigurasi-melalui-configjson)
- [Cara Menjalankan](#-cara-menjalankan)
  - [Eksekusi Manual](#eksekusi-manual)
  - [Dry-Run / Mode Pengujian](#dry-run--mode-pengujian)
  - [Menjalankan via Shell Script](#menjalankan-via-shell-script)
- [Otomasi Terjadwal](#-otomasi-terjadwal)
  - [macOS (launchd)](#1-macos-launchd)
  - [Linux / Unix (Cron)](#2-linux--unix-cron)
  - [Windows (Task Scheduler)](#3-windows-task-scheduler)
- [Struktur Direktori](#-struktur-direktori)
- [Keamanan & Praktik Terbaik](#-keamanan--praktik-terbaik)

---

## 🌟 Fitur Utama

1. **Multi-Source RSS Aggregation**: Mengumpulkan artikel dari berbagai sumber media kredibel (Antara, Tempo, BBC, CNN Indonesia, dll.) dalam rentang waktu 24 jam terakhir.
2. **Topic Clustering & Cross-Feed Ranking**: Mengelompokkan artikel ke dalam kluster isu spesifik menggunakan algoritma token matching ketat (*strict token overlap*) dan memeringkat topik berdasarkan jumlah media independen yang meliput isu tersebut.
3. **AI Synthesis (Gemini 3.8 Flash)**: Menghasilkan ringkasan berita 50–80 kata yang padat dan faktual dalam Bahasa Indonesia serta memilih 2 tautan rujukan utama.
4. **Resilient Local NLP Fallback**: Jika koneksi atau API key Gemini bermasalah/kuota habis, sistem secara otomatis beralih ke sintesis NLP lokal berbasis heuristik ekstraksi kalimat tanpa menghentikan proses.
5. **Multi-Channel Publishing**:
   - Menyimpan arsip harian berformat Markdown di `digests/digest-YYYY-MM-DD.md`.
   - Memperbarui berkas ringkasan terkini `daily-summary.md`.
   - Menyiarkan ringkasan berita berformat HTML ke channel/grup Telegram via Telegram Bot API dengan pembagian pesan otomatis (*chunking*) jika melebihi batas karakter.

---

## 🏗 Arsitektur & Alur Kerja

```
[RSS Feeds (Antara, BBC, Tempo, CNN, dll.)]
                    │
                    ▼
       [Fetch & Parse XML / Atom]
                    │
                    ▼
          [Filter Berita (24 Jam)]
                    │
                    ▼
     [Clustering & Cross-Feed Ranking]
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
  [Gemini API Synthesis]    [Local NLP Fallback]
         └──────────┬──────────┘
                    │
                    ▼
    [Format Output: Markdown & HTML]
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
[Simpan ke digests/ & daily-summary.md]   [Siaran ke Telegram Channel]
```

---

## 💻 Prasyarat & Lingkungan Runtime

- **Python 3.8+** (Direkomendasikan Python 3.10 atau lebih baru).
- **Zero External Dependencies**: Menggunakan pustaka bawaan (*Python Standard Library*) seperti `urllib`, `xml.etree.ElementTree`, `re`, `html`, `json`, `datetime`, dan `collections`. Tidak memerlukan instalasi paket tambahan melalui `pip`.

---

## ⚙️ Panduan Konfigurasi

Sistem mendukung konfigurasi fleksibel melalui file lingkungan `.env` maupun berkas JSON `config.json`. Parameter pada `.env` atau variabel lingkungan sistem akan diutamakan (*precedence*).

### 1. Konfigurasi melalui `.env` (Disarankan)

Salin template `.env.example` menjadi `.env`:

```bash
cp .env.example .env
```

Isi parameter konfigurasi sesuai kebutuhan:

```env
# Token bot Telegram dari @BotFather
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# ID chat, group, atau channel tujuan (contoh: @channel_kamu atau -1001234567890)
TELEGRAM_CHAT_ID=-1001234567890

# API key Google Gemini dari Google AI Studio (opsional, jika kosong fallback ke local NLP)
GEMINI_API_KEY=AIzaSyD-contoh_api_key_kamu

# Path folder penyimpanan arsip digest (default: ./digests)
OUTPUT_DIR=./digests

# Path berkas ringkasan terkini (default: ./daily-summary.md)
LATEST_SUMMARY_FILE=./daily-summary.md
```

### 2. Konfigurasi melalui `config.json`

Daftar RSS feed dan konfigurasi alternatif dapat dikelola pada `config.json`:

```json
{
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "YOUR_TELEGRAM_CHAT_ID"
  },
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "feeds": [
    {
      "name": "Antara News Terkini",
      "category": "Indonesia / Nasional",
      "url": "https://www.antaranews.com/rss/terkini.xml"
    },
    {
      "name": "Tempo Nasional",
      "category": "Indonesia / Nasional",
      "url": "http://rss.tempo.co/nasional"
    },
    {
      "name": "BBC Indonesia",
      "category": "Indonesia / Nasional",
      "url": "https://feeds.bbci.co.uk/indonesia/rss.xml"
    },
    {
      "name": "CNN Indonesia Nasional",
      "category": "Indonesia / Nasional",
      "url": "https://www.cnnindonesia.com/nasional/rss"
    }
  ],
  "output_dir": "./digests",
  "latest_summary_file": "./daily-summary.md"
}
```

---

## 🚀 Cara Menjalankan

### Eksekusi Manual

Jalankan script menggunakan runtime Python:

```bash
python daily_news.py
```

### Dry-Run / Mode Pengujian

Untuk menguji agregasi, clustering, dan pembuatan digest Markdown tanpa mengirim pesan siaran ke Telegram, gunakan flag `--dry-run` atau `--test`:

```bash
python daily_news.py --test
# atau
python daily_news.py --dry-run
```

### Menjalankan via Shell Script

Tersedia file `run.sh` untuk otomasi di sistem berbasis Unix / macOS / Linux:

```bash
chmod +x run.sh
./run.sh
```

---

## ⏰ Otomasi Terjadwal

### 1. macOS (`launchd`)

Proyek ini telah menyertakan berkas konfigurasi `com.alline.dailynews.plist` yang dijadwalkan berjalan otomatis setiap pukul 06:00 pagi:

1. Sesuaikan path pada `com.alline.dailynews.plist` agar mengarah ke direktori proyek Anda.
2. Salin plist ke `~/Library/LaunchAgents/`:
   ```bash
   cp com.alline.dailynews.plist ~/Library/LaunchAgents/
   ```
3. Aktifkan service launchd:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.alline.dailynews.plist
   ```

### 2. Linux / Unix (`Cron`)

Tambahkan entri crontab untuk menjalankan skrip setiap hari pukul 06:00 pagi:

```bash
crontab -e
```

Tambahkan baris berikut:

```cron
0 6 * * * cd /path/to/news-automation && ./run.sh >> automation.log 2>> automation.err.log
```

### 3. Windows (Task Scheduler)

1. Buka **Task Scheduler** di Windows (`taskschd.msc`).
2. Buat tugas baru (*Create Basic Task*), beri nama `Daily News Automation`.
3. Pilih pemicu (*Trigger*): **Daily** pada jam yang diinginkan (misal `06:00`).
4. Pilih aksi (*Action*): **Start a program**.
   - **Program/script**: `python` (atau path lengkap `C:\Users\<User>\.local\bin\python3.12.exe`).
   - **Add arguments**: `daily_news.py`
   - **Start in**: `E:\Portfolios\news-automation`
5. Simpan tugas.

---

## 📁 Struktur Direktori

```text
news-automation/
├── .env.example             # Template konfigurasi environment variable
├── .gitignore               # Daftar proteksi berkas credential, log, dan artefak
├── AGENTS.md                # Panduan arsitektur & instruksi untuk coding agent
├── README.md                # Dokumentasi utama proyek
├── daily_news.py            # Skrip inti agregasi, sintesis, dan siaran berita
├── config.json              # Berkas konfigurasi feed RSS dan kredensial lokal
├── run.sh                   # Runner script shell untuk eksekusi terjadwal
├── com.alline.dailynews.plist # Konfigurasi jadwal launchd macOS
├── daily-summary.md         # Berkas ringkasan berita harian terkini
├── automation.log           # Log standar output eksekusi terjadwal
├── automation.err.log       # Log pesan peringatan / error eksekusi terjadwal
└── digests/                 # Folder arsip ringkasan harian (Markdown)
    └── digest-YYYY-MM-DD.md
```

---

## 🔒 Keamanan & Praktik Terbaik

- **Jangan Pernah Mengunggah Kredensial**: File `.env` dan `config.json` riil sudah masuk ke dalam `.gitignore`. Jangan pernah memasukkan API key Gemini atau Bot Token Telegram ke dalam commit repositori git.
- **Validasi Feed URL**: Jika ada feed RSS yang memberikan respons HTTP 400/402/404 atau SSL error, script akan mencatat log peringatan dan tetap melanjutkan pemrosesan feed lainnya tanpa crash.
- **Graceful Fallback**: Desain skrip mengutamakan keandalan tinggi; ketiadaan API key eksternal tidak akan menghentikan pembuatan digest harian berkat algoritma klusterisasi lokal.
