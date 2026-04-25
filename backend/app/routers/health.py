from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("", response_class=JSONResponse)
async def healthcheck():
    return {"status": "ok", "service": "transit-ai-backend"}
