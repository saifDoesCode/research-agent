# logging_config.py
import logging
import sys
from datetime import datetime

def setup_logging(debug: bool = False):
    """
    Call this once at the start of each entry point (research_agent.py, app.py).
    
    Sets up:
      - A console handler (stdout) for human-readable output
      - A file handler that writes to logs/app_YYYYMMDD.log
      - DEBUG level if debug=True, INFO otherwise
    """

    level = logging.DEBUG if debug else logging.INFO

    # Create logs/ directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)

    log_filename = f"logs/app_{datetime.now().strftime('%Y%m%d')}.log"

    # Format: timestamp | level | module | message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # --- Console handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # --- File handler ---
    file_handler = logging.FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # always verbose in file
    file_handler.setFormatter(formatter)

    # --- Root logger ---
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    logging.info(f"Logging initialised — level={logging.getLevelName(level)}, file={log_filename}")