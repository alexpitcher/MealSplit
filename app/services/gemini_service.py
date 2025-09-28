import logging
import math
from functools import lru_cache
from typing import List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """Thin wrapper around Google Gemini APIs for embeddings and text normalization.

    This implementation uses REST via httpx to avoid a hard dependency on vendor SDKs.
    It is fully optional: if GEMINI_API_KEY isn't set, callers should skip using it.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        self.text_model = settings.GEMINI_TEXT_MODEL
        self._client = httpx.Client(timeout=10.0)

    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def embed_texts(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Get embeddings for the given texts. Returns None on error."""
        if not self.is_enabled():
            return None
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.embedding_model}:embedContent?key={self.api_key}"
            vectors: List[List[float]] = []
            for t in texts:
                payload = {
                    "model": self.embedding_model,
                    "content": {"parts": [{"text": t or ""}]},
                }
                resp = self._client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.warning("Gemini embed error %s: %s", resp.status_code, resp.text)
                    return None
                data = resp.json()
                emb = data.get("embedding", {}).get("values")
                if not emb:
                    return None
                vectors.append(emb)
            return vectors
        except Exception as e:
            logger.warning("Gemini embed exception: %s", e)
            return None

    def normalize_text(self, raw: str) -> Optional[str]:
        """Ask Gemini to normalize an item name (optional). Returns None on error."""
        if not self.is_enabled():
            return None
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.text_model}:generateContent?key={self.api_key}"
            prompt = (
                "Normalize the following grocery item name for matching. "
                "Lowercase, remove brand/promo words, standardize units. "
                "Return only the normalized name.\n\nItem: " + (raw or "")
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            resp = self._client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning("Gemini normalize error %s: %s", resp.status_code, resp.text)
                return None
            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                return None
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
            return (text or "").strip().lower()
        except Exception as e:
            logger.warning("Gemini normalize exception: %s", e)
            return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (na * nb)))

