import logging
import sys
from typing import Optional

def setup_logger(name: str = "a11y_auditor", level: Optional[str] = None) -> logging.Logger:
    """Configures structured stdout logger for the accessibility audit engine."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level or logging.INFO)
        logger.propagate = False
    return logger

logger = setup_logger("a11y_auditor")
