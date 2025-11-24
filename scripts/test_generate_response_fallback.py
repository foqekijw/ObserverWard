#!/usr/bin/env python3
"""Test generate_response fallback handling for response_modalities.

This script imports `generate_response` from main.py and runs a dummy model to
check whether passing `response_modalities` into GenerationConfig triggers our
fallback behavior (since the installed SDK rejects that kw).
"""
import sys
from pathlib import Path
from PIL import Image
from io import BytesIO
import base64

# Ensure project root is on sys.path
proj_root = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, proj_root)
from main import generate_response, CONFIG, render_style

# Minimal dummy render_style if not available
if render_style is None:
    def render_style(style_internal_key, user_content):
        return [
            {"role": "user", "parts": [{"text": user_content}]}
        ]
    render_style = render_style

# Configure CONFIG for the test
CONFIG['temperature'] = 0.7
CONFIG['max_output_tokens'] = 32
CONFIG['response_modalities'] = ["text"]

# Create a small image as screenshot
img = Image.new('RGB', (100, 100), color='white')

class DummyModel:
    def __init__(self):
        self.last_call = None

    def generate_content(self, messages, **kwargs):
        self.last_call = {
            'messages': messages,
            'kwargs': kwargs,
        }
        # Return a simple dict like SDK might
        return {'text': 'dummy response'}

model = DummyModel()
res = generate_response(model, img, 'natural_observer', '1-2 sentences', dynamic_text='test', history=[])
print('Result:', res)
print('Model last_call kwargs:', model.last_call['kwargs'])
