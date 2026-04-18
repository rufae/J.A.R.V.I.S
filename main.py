from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

from jarvis.core.config import AppConfig
from jarvis.runtime import JarvisApplication


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> None:
    workspace_root = Path(__file__).resolve().parent
    load_dotenv(workspace_root / ".env", override=False)
    config = AppConfig.from_env()
    configure_logging(config.system.log_level)
    app = JarvisApplication(config)
    app.run_forever()


if __name__ == "__main__":
    main()
