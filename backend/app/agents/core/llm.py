"""
Unified LLM Service for Procurement Flow.
Supports Ollama (primary), OpenAI, Anthropic.

Architecture:
  LLMService
    → Provider selection (auto → ollama → openai → anthropic)
    → Request/Response caching
    → Structured output parsing
    → Procurement-specific helpers (bid analysis, risk analysis)
    → Vision support (image extraction)
"""

from __future__ import annotations

import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standard LLM response envelope."""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def generate(
        self, prompt: str, **kwargs
    ) -> LLMResponse:
        """Generate text from prompt."""
        ...

    @abstractmethod
    async def generate_structured(
        self, prompt: str, schema: Dict, **kwargs
    ) -> Dict:
        """Generate structured output conforming to schema."""
        ...

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        ...

    @abstractmethod
    async def vision_extract(
        self, image_path: str, prompt: str, **kwargs
    ) -> LLMResponse:
        """Extract text from image using vision model."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...


class OllamaProvider(BaseLLMProvider):
    """Ollama provider — primary, local, works offline."""

    def __init__(self, base_url: str = None, default_model: str = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
        self.default_model = default_model or settings.OLLAMA_MODEL or "qwen2.5:7b"
        self.embedding_model = "nomic-embed-text"
        self._available = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check_health()
        return self._available

    def _check_health(self) -> bool:
        try:
            import httpx
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        **kwargs
    ) -> LLMResponse:
        start = time.time()
        model = model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            content=data.get("response", ""),
            model=model,
            provider="ollama",
            tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            latency_ms=(time.time() - start) * 1000,
        )

    async def generate_structured(
        self, prompt: str, schema: Dict, **kwargs
    ) -> Dict:
        structured_prompt = (
            f"{prompt}\n\n"
            f"Respond ONLY with valid JSON conforming to this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )
        response = await self.generate(structured_prompt, **kwargs)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return self._extract_json_from_markdown(response.content)

    async def embed(self, texts: List[str], model: str = None) -> List[List[float]]:
        model = model or self.embedding_model
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": model, "input": texts},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    embeddings = data.get("embeddings", [])
                    if embeddings:
                        return embeddings
        except Exception as e:
            logger.warning(f"Ollama embedding failed: {e}")
        return []

    async def vision_extract(self, image_path: str, prompt: str, **kwargs) -> LLMResponse:
        # Ollama supports vision models like llava
        vision_model = kwargs.get("model", "llava:13b")
        start = time.time()

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": vision_model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                }
            )
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            content=data.get("response", ""),
            model=vision_model,
            provider="ollama",
            tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            latency_ms=(time.time() - start) * 1000,
        )

    @staticmethod
    def _extract_json_from_markdown(content: str) -> Dict:
        """Try to extract JSON from markdown code blocks."""
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
            return json.loads(json_str)
        return {"error": "Failed to parse JSON", "raw": content}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider — fallback for cloud models and vision."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client = None
        self._available = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        if self._available is None:
            self._available = bool(self.api_key)
        return self._available

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        **kwargs
    ) -> LLMResponse:
        start = time.time()
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=model,
            provider="openai",
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=(time.time() - start) * 1000,
        )

    async def generate_structured(
        self, prompt: str, schema: Dict, **kwargs
    ) -> Dict:
        response = await self.generate(prompt, **kwargs)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return OllamaProvider._extract_json_from_markdown(response.content)

    async def embed(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        client = self._get_client()
        resp = await client.embeddings.create(model=model, input=texts)
        return [item.embedding for item in resp.data]

    async def vision_extract(
        self, image_path: str, prompt: str, model: str = "gpt-4o", **kwargs
    ) -> LLMResponse:
        start = time.time()
        client = self._get_client()

        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "application/pdf"

        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_image}"}},
                    ],
                }
            ],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        return LLMResponse(
            content=resp.choices[0].message.content or "",
            model=model,
            provider="openai",
            tokens_used=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=(time.time() - start) * 1000,
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider — fallback for Claude models and vision."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._client = None
        self._available = None

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        if self._available is None:
            self._available = bool(self.api_key)
        return self._available

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        **kwargs
    ) -> LLMResponse:
        start = time.time()
        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]

        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=messages,
        )

        content = resp.content[0].text if resp.content else ""

        return LLMResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=resp.usage.input_tokens + resp.usage.output_tokens if resp.usage else 0,
            latency_ms=(time.time() - start) * 1000,
        )

    async def generate_structured(
        self, prompt: str, schema: Dict, **kwargs
    ) -> Dict:
        response = await self.generate(prompt, **kwargs)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return OllamaProvider._extract_json_from_markdown(response.content)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError("Anthropic does not provide embeddings API")

    async def vision_extract(
        self, image_path: str, prompt: str, model: str = "claude-3-5-sonnet-20241022", **kwargs
    ) -> LLMResponse:
        start = time.time()
        client = self._get_client()

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lower()
        media_type = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

        resp = await client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                    ],
                }
            ],
        )

        content = resp.content[0].text if resp.content else ""

        return LLMResponse(
            content=content,
            model=model,
            provider="anthropic",
            tokens_used=resp.usage.input_tokens + resp.usage.output_tokens if resp.usage else 0,
            latency_ms=(time.time() - start) * 1000,
        )


class LLMCache:
    """Simple in-memory cache for LLM requests."""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, LLMResponse] = {}
        self._max_size = max_size

    def _key(self, prompt: str, provider: str, model: str, temperature: float) -> str:
        import hashlib
        raw = f"{provider}:{model}:{temperature}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def get(
        self, prompt: str, provider: str, model: str, temperature: float
    ) -> Optional[LLMResponse]:
        key = self._key(prompt, provider, model, temperature)
        return self._cache.get(key)

    async def set(
        self, prompt: str, provider: str, model: str, temperature: float, response: LLMResponse
    ):
        key = self._key(prompt, provider, model, temperature)
        if len(self._cache) >= self._max_size:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = response

    def clear(self):
        self._cache.clear()

    def stats(self) -> Dict:
        return {"size": len(self._cache), "max_size": self._max_size}


class LLMService:
    """
    Unified LLM Service for all agents.

    Primary: Ollama (local, qwen2.5:7b)
    Fallbacks: OpenAI (gpt-4o), Anthropic (claude-3.5-sonnet)

    Usage:
        llm = LLMService()
        response = await llm.generate("Analyze this tender...")
        structured = await llm.generate_structured("...", schema={...})
        embeddings = await llm.embed(["text1", "text2"])
    """

    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.cache = LLMCache()
        self._default_provider = "ollama"
        self._default_model = settings.OLLAMA_MODEL or "qwen2.5:7b"

        self._register_providers()

    def _register_providers(self):
        """Register all available providers."""
        # Ollama (primary)
        try:
            provider = OllamaProvider()
            if provider.is_available:
                self.providers["ollama"] = provider
                logger.info("✓ Ollama provider registered (%s)", provider.default_model)
            else:
                logger.warning("Ollama not available at %s", provider.base_url)
        except Exception as e:
            logger.warning("Ollama provider failed: %s", e)

        # OpenAI (fallback)
        if settings.OPENAI_API_KEY:
            try:
                provider = OpenAIProvider()
                if provider.is_available:
                    self.providers["openai"] = provider
                    logger.info("✓ OpenAI provider registered")
            except Exception as e:
                logger.warning("OpenAI provider failed: %s", e)

        # Anthropic (fallback)
        if settings.ANTHROPIC_API_KEY:
            try:
                provider = AnthropicProvider()
                if provider.is_available:
                    self.providers["anthropic"] = provider
                    logger.info("✓ Anthropic provider registered")
            except Exception as e:
                logger.warning("Anthropic provider failed: %s", e)

        if not self.providers:
            logger.error("NO LLM PROVIDERS AVAILABLE — agents requiring LLM will fail")

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        provider: str = "auto",
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: str = "",
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text from prompt.

        Args:
            provider: "auto" | "ollama" | "openai" | "anthropic"
            model: Specific model name (e.g., "qwen2.5:7b", "gpt-4o")
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum output tokens
            system_prompt: System instruction
            use_cache: Whether to cache/retrieve from cache
        """
        # Auto-select provider
        selected_provider = provider
        if provider == "auto":
            selected_provider = self._select_provider(model)

        # Check cache
        if use_cache:
            cached = await self.cache.get(
                prompt, selected_provider, model or self._default_model, temperature
            )
            if cached:
                logger.debug("LLM cache hit for %s", selected_provider)
                return cached

        # Generate
        llm_provider = self.providers.get(selected_provider)
        if not llm_provider:
            raise ValueError(
                f"Provider '{selected_provider}' not available. "
                f"Available: {list(self.providers.keys())}"
            )

        response = await llm_provider.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            **kwargs
        )

        # Cache
        if use_cache:
            await self.cache.set(
                prompt, selected_provider, model or self._default_model, temperature, response
            )

        return response

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict,
        provider: str = "auto",
        model: str = None,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict:
        """Generate structured output conforming to schema."""
        # Lower temperature for structured output
        response = await self.generate(
            prompt=prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            **kwargs
        )
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return self._extract_json_from_markdown(response.content)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    async def embed(self, texts: List[str], provider: str = "ollama") -> List[List[float]]:
        """Generate embeddings for texts."""
        llm_provider = self.providers.get(provider)
        if not llm_provider:
            raise ValueError(f"Provider '{provider}' not available for embeddings")
        return await llm_provider.embed(texts)

    # ------------------------------------------------------------------
    # Vision
    # ------------------------------------------------------------------

    async def vision_extract(
        self,
        image_path: str,
        prompt: str = "Extract all text from this document.",
        provider: str = "auto",
        model: str = None,
        **kwargs
    ) -> LLMResponse:
        """Extract text from image using vision model."""
        if provider == "auto":
            # Prefer OpenAI for vision, then Anthropic, then Ollama (llava)
            for p in ["openai", "anthropic", "ollama"]:
                if p in self.providers:
                    provider = p
                    break
            else:
                raise ValueError("No vision-capable provider available")

        llm_provider = self.providers.get(provider)
        if not llm_provider:
            raise ValueError(f"Provider '{provider}' not available")

        return await llm_provider.vision_extract(
            image_path=image_path, prompt=prompt, model=model, **kwargs
        )

    # ------------------------------------------------------------------
    # Procurement-specific helpers
    # ------------------------------------------------------------------

    async def analyze_bid(self, context: Dict, tender: Dict) -> Dict:
        """Specialized bid/no-bid analysis using LLM."""
        prompt = self._create_bid_prompt(context, tender)
        response = await self.generate(
            prompt=prompt,
            provider="ollama",
            temperature=0.3,
            system_prompt=(
                "You are a senior procurement bid analyst for a Bangladeshi civil works contractor. "
                "Analyze tender opportunities and provide structured recommendations. "
                "Respond in JSON with keys: recommendation, confidence, strengths, risks, margin_strategy"
            ),
        )
        return self._parse_structured(response.content)

    async def analyze_risk(self, context: Dict) -> Dict:
        """Risk analysis for procurement."""
        prompt = self._create_risk_prompt(context)
        response = await self.generate(
            prompt=prompt,
            provider="ollama",
            temperature=0.3,
            system_prompt=(
                "You are a construction risk analyst. Identify and assess risks for Bangladeshi government tenders. "
                "Respond in JSON with keys: overall_risk, financial_risks, technical_risks, "
                "contractual_risks, mitigations"
            ),
        )
        return self._parse_structured(response.content)

    async def summarize_tender(self, tender_text: str, max_length: int = 500) -> str:
        """Summarize tender document text."""
        prompt = f"Summarize this tender document in {max_length} characters or less:\n\n{tender_text[:8000]}"
        response = await self.generate(prompt, provider="ollama", temperature=0.3, max_tokens=512)
        return response.content[:max_length]

    async def extract_criteria(self, tds_text: str) -> Dict:
        """Extract financial/qualification criteria from TDS text."""
        prompt = (
            "Extract all qualification and financial criteria from this TDS section. "
            "Include: experience years, turnover, liquid assets, tender capacity, "
            "tender security, performance security, similar works. "
            "Respond in JSON with these exact keys: "
            "general_experience_years, specific_experience_years, avg_annual_turnover_bdt, "
            "liquid_assets_bdt, min_tender_capacity_bdt, tender_security_bdt, "
            "performance_security_bdt, similar_works_required\n\n"
            f"TDS TEXT:\n{tds_text[:10000]}"
        )
        response = await self.generate(prompt, provider="ollama", temperature=0.2, max_tokens=1024)
        return self._parse_structured(response.content)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _select_provider(self, model: str = None) -> str:
        """Select best provider based on model and availability."""
        if model:
            if model.startswith("gpt") and "openai" in self.providers:
                return "openai"
            if model.startswith("claude") and "anthropic" in self.providers:
                return "anthropic"

        # Default priority: ollama > openai > anthropic
        for p in ["ollama", "openai", "anthropic"]:
            if p in self.providers:
                return p

        raise ValueError("No LLM provider available")

    @staticmethod
    def _extract_json_from_markdown(content: str) -> Dict:
        """Extract JSON from markdown code blocks."""
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
            return json.loads(json_str)
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                return json.loads(parts[1].strip())
        return {"error": "Failed to parse JSON", "raw": content}

    @staticmethod
    def _parse_structured(content: str) -> Dict:
        """Parse structured JSON response, with fallback."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            try:
                return LLMService._extract_json_from_markdown(content)
            except Exception:
                return {"raw_analysis": content, "parsed": False}

    def _create_bid_prompt(self, context: Dict, tender: Dict) -> str:
        # TODO: Replace hardcoded prompts with PromptRegistry.get_prompt()
        # per-agent templates. See backend/app/agents/core/prompt_registry.py
        return f"""Analyze this tender bid opportunity:

TENDER: {tender.get('title', 'Unknown')}
AGENCY: {tender.get('agency', 'Unknown')}
ESTIMATED VALUE: {tender.get('estimated_amount_bdt', 'Unknown')} BDT
ZONE: {tender.get('zone', 'Unknown')}
CLOSING DATE: {tender.get('closing_date', 'Unknown')}

CONTEXT:
{json.dumps(context, indent=2, default=str)}

Provide a structured analysis.
"""

    def _create_risk_prompt(self, context: Dict) -> str:
        # TODO: Replace hardcoded prompts with PromptRegistry.get_prompt()
        # per-agent templates. See backend/app/agents/core/prompt_registry.py
        return f"""Analyze risks for this procurement opportunity:

CONTEXT:
{json.dumps(context, indent=2, default=str)}

Identify and assess all risks.
"""

    def get_stats(self) -> Dict:
        """Get service statistics."""
        return {
            "providers": {name: prov.is_available for name, prov in self.providers.items()},
            "default_provider": self._default_provider,
            "default_model": self._default_model,
            "cache": self.cache.stats(),
        }
