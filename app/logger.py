import logging
from logging.handlers import RotatingFileHandler
import os


LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
 
LOG_FILE  = os.path.join (LOG_DIR, "chat.log")

logger = logging.getLogger("chat_app")
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
file_handler.setFormatter(formatter)

# Avoid duplicate handlers if reloaded
if not logger.hasHandlers():
    logger.addHandler(file_handler)
