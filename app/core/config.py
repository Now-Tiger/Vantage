#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: config.py
# description: Class to access env variables
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str
    ALGORITHM: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # database parameters
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DATABASE_URL: str
    DB_NAME: str
    DB_ECHO: bool
    DATABASE_POOL_SIZE: int
    DATABASE_MAX_OVERFLOW: int
    DATABASE_ECHO: bool

    LLM_PROVIDER: str
    LLM_MODEL: str
    LLM_TEMPERATURE: float
    LLM_MAX_TOKENS: int

    OPENAI_API_KEY: SecretStr
    ANTHROPIC_API_KEY: SecretStr
    BASE_URL: str

    MAX_PDF_SIZE_MB: int
    PDF_CHUNK_SIZE: int

    LANGGRAPH_RECURSION_LIMIT: int

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# export settings
settings = Settings()
