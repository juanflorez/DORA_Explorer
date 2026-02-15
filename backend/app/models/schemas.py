from pydantic import BaseModel


class AzureCredentials(BaseModel):
    org: str
    pat: str


class ProjectRequest(AzureCredentials):
    pass


class RepoRequest(AzureCredentials):
    project: str


class EnvironmentRequest(AzureCredentials):
    project: str


class DeploymentRequest(AzureCredentials):
    project: str
    environment_id: int


class ProjectItem(BaseModel):
    id: str
    name: str


class RepoItem(BaseModel):
    id: str
    name: str


class EnvironmentItem(BaseModel):
    id: int
    name: str


class DeploymentRecord(BaseModel):
    id: int
    pipeline_name: str
    result: str
    started_on: str
    finished_on: str
