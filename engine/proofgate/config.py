"""Runtime settings, read once from the environment (and engine/.env if present)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ENGINE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ENGINE_DIR / ".env")


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name, "").strip()
    return value or default


@dataclass(frozen=True)
class Settings:
    nebius_api_key: str = field(default_factory=lambda: _env("NEBIUS_API_KEY"))
    nebius_base_url: str = field(
        default_factory=lambda: _env("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
    )
    tavily_api_key: str = field(default_factory=lambda: _env("TAVILY_API_KEY"))
    github_token: str = field(default_factory=lambda: _env("GITHUB_TOKEN"))

    model_nano: str = field(default_factory=lambda: _env("PG_MODEL_NANO"))
    model_omni: str = field(default_factory=lambda: _env("PG_MODEL_OMNI"))
    model_super: str = field(default_factory=lambda: _env("PG_MODEL_SUPER"))
    model_ultra: str = field(default_factory=lambda: _env("PG_MODEL_ULTRA"))

    sandbox: str = field(default_factory=lambda: _env("PG_SANDBOX", "docker"))
    max_cost_per_report: float = field(
        default_factory=lambda: float(_env("PG_MAX_COST_PER_REPORT", "0.25"))
    )
    cache_dir: Path = field(
        default_factory=lambda: Path(
            _env("PG_CACHE_DIR", str(Path.home() / ".cache" / "proofgate"))
        )
    )

    @property
    def repos_dir(self) -> Path:
        return self.cache_dir / "repos"

    @property
    def db_path(self) -> Path:
        return self.cache_dir / "proofgate.sqlite"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.nebius_api_key)

    @property
    def tavily_enabled(self) -> bool:
        return bool(self.tavily_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
