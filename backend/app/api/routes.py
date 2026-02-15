from fastapi import APIRouter, HTTPException
from httpx import HTTPStatusError

from app.models.schemas import (
    DeploymentRecord,
    DeploymentRequest,
    EnvironmentItem,
    EnvironmentRequest,
    ProjectItem,
    ProjectRequest,
    RepoItem,
    RepoRequest,
)
from app.services.azure_devops import (
    get_deployments,
    list_environments,
    list_projects,
    list_repos,
)

router = APIRouter()


@router.post("/projects", response_model=list[ProjectItem])
async def projects(req: ProjectRequest):
    try:
        data = await list_projects(req.org, req.pat)
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    return [ProjectItem(id=p["id"], name=p["name"]) for p in data]


@router.post("/repos", response_model=list[RepoItem])
async def repos(req: RepoRequest):
    try:
        data = await list_repos(req.org, req.project, req.pat)
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    return [RepoItem(id=r["id"], name=r["name"]) for r in data]


@router.post("/environments", response_model=list[EnvironmentItem])
async def environments(req: EnvironmentRequest):
    try:
        data = await list_environments(req.org, req.project, req.pat)
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    return [EnvironmentItem(id=e["id"], name=e["name"]) for e in data]


@router.post("/deployments", response_model=list[DeploymentRecord])
async def deployments(req: DeploymentRequest):
    try:
        data = await get_deployments(req.org, req.project, req.environment_id, req.pat)
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    return [
        DeploymentRecord(
            id=d["id"],
            pipeline_name=d.get("definition", {}).get("name", "Unknown"),
            result=d.get("result", "unknown"),
            started_on=d.get("startedOn", ""),
            finished_on=d.get("finishedOn", ""),
        )
        for d in data
    ]
