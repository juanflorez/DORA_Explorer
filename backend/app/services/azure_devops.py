import base64
from datetime import UTC, datetime, timedelta

import httpx

BASE_URL = "https://dev.azure.com"
API_VERSION = "7.1"


def _auth_header(pat: str) -> dict[str, str]:
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


async def list_projects(org: str, pat: str) -> list[dict]:
    url = f"{BASE_URL}/{org}/_apis/projects"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers=_auth_header(pat),
            params={"api-version": API_VERSION},
        )
        resp.raise_for_status()
        return resp.json()["value"]


async def list_repos(org: str, project: str, pat: str) -> list[dict]:
    url = f"{BASE_URL}/{org}/{project}/_apis/git/repositories"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers=_auth_header(pat),
            params={"api-version": API_VERSION},
        )
        resp.raise_for_status()
        return resp.json()["value"]


async def list_environments(org: str, project: str, pat: str) -> list[dict]:
    url = f"{BASE_URL}/{org}/{project}/_apis/distributedtask/environments"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers=_auth_header(pat),
            params={"api-version": API_VERSION},
        )
        resp.raise_for_status()
        return resp.json()["value"]


async def get_deployments(
    org: str, project: str, environment_id: int, pat: str
) -> list[dict]:
    """Get deployment records for an environment from the past 6 months."""
    url = (
        f"{BASE_URL}/{org}/{project}/_apis/distributedtask/environments"
        f"/{environment_id}/environmentdeploymentrecords"
    )
    six_months_ago = datetime.now(UTC) - timedelta(days=180)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers=_auth_header(pat),
            params={
                "api-version": API_VERSION,
                "top": 500,
                "minStartedTime": six_months_ago.isoformat(),
            },
        )
        resp.raise_for_status()
        return resp.json()["value"]
