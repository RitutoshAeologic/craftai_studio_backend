import logging
import sys

def setup_logging(level: str = "INFO") -> logging.Logger:
    log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger("craftai.backend")
    return logger

logger = setup_logging()
