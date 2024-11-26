# ollama_client.py

from ollama import chat
from config import OLLAMA_MODEL_NAME, OLLAMA_TIMEOUT
from logger import logger

def send_to_ollama(prompt):
    user_message = {
        'role': 'user',
        'content': prompt
    }
    
    try:
        response = chat(
            model=OLLAMA_MODEL_NAME,
            messages=[user_message]
        )
        
        assistant_reply = response.get('message', {}).get('content', '')
        
        if assistant_reply:
            logger.info("Received response from Ollama.")
            return assistant_reply
        else:
            logger.warning("Ollama returned an empty response.")
            return None
    
    except Exception as e:
        logger.error(f"Error communicating with Ollama: {e}")
        return None