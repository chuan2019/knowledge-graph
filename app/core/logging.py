from __future__ import annotations

import logging


DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
        return

    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)