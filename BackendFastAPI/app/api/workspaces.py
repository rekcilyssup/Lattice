from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services import workspaces as svc

router = APIRouter(prefix='/workspaces', tags=['workspaces'])


class CreateWorkspaceBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)


@router.get('')
def list_workspaces():
    return {'workspaces': svc.list_workspaces()}


@router.post('')
def create_workspace(body: CreateWorkspaceBody):
    return {'workspace': svc.create_workspace(body.name)}


@router.get('/{workspace_id}')
def get_workspace(workspace_id: str):
    ws = svc.get_workspace(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail='Workspace not found')
    return {'workspace': ws}
