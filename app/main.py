#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filename: main.py
# description: Main application file
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as process_router
from app.db.connection import close_pool, init_pool

# LangChain's AIMessage.parsed field triggers a harmless Pydantic v2
# serialization warning when with_structured_output() is used.
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await init_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Vantage",
    description="AI-powered claim document segregation and multi-agent extraction service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "Claim Processing Pipeline",
        "version": "1.0.0",
        "endpoints": {"process": "POST /api/process", "health": "GET /api/health", "docs": "/docs"},
    }
