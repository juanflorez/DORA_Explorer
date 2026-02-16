from pydantic import BaseModel


class AzureCredentials(BaseModel):
    org: str
    pat: str


class ProjectRequest(AzureCredentials):
    pass


class RepoRequest(AzureCredentials):
    project: str


class PipelineRequest(AzureCredentials):
    project: str


class BuildsRequest(AzureCredentials):
    project: str
    definition_id: int


class ProjectItem(BaseModel):
    id: str
    name: str


class RepoItem(BaseModel):
    id: str
    name: str


class PipelineItem(BaseModel):
    id: int
    name: str


class BuildRecord(BaseModel):
    id: int
    build_number: str
    pipeline_name: str
    result: str
    status: str
    started_on: str
    finished_on: str
