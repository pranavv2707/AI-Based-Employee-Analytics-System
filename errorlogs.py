import logging
import os
from datetime import datetime

LOG_DIR = "logging_file"
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.ERROR,
    format=" %(levelname)s ----> %(message)s  | %(name)s | ---at--- %(asctime)s ",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("RAG_emp_app")