from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient

from app.main import app

MOCK_PROJECTS = [{"id": "p1", "name": "Project One"}]
MOCK_REPOS = [{"id": "r1", "name": "Repo One"}]
MOCK_PIPELINES = [{"id": 10, "name": "deploy-pipeline"}]
MOCK_BUILDS = [
    {
        "id": 101,
        "buildNumber": "20250101.1",
        "definition": {"name": "deploy-pipeline"},
        "result": "succeeded",
        "status": "completed",
        "startTime": "2025-12-01T10:00:00Z",
        "finishTime": "2025-12-01T10:05:00Z",
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


@patch("app.api.routes.list_pipelines", new_callable=AsyncMock)
async def test_pipelines(mock_list):
    mock_list.return_value = MOCK_PIPELINES
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/pipelines",
            json={"org": "myorg", "pat": "fake-token", "project": "proj"},
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "deploy-pipeline"
    assert data[0]["id"] == 10


@patch("app.api.routes.get_builds", new_callable=AsyncMock)
async def test_builds(mock_get):
    mock_get.return_value = MOCK_BUILDS
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/builds",
            json={
                "org": "myorg",
                "pat": "fake-token",
                "project": "proj",
                "definition_id": 10,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["pipeline_name"] == "deploy-pipeline"
    assert data[0]["result"] == "succeeded"
    assert data[0]["build_number"] == "20250101.1"
