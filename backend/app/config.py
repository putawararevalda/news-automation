import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Base directories
BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config.json"
DEFAULT_ENV_PATH = BASE_DIR / ".env"
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_DIGESTS_DIR = BASE_DIR / "digests"
DEFAULT_LATEST_SUMMARY = BASE_DIR / "daily-summary.md"


def load_env_file(env_file: Optional[Path] = None) -> None:
    path = env_file or DEFAULT_ENV_PATH
    if not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
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
        print(f"[WARN] Failed to load .env file from {path}: {e}", file=sys.stderr)


class Settings:
    def __init__(self, config_file: Optional[Path] = None, env_file: Optional[Path] = None):
        load_env_file(env_file)
        self.config_path = config_file or DEFAULT_CONFIG_PATH
        self.raw_config: Dict[str, Any] = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.raw_config = json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to read {self.config_path}: {e}", file=sys.stderr)

        # Database settings
        db_dir = os.environ.get("DATA_DIR", str(DEFAULT_DATA_DIR))
        self.data_dir = Path(db_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        default_db_file = self.data_dir / "news.db"
        self.database_url = os.environ.get("DATABASE_URL", f"sqlite:///{default_db_file}")

        # Gemini settings
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or self.raw_config.get("gemini_api_key")

        # Telegram settings
        tg_conf = self.raw_config.get("telegram", {})
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or tg_conf.get("bot_token")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID") or tg_conf.get("chat_id")

        # Output paths
        output_dir = os.environ.get("OUTPUT_DIR") or self.raw_config.get("output_dir", str(DEFAULT_DIGESTS_DIR))
        self.output_dir = Path(output_dir) if os.path.isabs(output_dir) else (BASE_DIR / output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        latest_file = os.environ.get("LATEST_SUMMARY_FILE") or self.raw_config.get("latest_summary_file", str(DEFAULT_LATEST_SUMMARY))
        self.latest_summary_file = Path(latest_file) if os.path.isabs(latest_file) else (BASE_DIR / latest_file).resolve()

        # Feeds config
        self.default_feeds: List[Dict[str, str]] = self.raw_config.get("feeds", [])

        # Cron schedule
        self.cron_schedule = os.environ.get("CRON_SCHEDULE", "0 6 * * *")


settings = Settings()
