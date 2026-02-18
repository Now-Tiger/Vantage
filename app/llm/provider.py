#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: llm/provider.py
# description: LLM provider initialization and management

from __future__ import annotations

import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Manages LLM provider initialization based on configuration.
    """

    _instance: Optional[object] = None

    def __new__(cls):
        """Singleton pattern - ensure only one LLM instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize LLM provider."""
        if self._initialized:
            return

        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.base_url = settings.BASE_URL

        self.client = self._initialize_llm()
        self._initialized = True
        logger.info(f"LLM Provider initialized: {self.provider} ({self.model})")

    def _initialize_llm(self):
        """
        Initialize the appropriate LLM based on configuration.

        Returns:
            Initialized language model client
        """
        try:
            if self.provider.lower() == "openai":
                return self._init_openai()
            elif self.provider.lower() == "anthropic":
                return self._init_anthropic()
            else:
                logger.warning(f"Unknown LLM provider: {self.provider}, defaulting to OpenAI")
                return self._init_openai()

        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            raise

    def _init_openai(self):
        """Initialize OpenAI chat model."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in environment variables")

        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=self.base_url,
            model=self.model,
            temperature=float(self.temperature),
            max_completion_tokens=int(self.max_tokens),
            timeout=30,
            max_retries=2,
        )

    def _init_anthropic(self):
        """Initialize Anthropic (Claude) chat model."""
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment variables")

        return ChatAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            model_name=self.model,
            temperature=float(self.temperature),
            max_tokens_to_sample=int(self.max_tokens),
            timeout=30,
            stop=[""],  # TODO: configure this parameter correctly
        )

    def get_client(self):
        """Get the initialized LLM client."""
        return self.client

    def get_model_info(self) -> dict:
        """Get information about the current LLM configuration."""
        return {"provider": self.provider, "model": self.model, "temperature": self.temperature, "max_tokens": self.max_tokens}


def get_llm():
    """
    Get the LLM client instance.

    Returns:
        Initialized language model client
    """
    provider = LLMProvider()
    return provider.get_client()


def get_llm_info() -> dict:
    """
    Get information about the LLM configuration.

    Returns:
        Dictionary with LLM configuration
    """
    provider = LLMProvider()
    return provider.get_model_info()