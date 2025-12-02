import os
import json
import logging
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
                    logging.warning(f"Attempt {attempt+1} failed: {e}")
                    time.sleep(delay)
                else:
                    print(f"Attempt {attempt+1} failed, retrying immediately...")
                    logging.warning(f"Attempt {attempt+1} failed: {e}")
            else:
                print(f"All attempts failed: {e}")
                logging.error(f"All API attempts failed: {e}")
                return None
    return None

def analyze_with_gemini(model: GenerativeModel, 
                       screenshot: Image.Image, 
                       config: AppConfig,
                       style_prompt: Optional[str] = None, 
                       history: Optional[List[Dict]] = None,
                       user_message: Optional[str] = None,
                       persona_manager: Any = None,
                       # NEW PARAMETERS (backwards compatible)
                       history_manager: Optional[Any] = None,
                       prompt_manager: Optional[Any] = None) -> Optional[str]:
    """
    Sends image to Gemini and gets a comment.
    
    Args:
        model: Gemini model instance
        screenshot: Image to analyze
        config: App configuration
        style_prompt: Style/persona instruction
        history: (DEPRECATED) Raw history list - use history_manager instead
        user_message: Optional user message
        persona_manager: Persona state manager
        history_manager: NEW - HistoryManager instance (preferred over raw history)
        prompt_manager: NEW - PromptManager instance
        
    Returns:
        Comment string or None on error
    """
    try:
        # Lazy imports to avoid circular dependencies
        from .token_counter import TokenCounter
        
        # Encode image
        buf = BytesIO()
        screenshot.save(buf, format="PNG")
        img_bytes = buf.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode()
        
        # Initialize prompt manager if not provided
        if prompt_manager is None:
            from .prompts import PromptManager
            prompt_manager = PromptManager()
        
        # Build prompt components
        persona_instruction = f"PERSONA: {style_prompt}" if style_prompt else ""
        
        persona_context = ""
        if persona_manager and getattr(config, 'use_persona_context', True):
            persona_context = persona_manager.get_context_prompt()
        
        history_display = ""
        if getattr(config, 'use_history_context', True):
            # Use new HistoryManager if provided, otherwise fall back to old method
            if history_manager:
                history_display = history_manager.get_context_for_prompt(
                    max_comments=3,
                    max_tokens=500
                )
            elif history:
                # DEPRECATED: Old method for backwards compatibility
                recent_history = history[-5:]
                history_items = []
                for h in recent_history:
                    if isinstance(h, dict) and h.get('comment'):
                        history_items.append(h.get('comment'))
                
                if history_items:
                    last_comments = history_items[-3:]
                    history_display = "\n".join([f'  {i+1}. "{c}"' for i, c in enumerate(last_comments)])
        
        # Use prompt manager to build final prompt
        try:
            user_text = prompt_manager.build_analysis_prompt(
                persona_instruction=persona_instruction,
                persona_context=persona_context,
                history_display=history_display,
                user_message=user_message or "",
                include_anti_repetition=getattr(config, 'use_anti_repetition', True)
            )
        except Exception as e:
            logging.warning(f"PromptManager failed, falling back to manual prompt: {e}")
            # Fallback to old method if PromptManager fails
            user_text = ""
            if style_prompt:
                user_text += f"PERSONA: {style_prompt}\n\n"
            if persona_context:
                user_text += f"{persona_context}\n\n"
            user_text += """[YOUR PRIMARY TASK]:
Analyze THIS image you are seeing RIGHT NOW.
"""
            if history_display:
                user_text += f"\n[WHAT YOU ALREADY SAID]:\n{history_display}\n"
            if user_message:
                user_text += f"\n[USER MESSAGE]: {user_message}\n"
            user_text += "\nOUTPUT FORMAT: Return a JSON object with fields: comment, mood_update, intensity"
        
        # Debug logging with token count
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            debug_output = "\n" + "="*80 + "\n"
            debug_output += "FULL PROMPT SENT TO GEMINI API\n"
            debug_output += "="*80 + "\n"
            debug_output += user_text
            debug_output += "\n" + "="*80 + "\n"
            
            # Log token count if possible
            try:
                token_counter = TokenCounter()
                token_count = token_counter.count_tokens(user_text)
                debug_output += f"Total tokens: {token_count}\n"
                debug_output += "="*80 + "\n"
            except Exception:
                pass
            
            logging.debug(debug_output)

        # Build API request
        contents = [
            {
                "role": "user",
                "parts": [
                    {"text": user_text},
                    {"inline_data": {"mime_type": "image/png", "data": img_base64}}
                ]
            }
        ]
        
        gen_cfg_params = {
            "temperature": config.temperature,
            "max_output_tokens": config.max_output_tokens,
            "response_mime_type": "application/json"
        }
        
        # Call Gemini API
        try:
            response = model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(**gen_cfg_params)
            )
            
            # Parse JSON response
            try:
                result = json.loads(response.text)
                comment = result.get("comment", "")
                mood = result.get("mood_update", "neutral")
                intensity = result.get("intensity", "low")
                
                # Update Persona State
                if persona_manager:
                    persona_manager.update_state(mood, intensity)
                    persona_manager.record_interaction(comment, mood)
                
                # Add to history manager if provided
                if history_manager:
                    history_manager.add(
                        comment=comment,
                        mood=mood,
                        intensity=intensity,
                        user_message=user_message
                    )
                    
                return comment
            except json.JSONDecodeError:
                # Fallback if JSON fails (rare with response_mime_type)
                logging.warning(f"Failed to parse JSON response: {response.text}")
                return response.text
                
        except Exception as e:
            raise e
            
    except Exception as e:
        raise e

