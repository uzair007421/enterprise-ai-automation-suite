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
                if self.provider == "gemini" and self.gemini_key:
                    raw_text, in_tok, out_tok = self._call_gemini_sync(
                        prompt=augmented_prompt,
                        system_instruction=system_instruction,
                        temperature=temperature
                    )
                elif self.provider == "openai" and self.openai_key:
                    raw_text, in_tok, out_tok = self._call_openai_sync(
                        prompt=augmented_prompt,
                        system_instruction=system_instruction,
                        temperature=temperature
                    )
                else:
                    # Deterministic Sandbox Synthesizer when no live API key is configured
                    raw_text, in_tok, out_tok = self._synthesize_fallback(prompt, response_model)

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

    def _synthesize_fallback(self, prompt: str, model_cls: Type[T]) -> tuple[str, int, int]:
        """
        When external API keys are not supplied in development environment,
        synthesizes high-fidelity domain responses respecting nested schemas and field types.
        """
        schema = model_cls.model_json_schema()
        defs = schema.get("$defs", {})

        def build_obj(s: Dict[str, Any]) -> Dict[str, Any]:
            props = s.get("properties", {})
            out: Dict[str, Any] = {}
            for k, p in props.items():
                out[k] = build_value(k, p)
            return out

        def build_value(k: str, p: Dict[str, Any]) -> Any:
            if "$ref" in p:
                ref_key = p["$ref"].split("/")[-1]
                return build_obj(defs.get(ref_key, {}))
            
            p_type = p.get("type", "string")
            if p_type == "array":
                item_spec = p.get("items", {})
                if "$ref" in item_spec:
                    ref_key = item_spec["$ref"].split("/")[-1]
                    return [build_obj(defs.get(ref_key, {}))]
                return ["Sample entry"]
            elif p_type == "object":
                return build_obj(p)
            elif p_type in ["number", "integer"]:
                if "sentiment" in k.lower():
                    return 35
                elif "subtotal" in k.lower():
                    return 500.00
                elif "tax" in k.lower():
                    return 50.00
                elif "total" in k.lower():
                    return 550.00
                elif "unit_price" in k.lower():
                    return 250.00
                elif "quantity" in k.lower():
                    return 2.0
                elif "line_total" in k.lower():
                    return 500.00
                elif "confidence" in k.lower() or "score" in k.lower():
                    return 95
                return 1.0 if p_type == "number" else 1
            elif p_type == "boolean":
                if "angry" in k.lower() or "escalat" in k.lower():
                    hostile_words = ["scam", "chor", "dhoka", "bakwas", "fraud", "lawyer", "court", "ghatia", "loot", "sharam", "police", "horrible", "worst", "terrible"]
                    return any(w in prompt.lower() for w in hostile_words)
                if "duplicate" in k.lower() or "blocked" in k.lower():
                    return False
                return True
            else:
                # String heuristics based on prompt context
                p_low = prompt.lower()
                if "language" in k.lower():
                    urdu_indicators = ["mera", "meri", "kahan", "kab", "paisa", "paise", "wapis", "hai", "bhai", "karo", "karein", "shukriya", "chahiye", "karwayen", "baat", "insaan", "bohat", "kitnay", "bheja", "salam", "aoa", "ghatia", "bakwas", "chor", "dhoka"]
                    return "Roman Urdu" if any(w in p_low for w in urdu_indicators) else "English"
                elif "plain_english" in k.lower() or "summary" in k.lower():
                    if "429" in prompt:
                        return "Upstream API rate limit throttled requests; exponential backoff applied."
                    elif "401" in prompt:
                        return "OAuth access token expired; refreshed credentials successfully."
                    elif "504" in prompt:
                        return "Downstream gateway timeout occurred; circuit breaker reset connection."
                    return "Diagnostic summary indicating automated remediation success."
                elif "intent" in k.lower():
                    if any(w in p_low for w in ["track", "kahan", "kab", "parcel", "order"]):
                        return "TRACK_ORDER"
                    elif any(w in p_low for w in ["refund", "wapis", "paisa"]):
                        return "REFUND_INQUIRY"
                    elif any(w in p_low for w in ["salam", "hello", "hi", "hey", "aoa"]):
                        return "GREETING"
                    return "PRODUCT_QUESTION"
                elif "sentiment" in k.lower():
                    if any(w in p_low for w in ["scam", "chor", "dhoka", "bakwas", "lawyer"]):
                        return "ANGRY"
                    return "NEUTRAL"
                elif "vendor" in k.lower():
                    return "Acme Global Solutions"
                elif "invoice_number" in k.lower():
                    return "INV-89102"
                elif "currency" in k.lower():
                    return "USD"
                elif "date" in k.lower():
                    return "2026-11-20"
                elif "status" in k.lower():
                    return "APPROVED"
                return f"Verified {k}"

        res_dict = build_obj(schema)
        raw = json.dumps(res_dict)
        return raw, len(prompt) // 4, len(raw) // 4

llm = LLMClient()
