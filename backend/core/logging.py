"""Structured logging (plan, Phase 6).

Never log passwords, tokens, codes or payment credentials, and mask phone numbers.
Log lines with level "ALERT" (CRITICAL) are the ones monitoring should notify on.
"""
import json
import logging
import re
from datetime import datetime, timezone

SENSITIVE_KEY = re.compile(r"pass|secret|token|pin|code|cookie|authorization|csrf", re.I)
PHONE = re.compile(r"\+?\d[\d\s-]{7,}\d")


def mask_phone(text):
    def _mask(m):
        digits = re.sub(r"\D", "", m.group(0))
        return "*" * max(len(digits) - 3, 0) + digits[-3:]

    return PHONE.sub(_mask, str(text))


def scrub(value):
    if isinstance(value, dict):
        return {k: "[redacted]" if SENSITIVE_KEY.search(str(k)) else scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        return mask_phone(value)
    return value


class ScrubFilter(logging.Filter):
    def filter(self, record):
        record.msg = mask_phone(record.getMessage())
        record.args = ()
        if hasattr(record, "data"):
            record.data = scrub(record.data)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        line = {
            "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": "ALERT" if record.levelno >= logging.CRITICAL else record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "data"):
            line["data"] = record.data
        if record.exc_info:
            line["error"] = mask_phone(self.formatException(record.exc_info))
        return json.dumps(line, default=str)


def alert(message, **data):
    """For events monitoring should notify on: lockouts, payment mismatches, tampering."""
    logging.getLogger("secureseat").critical(message, extra={"data": data})
