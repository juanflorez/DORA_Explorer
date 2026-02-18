"""Azure DevOps REST API client — read-only access."""

import base64
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

BASE_URL = "https://dev.azure.com"
API_VERSION = "7.1"

_URL_PATTERNS = [
    re.compile(r"https?://dev\.azure\.com/([^/]+)"),
    re.compile(r"https?://([^.]+)\.visualstudio\.com"),
]


def parse_org(org: str) -> str:
    org = org.strip().rstrip("/")
    for pattern in _URL_PATTERNS:
        m = pattern.match(org)
        if m:
            return m.group(1)
    return org


def auth_header(pat: str) -> dict[str, str]:
    encoded = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def read_pat() -> str:
    pat_file = Path(__file__).parent / "env.tks"
    if not pat_file.exists():
        print("Error: env.tks not found in project root.")
        sys.exit(1)
    pat = pat_file.read_text().strip()
    if not pat:
        print("Error: env.tks is empty.")
        sys.exit(1)
    return pat


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s)


async def api_get(client: httpx.AsyncClient, url: str, pat: str, params: dict | None = None) -> dict:
    all_params = {"api-version": API_VERSION}
    if params:
        all_params.update(params)
    resp = await client.get(url, headers=auth_header(pat), params=all_params, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def fetch_projects(client: httpx.AsyncClient, org: str, pat: str) -> list[dict]:
    data = await api_get(client, f"{BASE_URL}/{org}/_apis/projects", pat)
    return sorted(data["value"], key=lambda p: p["name"].lower())


async def fetch_pipelines(client: httpx.AsyncClient, org: str, project: str, pat: str) -> list[dict]:
    data = await api_get(client, f"{BASE_URL}/{org}/{project}/_apis/pipelines", pat)
    return sorted(data["value"], key=lambda p: p["name"].lower())


async def fetch_builds(client: httpx.AsyncClient, org: str, project: str, definition_id: int, pat: str) -> list[dict]:
    six_months_ago = datetime.now(UTC) - timedelta(days=180)
    data = await api_get(
        client,
        f"{BASE_URL}/{org}/{project}/_apis/build/builds",
        pat,
        params={
            "definitions": str(definition_id),
            "minTime": six_months_ago.isoformat(),
            "queryOrder": "finishTimeDescending",
            "$top": 500,
        },
    )
    return data["value"]


async def fetch_commit(client: httpx.AsyncClient, org: str, project: str, repo_id: str, commit_id: str, pat: str) -> dict | None:
    url = f"{BASE_URL}/{org}/{project}/_apis/git/repositories/{repo_id}/commits/{commit_id}"
    try:
        data = await api_get(client, url, pat)
        return data
    except httpx.HTTPStatusError:
        return None


async def fetch_repos(client: httpx.AsyncClient, org: str, project: str, pat: str) -> list[dict]:
    data = await api_get(client, f"{BASE_URL}/{org}/{project}/_apis/git/repositories", pat)
    return sorted(data["value"], key=lambda r: r["name"].lower())


async def fetch_pull_requests(
    client: httpx.AsyncClient, org: str, project: str, repo_id: str, pat: str, status: str = "completed"
) -> list[dict]:
    six_months_ago = datetime.now(UTC) - timedelta(days=180)
    data = await api_get(
        client,
        f"{BASE_URL}/{org}/{project}/_apis/git/repositories/{repo_id}/pullrequests",
        pat,
        params={
            "searchCriteria.status": status,
            "searchCriteria.minTime": six_months_ago.isoformat(),
            "searchCriteria.queryTimeRangeType": "closed",
            "$top": 500,
        },
    )
    return data["value"]


async def fetch_pr_commits(
    client: httpx.AsyncClient, org: str, project: str, repo_id: str, pr_id: int, pat: str
) -> list[dict]:
    url = f"{BASE_URL}/{org}/{project}/_apis/git/repositories/{repo_id}/pullRequests/{pr_id}/commits"
    try:
        data = await api_get(client, url, pat)
        return data["value"]
    except httpx.HTTPStatusError:
        return []


async def fetch_all_builds_for_project(
    client: httpx.AsyncClient, org: str, project: str, pat: str
) -> list[dict]:
    """Fetch all builds for a project (past 6 months), not filtered by pipeline."""
    six_months_ago = datetime.now(UTC) - timedelta(days=180)
    data = await api_get(
        client,
        f"{BASE_URL}/{org}/{project}/_apis/build/builds",
        pat,
        params={
            "minTime": six_months_ago.isoformat(),
            "queryOrder": "finishTimeDescending",
            "$top": 500,
        },
    )
    return data["value"]
