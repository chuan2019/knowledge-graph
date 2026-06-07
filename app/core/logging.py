from __future__ import annotations

import logging

from app.core.tracing import current_span_id, current_trace_id


DEFAULT_LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] "
    "trace_id=%(trace_id)s span_id=%(span_id)s %(message)s"
)


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Don't overwrite values already injected via `extra=` (e.g. from error
        # handlers that run outside the active span and supply the stashed IDs).
        if not hasattr(record, "trace_id"):
            record.trace_id = current_trace_id() or "-"
        if not hasattr(record, "span_id"):
            record.span_id = current_span_id() or "-"
        return True


def _configure_handler(handler: logging.Handler, level: int) -> None:
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    if not any(isinstance(existing_filter, TraceContextFilter) for existing_filter in handler.filters):
        handler.addFilter(TraceContextFilter())


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
    
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        _configure_handler(handler, level)