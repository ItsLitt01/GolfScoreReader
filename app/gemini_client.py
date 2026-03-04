# app/gemini_client.py
"""Gemini API client and image helpers."""
from __future__ import annotations

import os
from typing import List

from fastapi import HTTPException
from PIL import Image, ImageOps
import google.generativeai as genai

from app import config

_resolved_model: str | None = None


def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not set. Set it in your environment or in a .env file in the project root.",
        )
    return key


def get_model_list() -> List[str]:
    """Order of models to try; env GEMINI_MODEL overrides to a single model."""
    override = os.environ.get("GEMINI_MODEL", "").strip()
    return [override] if override else config.GEMINI_MODEL_ORDER.copy()


def get_resolved_model() -> str:
    """Model name currently in use (for debug)."""
    return _resolved_model or get_model_list()[0]


def get_gemini_model(model_id: str | None = None):
    api_key = get_gemini_api_key()
    genai.configure(api_key=api_key)
    mid = model_id or _resolved_model or get_model_list()[0]
    return genai.GenerativeModel(mid)


def fix_image_orientation(img: Image.Image) -> Image.Image:
    """Fix EXIF orientation so photos from phones are upright."""
    return ImageOps.exif_transpose(img)


def resize_for_vision(img: Image.Image, max_dimension: int | None = None) -> Image.Image:
    """Resize so longest side is at most max_dimension; reduces upload size and speeds up Gemini."""
    max_dimension = max_dimension or config.MAX_IMAGE_DIMENSION
    w, h = img.size
    if w <= max_dimension and h <= max_dimension:
        return img
    if w >= h:
        new_w, new_h = max_dimension, max(1, int(h * max_dimension / w))
    else:
        new_w, new_h = max(1, int(w * max_dimension / h)), max_dimension
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if resized.mode in ("RGBA", "P"):
        resized = resized.convert("RGB")
    return resized


def gemini_vision(img: Image.Image, prompt: str) -> str:
    """Send image + prompt to Gemini; return response text. Tries model list until one works."""
    global _resolved_model
    last_error: str | None = None
    for model_id in get_model_list():
        try:
            model = get_gemini_model(model_id=model_id)
            response = model.generate_content([prompt, img])
            if not response.text:
                raise ValueError("Empty or blocked response from Gemini")
            _resolved_model = model_id
            return response.text.strip()
        except HTTPException:
            raise
        except Exception as e:
            last_error = str(e)
            continue
    raise HTTPException(
        status_code=502,
        detail="Gemini request failed with every model. Last error: " + (last_error or "unknown"),
    )
