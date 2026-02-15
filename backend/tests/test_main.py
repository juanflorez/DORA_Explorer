from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

MOCK_PROJECTS = [{"id": "p1", "name": "Project One"}]
MOCK_REPOS = [{"id": "r1", "name": "Repo One"}]
MOCK_ENVIRONMENTS = [{"id": 1, "name": "production"}]
MOCK_DEPLOYMENTS = [
    {
        "id": 101,
        "definition": {"name": "deploy-pipeline"},
        "result": "succeeded",
        "startedOn": "2025-12-01T10:00:00Z",
        "finishedOn": "2025-12-01T10:05:00Z",
    }
]


async def test_health():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.api.routes.list_projects", new_callable=AsyncMock)
async def test_projects(mock_list):
    mock_list.return_value = MOCK_PROJECTS
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/projects", json={"org": "myorg", "pat": "fake-token"}
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Project One"


@patch("app.api.routes.list_repos", new_callable=AsyncMock)
async def test_repos(mock_list):
    mock_list.return_value = MOCK_REPOS
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/repos",
            json={"org": "myorg", "pat": "fake-token", "project": "proj"},
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Repo One"


@patch("app.api.routes.list_environments", new_callable=AsyncMock)
async def test_environments(mock_list):
    mock_list.return_value = MOCK_ENVIRONMENTS
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/environments",
            json={"org": "myorg", "pat": "fake-token", "project": "proj"},
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "production"
    assert data[0]["id"] == 1


@patch("app.api.routes.get_deployments", new_callable=AsyncMock)
async def test_deployments(mock_get):
    mock_get.return_value = MOCK_DEPLOYMENTS
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/deployments",
            json={
                "org": "myorg",
                "pat": "fake-token",
                "project": "proj",
                "environment_id": 1,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["pipeline_name"] == "deploy-pipeline"
    assert data[0]["result"] == "succeeded"
