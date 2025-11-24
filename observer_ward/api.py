import os
import time
import base64
from io import BytesIO
from typing import Optional, List, Dict, Any, Callable, TypeVar
from PIL import Image
import google.generativeai as genai
from google.generativeai.generative_models import GenerativeModel
from .config import AppConfig

T = TypeVar("T")

def init_apis(config: AppConfig) -> Optional[GenerativeModel]:
    """Initializes the Gemini API."""
    gem_key = os.getenv("GEMINI_API_KEY", "")
    if not gem_key:
        print("GEMINI_API_KEY not set")
        return None
        
    try:
        os.environ["GEMINI_API_KEY"] = gem_key
        model = GenerativeModel(config.gemini_model)
        print(f"[OK] Gemini Vision ({config.gemini_model}) connected")
        return model
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def with_retry(func: Callable[[], T], config: AppConfig) -> Optional[T]:
    """Executes a function with retry logic."""
    max_attempts = config.retry_max_attempts
    if config.disable_retries:
        max_attempts = 1
        
    initial_delay = config.retry_initial_delay
    backoff = config.retry_backoff_factor
    
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt < max_attempts - 1:
                delay = initial_delay * (backoff ** attempt) if not config.disable_retries else 0
                if delay > 0:
                    print(f"Attempt {attempt+1} failed, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    print(f"Attempt {attempt+1} failed, retrying immediately...")
            else:
                print(f"All attempts failed: {e}")
                return None
    return None

def analyze_with_gemini(model: GenerativeModel, 
                       screenshot: Image.Image, 
                       config: AppConfig,
                       style_prompt: Optional[str] = None, 
                       history: Optional[List[Dict]] = None,
                       user_message: Optional[str] = None) -> Optional[str]:
    """
    Sends image to Gemini and gets a comment.
    """
    try:
        buf = BytesIO()
        screenshot.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode()
        
        user_text = (
            "Дай короткий, целостный комментарий к изображению в выбранном стиле. "
        )
        
        if style_prompt:
            user_text = f"{user_text}\nСтиль: {style_prompt}"
            
        full_prompt = f"{style_prompt}\n\n{user_text}" if style_prompt else user_text
        
        if user_message:
            full_prompt += f"\n\n[USER MESSAGE]: {user_message}\n(Please answer the user's message while also considering the context of the screen and the persona)"

        contents = [
            {
                "role": "user",
                "parts": [
                    {"text": full_prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_base64}}
                ]
            }
        ]
        
        gen_cfg_params = {
            "temperature": config.temperature,
            "max_output_tokens": config.max_output_tokens
        }
        
        try:
            response = model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(**gen_cfg_params)
            )
            return response.text
        except Exception as e:
            raise e
            
    except Exception as e:
        raise e
