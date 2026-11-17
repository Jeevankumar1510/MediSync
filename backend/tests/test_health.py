from app.main import app


def test_app_routes_registered():
    """Verify that root, health, docs, and API routes are properly registered in OpenAPI schema."""
    paths = app.openapi()["paths"]
    assert "/" in paths
    assert "/monitoring/health" in paths
    assert "/api/v1/health" in paths


def test_app_metadata():
    """Verify application metadata and configuration."""
    assert app.title == "MediSync AI"
    assert app.version == "1.0.0"
