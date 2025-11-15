"""
Configuration settings for the adjudication system
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "NPHIES Pre-Authorization Adjudication System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = Field(default="change-this-secret-key-in-production", env="SECRET_KEY")
    ALLOWED_HOSTS: list = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    
    # CORS Configuration
    ALLOWED_ORIGINS: list = Field(
        default=["http://localhost:3000", "http://localhost:7860"],
        env="ALLOWED_ORIGINS"
    )
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 7860
    
    # LLM Configuration - Google Gemini Only
    GOOGLE_API_KEY: str = Field(default="", env="GOOGLE_API_KEY")
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_MAX_TOKENS: int = 2000
    GEMINI_TEMPERATURE: float = 0.1
    
    # RAG Configuration
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTOR_STORE_PATH: str = "data/embeddings/chroma_db"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RETRIEVAL: int = 5
    
    # Rules Engine
    RULES_CONFIG_PATH: str = "app/config/rules.yaml"
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./data/health_insurance.db",
        env="DATABASE_URL"
    )
    
    # Redis (optional)
    REDIS_URL: Optional[str] = Field(None, env="REDIS_URL")
    
    # Processing
    MAX_CONCURRENT_REQUESTS: int = 100
    TIMEOUT_SECONDS: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/adjudication.log"
    REDACT_PHI: bool = True
    
    # NPHIES Specific
    NPHIES_VERSION: str = "R4"
    REQUIRED_FHIR_VERSION: str = "4.0.1"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )

# Global settings instance
settings = Settings()
