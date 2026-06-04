from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://tbr:tbr@postgres:5432/tbr"
    dataset_dir: Path = Path(__file__).resolve().parents[2] / "the_blue_red_candidate_case_dataset"
    auto_seed: bool = True
    llm_enabled: bool = False
    llm_model: str = "gpt-4.1-mini"
    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        env_prefix = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
