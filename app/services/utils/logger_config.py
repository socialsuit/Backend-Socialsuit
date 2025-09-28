import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "socialsuit.log")

# Rotating file handler
handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=10,
    encoding="utf-8"
)

formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

handler.setFormatter(formatter)

# Console handler
console = logging.StreamHandler()
console.setFormatter(formatter)

# Global logger (optional)
logger = logging.getLogger("socialsuit")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.addHandler(console)


def setup_logger(__name__):
    module_logger = logging.getLogger(__name__)
    module_logger.setLevel(logging.DEBUG)
    if not module_logger.handlers:
        module_logger.addHandler(handler)
        module_logger.addHandler(console)
    return module_logger