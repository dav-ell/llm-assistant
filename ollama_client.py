# ollama_client.py

from ollama import Client, chat
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

# **New Function for Streaming**
def send_to_ollama_stream(prompt):
    user_message = {
        'role': 'user',
        'content': prompt
    }
    
    try:
        client = Client()
        logger.info("Starting streaming with Ollama.")
        for part in client.chat(model=OLLAMA_MODEL_NAME, messages=[user_message], stream=True):
            assistant_part = part.get('message', {}).get('content', '')
            if assistant_part:
                yield assistant_part
        logger.info("Completed streaming response from Ollama.")
    except Exception as e:
        logger.error(f"Error streaming from Ollama: {e}")
        yield "Error communicating with the assistant."   
        