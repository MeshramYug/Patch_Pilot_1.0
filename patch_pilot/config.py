"""
Configuration management for PatchPilot.
Loads settings from environment variables and .env files.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Automatically load .env if present
load_dotenv()

class Config:
    """Global configuration settings."""
    
    # Provider selection: 'gemini', 'groq', 'ollama', 'openai', 'mock'
    PROVIDER: str = os.getenv("PATCH_PILOT_PROVIDER", "").lower()
    
    # API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Ollama settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    
    # Default models
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Execution & Self-Healing limits
    MAX_REPAIR_ATTEMPTS: int = int(os.getenv("MAX_REPAIR_ATTEMPTS", "3"))
    SANDBOX_TIMEOUT_SECONDS: int = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "15"))

    @classmethod
    def resolve_provider(cls) -> str:
        """Determines the active provider based on environment or explicit setting."""
        if cls.PROVIDER:
            return cls.PROVIDER
        if cls.GEMINI_API_KEY:
            return "gemini"
        if cls.GROQ_API_KEY:
            return "groq"
        if cls.OPENAI_API_KEY:
            return "openai"
        return "mock"
