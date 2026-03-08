from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nova API (api.nova.amazon.com — OpenAI-compatible dev path)
    nova_api_key: str = ""

    # AWS
    aws_region: str = "us-east-1"
    aws_profile: str = "default"
    # Bearer token for boto3 Bedrock calls (production path — enables console visibility).
    # When set, model clients should use boto3 instead of the Nova API.
    aws_bearer_token_bedrock: str = ""

    # Bedrock models
    bedrock_model_sonic: str = "amazon.nova-sonic-v1:0"
    bedrock_model_lite: str = "amazon.nova-lite-v1:0"
    bedrock_model_embedding: str = "amazon.nova-pro-v1:0"

    # Data stores
    redis_url: str = "redis://localhost:6379"
    database_url: str = "postgresql+asyncpg://mc:mc@localhost:5432/missioncontrol"

    # S3
    s3_bucket_evidence: str = "mission-control-evidence-dev"

    # Vector store — required in AWS mode, optional when DEMO_MODE=true
    opensearch_endpoint: str = Field(default="")

    # App
    log_level: str = "INFO"
    demo_mode: bool = False
    api_key: str = "changeme"
    agent_pool_size: int = 6
    backend_url: str = "http://localhost:8000"


settings = Settings()
