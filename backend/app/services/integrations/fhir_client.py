import time
from typing import Dict, Any, List, Optional
import httpx

from app.services.integrations.client_base import BaseHealthcareClient


class FHIRClient(BaseHealthcareClient):
    """
    Standardized client adapter for FHIR R4 REST APIs.
    Supports OAuth2 / Bearer token authentication, pagination, and Bundle extraction.
    """

    async def test_connection(self) -> Dict[str, Any]:
        """Pings the FHIR conformance statement (metadata)."""
        url = f"{self.base_url}/metadata"
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url, headers=self.auth_headers)
                latency = round((time.perf_counter() - start_time) * 1000, 2)

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "status_code": 200,
                        "latency_ms": latency,
                        "message": "Connected to FHIR server successfully.",
                        "details": {
                            "fhirVersion": data.get("fhirVersion", "4.0.1"),
                            "publisher": data.get("publisher", "Unknown"),
                        }
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "latency_ms": latency,
                        "message": f"Server responded with HTTP {response.status_code}",
                        "details": {"response_text": response.text[:200]}
                    }
        except httpx.TimeoutException:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "success": False,
                "status_code": None,
                "latency_ms": latency,
                "message": f"Connection timed out after {self.timeout_seconds}s.",
                "details": None
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
        resource_type: str,
        page: int = 1,
        limit: int = 50,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Queries FHIR resource endpoints (e.g. /Patient, /Observation) and unpacks the Bundle."""
        url = f"{self.base_url}/{resource_type}"
        query_params = params.copy() if params else {}
        query_params["_count"] = limit
        query_params["_offset"] = (page - 1) * limit

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, headers=self.auth_headers, params=query_params)
            response.raise_for_status()
            data = response.json()

            # Unpack FHIR Bundle
            records: List[Dict[str, Any]] = []
            if data.get("resourceType") == "Bundle" and "entry" in data:
                for entry in data["entry"]:
                    if "resource" in entry:
                        records.append(entry["resource"])
            elif isinstance(data, dict) and "resourceType" in data:
                records.append(data)

            return records
