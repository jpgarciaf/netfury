"""Central configuration for NetFury using pydantic-settings.

All settings are read from environment variables or a .env file.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider ---
    llm_provider: str = Field(
        default="anthropic",
        description="LLM provider: anthropic | openai | google | local",
    )
    llm_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model identifier for the selected provider",
    )

    # --- API keys ---
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    google_api_key: str = Field(
        default="",
        validation_alias="GEMINI_API_KEY",
    )

    # --- Ollama (local) ---
    ollama_base_url: str = Field(default="http://localhost:11434")

    # --- Evaluation ---
    eval_models: str = Field(
        default="claude-sonnet-4-20250514,gpt-4o,gpt-4o-mini,gemini-2.0-flash",
        description="Comma-separated list of models to evaluate",
    )
    eval_isp: str = Field(default="xtrim")

    # --- Scraping ---
    scrape_delay_min: float = Field(default=2.0)
    scrape_delay_max: float = Field(default=5.0)
    screenshot_width: int = Field(default=1440)
    screenshot_height: int = Field(default=900)

    def get_eval_models_list(self) -> list[str]:
        """Return evaluation models as a list."""
        return [m.strip() for m in self.eval_models.split(",") if m.strip()]


# --- LLM Pricing Table (USD per 1M tokens) ---
LLM_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "llava:13b": {"input": 0.00, "output": 0.00},
    "moondream": {"input": 0.00, "output": 0.00},
}

# --- ISP Company Mapping (Superintendencia de Companias) ---
ISP_COMPANY_MAP: dict[str, str] = {
    "netlife": "MEGADATOS S.A.",
    "ecuanet": "MEGADATOS S.A.",
    "claro": "CONECEL S.A.",
    "cnt": "CORPORACION NACIONAL DE TELECOMUNICACIONES CNT EP",
    "xtrim": "SETEL S.A.",
    "puntonet": "PUNTONET S.A.",
    "alfanet": "ALFANET S.A.",
    "fibramax": "FIBRAMAX S.A.",
}

# --- ISP URLs ---
ISP_URLS: dict[str, str] = {
    "netlife": "https://www.netlife.ec",
    "ecuanet": "https://www.ecuanet.ec",
    "claro": "https://www.claro.com.ec",
    "cnt": "https://www.cnt.gob.ec",
    "xtrim": "https://www.xtrim.com.ec",
    "puntonet": "https://www.celerity.ec",
    "alfanet": "https://www.alfanet.ec",
    "fibramax": "https://www.fibramax.ec",
}


def get_settings() -> Settings:
    """Create and return a Settings instance (cached on first call)."""
    return Settings()
