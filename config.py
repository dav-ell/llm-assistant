# config.py

import os
from datetime import timedelta

# Database Configuration
DATABASE_PATH = '/Users/davell/Library/Containers/today.jason.rem/Data/Library/Application Support/today.jason.rem/db.sqlite3'

# Assistant Configuration
INTERVAL_SECONDS = 15

# Ollama Configuration
OLLAMA_MODEL_NAME = 'llama3.2:3b'  # Update as per your model
OLLAMA_TIMEOUT = 60  # Timeout in seconds

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')  # Can be set to DEBUG for more verbosity
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_FILE = 'assistant.log'

# Prompt Configuration
# Define your prompt here. This is the part you want to prominently feature for easy editing.
DEFAULT_PROMPT = """
You are an assistant that helps answer questions based on recent user context. Provide clear and concise answers to the user's queries.
"""

# You can also define additional prompts or templates as needed