import json
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from app.services import documents as svc
from app.services.ingestion import ingest_document
from app.services import workspaces as ws

router = APIRouter(prefix='/workspaces/{workspace_id}/documents', tags=['documents'])


@router.get('')
def list_documents(workspace_id: str):
    if not ws.get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail='Workspace not found')
    return {'documents': svc.list_documents(workspace_id)}


@router.post('/upload', status_code=202)
async def upload_document(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: str | None = Form(None),
):
    if not ws.get_workspace(workspace_id):
        raise HTTPException(status_code=404, detail='Workspace not found')

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF files are supported')

    md = {}
    if metadata:
        try:
            md = json.loads(metadata)
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid metadata JSON')

    document = await svc.upload_document(workspace_id, file, md)
    background_tasks.add_task(ingest_document, document['id'])
    return {'document': document}
