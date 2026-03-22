from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix='/health', tags=['health'])


@router.get('')
def health():
    return {
        'status': 'ok',
        'service': 'lattice-backend-fastapi',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
