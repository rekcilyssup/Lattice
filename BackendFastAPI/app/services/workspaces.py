import json
import uuid
from app.db.connection import get_conn


def _normalize_workspace_id(workspace_id: str) -> str | None:
    try:
        return str(uuid.UUID(str(workspace_id)))
    except Exception:
        return None


def _get_documents(workspace_id: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, status FROM documents WHERE workspace_id=%s ORDER BY created_at ASC", (workspace_id,)
            )
            return [{'id': r['id'], 'name': r['name'], 'status': r['status']} for r in cur.fetchall()]


def _get_messages(workspace_id: str) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, role, content, citations FROM messages WHERE workspace_id=%s ORDER BY created_at ASC",
                (workspace_id,),
            )
            rows = cur.fetchall()
            out = []
            for r in rows:
                citations = r['citations'] if isinstance(r['citations'], list) else json.loads(r['citations'] or '[]')
                out.append({'id': r['id'], 'role': r['role'], 'content': r['content'], 'citations': citations})
            return out


def create_workspace(name: str) -> dict:
    wid = str(uuid.uuid4())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO workspaces(id, name) VALUES (%s, %s)", (wid, name))
            cur.execute(
                "INSERT INTO messages(id, workspace_id, role, content, citations) VALUES (%s,%s,'assistant',%s,%s::jsonb)",
                (
                    str(uuid.uuid4()),
                    wid,
                    f'Workspace created. Upload documents to start grounded Q&A in "{name}".',
                    '[]',
                ),
            )
        conn.commit()
    return get_workspace(wid)


def get_workspace(workspace_id: str) -> dict | None:
    normalized_workspace_id = _normalize_workspace_id(workspace_id)
    if not normalized_workspace_id:
        return None

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM workspaces WHERE id=%s", (normalized_workspace_id,))
            row = cur.fetchone()
            if not row:
                return None

    return {
        'id': row['id'],
        'name': row['name'],
        'documents': _get_documents(normalized_workspace_id),
        'messages': _get_messages(normalized_workspace_id),
    }


def list_workspaces() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces ORDER BY created_at ASC")
            ids = [r['id'] for r in cur.fetchall()]
    return [get_workspace(wid) for wid in ids]
