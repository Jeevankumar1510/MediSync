import time
from typing import Dict, Any, List, Optional
import httpx

from app.services.integrations.client_base import BaseHealthcareClient


class VendorRESTClient(BaseHealthcareClient):
    """
    Client connector for non-standard proprietary EHR REST APIs.
    Communicates via custom endpoints and retrieves un-normalized vendor clinical dumps.
    """

    async def test_connection(self) -> Dict[str, Any]:
        """Pings the base or records endpoint."""
        url = f"{self.base_url}"
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=self.auth_headers)
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "latency_ms": latency,
                    "message": "Vendor endpoint reachable." if response.status_code < 400 else f"HTTP {response.status_code}",
                    "details": {"content_type": response.headers.get("content-type", "unknown")}
                }
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "status_code": None,
                "latency_ms": latency,
                "message": f"Connection failed: {str(exc)}",
                "details": None
            }

    async def fetch_records(
        self,
        resource_type: str = "records",
        page: int = 1,
        limit: int = 50,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Queries the proprietary vendor JSON endpoint."""
        url = f"{self.base_url}/{resource_type}" if not self.base_url.endswith(resource_type) else self.base_url
        query_params = params.copy() if params else {}

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=self.auth_headers, params=query_params)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # Search common collection keys
                for key in ["patients", "records", "data", "results", "items"]:
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
            return []
