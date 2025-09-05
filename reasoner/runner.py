"""LLM runner supporting multiple providers.

This module provides a small abstraction over local language model
providers. The runner keeps the public surface minimal: callers
instantiate ``Runner`` with a provider and call :meth:`generate` with a
prompt string. The implementation intentionally avoids importing heavy
libraries unless the corresponding provider is selected.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

Provider = Literal["none", "transformers", "ollama"]


@dataclass
class Runner:
    """Execute text generation against a configured provider.

    Parameters
    ----------
    provider:
        Backend to use. ``none`` short‑circuits generation and returns an
        empty string. ``transformers`` uses a local Hugging Face model
        defined by ``TRANSFORMERS_MODEL``. ``ollama`` sends the prompt to a
        running Ollama instance using the model specified by
        ``OLLAMA_MODEL``.
    """

    provider: Provider

    def __post_init__(self) -> None:
        self._impl = None
        if self.provider == "transformers":
            model_name = os.environ.get("TRANSFORMERS_MODEL", "gpt2")
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._tok = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModelForCausalLM.from_pretrained(model_name)
        elif self.provider == "ollama":
            import ollama

            self._client = ollama.Client()
            self._model_name = os.environ.get("OLLAMA_MODEL", "llama3:instruct")

    def generate(self, prompt: str, *, max_new_tokens: int = 128) -> str:
        """Generate an answer for ``prompt`` using the configured provider."""

        if self.provider == "none":
            return ""
        if self.provider == "transformers":
            inputs = self._tok(prompt, return_tensors="pt")
            output = self._model.generate(**inputs, max_new_tokens=max_new_tokens)
            return self._tok.decode(output[0], skip_special_tokens=True)
        if self.provider == "ollama":
            response = self._client.generate(model=self._model_name, prompt=prompt)
            return response.get("response", "")
        raise ValueError(f"Unknown provider: {self.provider}")
