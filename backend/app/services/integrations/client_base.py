from abc import ABC, abstractmethod
import time
from typing import Dict, Any, List, Optional
import httpx


class BaseHealthcareClient(ABC):
    """Abstract base class for healthcare data integration connectors."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 30,
        rate_limit_per_min: int = 60,
        auth_headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.rate_limit_per_min = rate_limit_per_min
        self.auth_headers = auth_headers or {}

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity and returns status, latency, and diagnostics."""
        pass

    @abstractmethod
    async def fetch_records(
        self,
        resource_type: str,
        page: int = 1,
        limit: int = 50,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetches raw records from the external source."""
        pass
