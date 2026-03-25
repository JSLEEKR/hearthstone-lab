from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///hearthstone.db"
    BLIZZARD_CLIENT_ID: str = ""
    BLIZZARD_CLIENT_SECRET: str = ""
    BLIZZARD_API_REGION: str = "kr"
    HEARTHSTONE_JSON_URL: str = "https://api.hearthstonejson.com/v1/latest"
    BASE_DIR: Path = Path(__file__).parent
    IMAGE_CACHE_DIR: Path = BASE_DIR / "src" / "web" / "static" / "card_cache"
    IMAGE_BASE_URL: str = "https://art.hearthstonejson.com/v1/render/latest/koKR/512x"
    SIM_MATCHES_PER_MATCHUP: int = 100
    SIM_MAX_TURNS: int = 60
    MCTS_ITERATIONS: int = 1000
    MCTS_ITERATIONS_BULK: int = 200
    SCHEDULER_CRON_HOUR: int = 3
    SCHEDULER_CRON_MINUTE: int = 0
    WEB_HOST: str = "127.0.0.1"
    WEB_PORT: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
