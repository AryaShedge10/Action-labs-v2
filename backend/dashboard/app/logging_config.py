"""Logging without PHI. Never log patient records, notes, or transcripts."""

import logging
import sys

SAFE_KEYS = {
    "encounter_id",
    "status",
    "action",
    "event",
    "conflict_count",
    "severity",
    "handoff_status",
    "path",
    "method",
}


class RedactingFilter(logging.Filter):
    BLOCKED = (
        "patient",
        "transcript",
        "allergy",
        "medication",
        "note",
        "soap",
        "diagnosis",
        "phi",
        "dob",
        "name",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = str(record.getMessage()).lower()
        if any(token in message for token in self.BLOCKED):
            record.msg = "redacted log message (possible PHI)"
            record.args = ()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
