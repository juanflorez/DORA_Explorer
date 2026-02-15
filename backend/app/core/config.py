from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AzTrial"
    debug: bool = False
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_prefix": "AZTRIAL_"}


settings = Settings()
