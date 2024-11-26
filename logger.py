# logger.py

import logging
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE

def setup_logger():
    logger = logging.getLogger('LLMAssistant')
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT)

    # Stream Handler (console)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()