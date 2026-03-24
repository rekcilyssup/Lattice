from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services import chat as svc
from app.services import workspaces as ws

router = APIRouter(prefix='/workspaces/{workspace_id}/chat', tags=['chat'])


class AskBody(BaseModel):
    query: str = Field(min_length=2, max_length=5000)


@router.post('')
async def ask(workspace_id: str, body: AskBody):
    if not ws.get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail='Workspace not found')
    try:
        return await svc.ask_question(workspace_id, body.query)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat endpoint failed ({type(exc).__name__}): {exc}") from exc
