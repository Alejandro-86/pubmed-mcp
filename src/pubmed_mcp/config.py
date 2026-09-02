"""Server configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the PubMed MCP server.

    Args:
        ncbi_api_key: Optional NCBI API key for 10 req/s rate limit.
        max_search_results: Default cap on search results returned per query.
        http_timeout: Timeout in seconds for PubMed API calls.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ncbi_api_key: str = ""
    max_search_results: int = 10
    http_timeout: float = 10.0


settings = Settings()
