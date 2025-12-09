import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME: str = "Content Workflow (LangGraph + SSE)"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    ENV: str = os.getenv("ENV", "development")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")


settings = Settings()
