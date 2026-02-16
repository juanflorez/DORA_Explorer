from fastapi import APIRouter, HTTPException
from httpx import HTTPStatusError

from app.models.schemas import (
    BuildRecord,
    BuildsRequest,
    PipelineItem,
    PipelineRequest,
    ProjectItem,
    ProjectRequest,
    RepoItem,
    RepoRequest,
)
from app.services.azure_devops import (
    get_builds,
    list_pipelines,
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


@router.post("/pipelines", response_model=list[PipelineItem])
async def pipelines(req: PipelineRequest):
    try:
        data = await list_pipelines(req.org, req.project, req.pat)
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    return [PipelineItem(id=p["id"], name=p["name"]) for p in data]


@router.post("/builds", response_model=list[BuildRecord])
async def builds(req: BuildsRequest):
    try:
        data = await get_builds(req.org, req.project, req.definition_id, req.pat)
    except HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e)) from e
    return [
        BuildRecord(
            id=b["id"],
            build_number=b.get("buildNumber", ""),
            pipeline_name=b.get("definition", {}).get("name", "Unknown"),
            result=b.get("result", "unknown"),
            status=b.get("status", "unknown"),
            started_on=b.get("startTime", ""),
            finished_on=b.get("finishTime", ""),
        )
        for b in data
    ]
