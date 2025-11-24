#!/usr/bin/env python3
"""Quick script to check whether google.generativeai.GenerationConfig accepts "response_modalities".
Usage: python scripts/check_genai_response_modalities.py
"""
import sys
try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig
    print("Imported google.generativeai and GenerationConfig OK")
    try:
        cfg = GenerationConfig(temperature=0.7, response_modalities=["text"])  # try to include the keyword
        print("GenerationConfig accepted response_modalities:", cfg)
    except TypeError as e:
        print("GenerationConfig rejected response_modalities:", e)
    except Exception as e:
        print("Other error when creating GenerationConfig:", e)
except Exception as e:
    print("Failed to import google.generativeai or GenerationConfig:", e)
    sys.exit(1)
