"""
Universal LLM Client Module
Provides structured JSON generation, Pydantic validation, retries, token usage tracking,
and daily budget enforcement across Google Gemini and OpenAI.
Supports synchronous and asynchronous execution.
"""
import json
import logging
import time
from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
import httpx
from .config import settings

logger = logging.getLogger("core.llm")

class LLMNotConfigured(Exception):
    """Raised when no live LLM API key is configured or provider is unavailable."""
    pass

T = TypeVar("T", bound=BaseModel)

# Approximate Pricing Table per 1M Tokens (USD)
MODEL_PRICING = {
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00}
}

class LLMUsageMeter:
    """Tracks token volume and estimated expenditure against daily demo caps."""
    def __init__(self):
        self.daily_cost_usd = 0.0
        self.total_tokens_today = 0
        self.last_reset_day = time.strftime("%Y-%m-%d")

    def check_and_reset_daily(self):
        today = time.strftime("%Y-%m-%d")
        if today != self.last_reset_day:
            self.daily_cost_usd = 0.0
            self.total_tokens_today = 0
            self.last_reset_day = today

    def record_usage(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        self.check_and_reset_daily()
        rates = MODEL_PRICING.get(model, {"input": 0.10, "output": 0.40})
        cost = (prompt_tokens / 1_000_000.0) * rates["input"] + (completion_tokens / 1_000_000.0) * rates["output"]
        self.daily_cost_usd += cost
        self.total_tokens_today += (prompt_tokens + completion_tokens)
        logger.info(f"LLM Call: {model} | In: {prompt_tokens} | Out: {completion_tokens} | Cost: ${cost:.5f} | Daily: ${self.daily_cost_usd:.4f}")
        return cost

    def is_budget_exceeded(self) -> bool:
        self.check_and_reset_daily()
        return self.daily_cost_usd >= settings.GLOBAL_DAILY_BUDGET_USD

usage_meter = LLMUsageMeter()

class LLMClient:
    """Unified client for structured LLM execution with validation and retries."""

    def __init__(self):
        self.provider = settings.AI_PROVIDER.lower()
        self.gemini_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.openai_key = settings.OPENAI_API_KEY
        self.openai_model = settings.OPENAI_MODEL

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_retries: int = 3
    ) -> T:
        """
        Synchronous execution: generates and returns validated Pydantic model instance.
        Enforces JSON schema output, timeouts, and exponential backoff retries.
        """
        if usage_meter.is_budget_exceeded():
            raise RuntimeError("Daily LLM budget cap reached ($10.00). Demo temporarily paused to prevent bill overrun.")

        if (self.provider == "gemini" and not self.gemini_key) or (self.provider == "openai" and not self.openai_key):
            raise LLMNotConfigured(f"No active LLM API key configured for provider '{self.provider}'.")
        if self.provider not in ("gemini", "openai"):
            raise LLMNotConfigured(f"Unsupported AI provider: '{self.provider}'.")

        schema = response_model.model_json_schema()
        schema_str = json.dumps(schema)

        augmented_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: You must reply with a valid JSON object strictly matching this JSON Schema:\n"
            f"{schema_str}\n"
            f"Do not include any introductory or concluding text, explanations, or code blocks. Return ONLY raw JSON."
        )

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                if self.provider == "gemini":
                    raw_text, in_tok, out_tok = self._call_gemini_sync(
                        prompt=augmented_prompt,
                        system_instruction=system_instruction,
                        temperature=temperature
                    )
                elif self.provider == "openai":
                    raw_text, in_tok, out_tok = self._call_openai_sync(
                        prompt=augmented_prompt,
                        system_instruction=system_instruction,
                        temperature=temperature
                    )

                # Parse & Validate with Pydantic
                clean_json = raw_text.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()

                parsed_dict = json.loads(clean_json)
                validated_model = response_model.model_validate(parsed_dict)
                return validated_model

            except LLMNotConfigured:
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"LLM Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(0.3 * (2 ** (attempt - 1)))

        logger.error(f"LLM Generation completely failed after {max_retries} attempts: {last_error}")
        raise ValueError(f"Failed to generate structured response: {last_error}")

    def _call_gemini_sync(self, prompt: str, system_instruction: Optional[str], temperature: float) -> tuple[str, int, int]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini API HTTP {resp.status_code}: {resp.text}")
            data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned by Gemini model.")

            text = candidates[0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            in_tok = usage.get("promptTokenCount", len(prompt) // 4)
            out_tok = usage.get("candidatesTokenCount", len(text) // 4)
            usage_meter.record_usage(self.gemini_model, in_tok, out_tok)
            return text, in_tok, out_tok

    def _call_openai_sync(self, prompt: str, system_instruction: Optional[str], temperature: float) -> tuple[str, int, int]:
        url = "https://api.openai.com/v1/chat/completions"
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": self.openai_model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI API HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            in_tok = usage.get("prompt_tokens", len(prompt) // 4)
            out_tok = usage.get("completion_tokens", len(text) // 4)
            usage_meter.record_usage(self.openai_model, in_tok, out_tok)
            return text, in_tok, out_tok

llm = LLMClient()
