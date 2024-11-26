# main.py

import time
from datetime import datetime
from config import INTERVAL_SECONDS, DEFAULT_PROMPT
from database import get_db_connection, fetch_recent_full_texts, timer
from ollama_client import send_to_ollama
from logger import logger

def process_entry(frame_id, timestamp, full_text, langid):
    logger.debug(f"Processing frame ID: {frame_id}, Language: {langid}")
    
    # Here, you can modify the prompt as needed.
    # For example, appending context or instructions.
    prompt = DEFAULT_PROMPT + "\n\n" + full_text
    
    assistant_reply = send_to_ollama(prompt)
    
    if assistant_reply:
        logger.info(f"Ollama response for frame {frame_id}: {assistant_reply}")
        
        # TODO: Integrate the assistant_reply as needed
        # Example: Print to console
        print(f"Frame ID: {frame_id}, Timestamp: {timestamp}, Language: {langid}")
        print(f"Full text: {full_text}")
        print(f"Ollama response: {assistant_reply}\n")
    else:
        logger.warning(f"No response from Ollama for frame {frame_id}.")

def main():
    logger.info("Starting LLMAssistant.")
    iteration = 0
    
    try:
        with get_db_connection() as conn:
            while True:
                iteration += 1
                logger.info(f"Starting iteration {iteration}.")
                
                with timer(f"Iteration {iteration}"):
                    entries = fetch_recent_full_texts(conn)
                    
                    for entry in entries:
                        frame_id, timestamp, full_text, langid = entry
                        process_entry(frame_id, timestamp, full_text, langid)
                
                logger.info(f"Sleeping for {INTERVAL_SECONDS} seconds.")
                time.sleep(INTERVAL_SECONDS)
    
    except KeyboardInterrupt:
        logger.info("Received shutdown signal. Exiting gracefully.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("LLMAssistant has stopped.")

if __name__ == "__main__":
    main()