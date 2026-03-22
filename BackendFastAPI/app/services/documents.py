import json
import os
import uuid
from datetime import datetime, timezone
from fastapi import UploadFile
from app.core.config import settings
from app.db.connection import get_conn


async def upload_document(workspace_id: str, file: UploadFile, metadata: dict | None = None) -> dict:
    metadata = metadata or {}
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    doc_id = str(uuid.uuid4())
    safe_name = ''.join(c if c.isalnum() or c in '._-' else '_' for c in file.filename)
    save_name = f"{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4()}-{safe_name}"
    path = os.path.join(settings.UPLOAD_DIR, save_name)

    content = await file.read()
    with open(path, 'wb') as f:
        f.write(content)

    doc_meta = {**metadata, 'uploadedAt': datetime.now(timezone.utc).isoformat()}

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents(id, workspace_id, name, storage_path, status, metadata)
                VALUES (%s,%s,%s,%s,'ingesting',%s::jsonb)
                """,
                (doc_id, workspace_id, file.filename, path, json.dumps(doc_meta)),
            )
        conn.commit()

    return {'id': doc_id, 'name': file.filename, 'status': 'ingesting'}


def list_documents(workspace_id: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, status FROM documents WHERE workspace_id=%s ORDER BY created_at ASC", (workspace_id,))
            return [{'id': r['id'], 'name': r['name'], 'status': r['status']} for r in cur.fetchall()]
