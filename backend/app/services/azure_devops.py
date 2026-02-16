import base64
import re
from datetime import UTC, datetime, timedelta

import httpx

BASE_URL = "https://dev.azure.com"
API_VERSION = "7.1"

# Patterns for extracting org from common Azure DevOps URLs
_URL_PATTERNS = [
    re.compile(r"https?://dev\.azure\.com/([^/]+)"),
    re.compile(r"https?://([^.]+)\.visualstudio\.com"),
]


def parse_org(org: str) -> str:
    """Extract org name from a raw string that may be a full URL."""
    org = org.strip().rstrip("/")
    for pattern in _URL_PATTERNS:
        m = pattern.match(org)
        if m:
            return m.group(1)
    return org


def _auth_header(pat: str) -> dict[str, str]:
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


async def list_projects(org: str, pat: str) -> list[dict]:
    org = parse_org(org)
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
    org = parse_org(org)
    url = f"{BASE_URL}/{org}/{project}/_apis/git/repositories"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers=_auth_header(pat),
            params={"api-version": API_VERSION},
        )
        resp.raise_for_status()
        return resp.json()["value"]


async def list_pipelines(org: str, project: str, pat: str) -> list[dict]:
    org = parse_org(org)
    url = f"{BASE_URL}/{org}/{project}/_apis/pipelines"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers=_auth_header(pat),
            params={"api-version": API_VERSION},
        )
        resp.raise_for_status()
        return resp.json()["value"]


async def get_builds(
    org: str, project: str, definition_id: int, pat: str
) -> list[dict]:
    """Get build runs for a pipeline definition from the past 6 months."""
    org = parse_org(org)
    six_months_ago = datetime.now(UTC) - timedelta(days=180)
    url = f"{BASE_URL}/{org}/{project}/_apis/build/builds"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers=_auth_header(pat),
            params={
                "api-version": API_VERSION,
                "definitions": str(definition_id),
                "minTime": six_months_ago.isoformat(),
                "queryOrder": "finishTimeDescending",
                "$top": 500,
            },
        )
        resp.raise_for_status()
        return resp.json()["value"]
