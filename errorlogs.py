import logging
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logging_file")
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")
print("Log file location:", os.path.abspath(log_filename))

logger = logging.getLogger("RAG_emp_app")
logger.setLevel(logging.ERROR)

formatter = logging.Formatter(" %(levelname)s ----> %(message)s  | %(name)s | ---at--- %(asctime)s ")

file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)
logger.propagate = False

# Test call goes here — AFTER handlers are attached
logger.error("Test log entry — if you see this in the file, logging works.")