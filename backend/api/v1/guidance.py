from fastapi import APIRouter, HTTPException

from backend.api.v1.demo import get_demo_service
from backend.services.application_guidance import build_guidance_packet


router = APIRouter(prefix="/guidance", tags=["Application guidance"])


@router.get("/schemes/{scheme_id}")
def guidance_for_scheme(scheme_id: str):
    if not scheme_id.startswith("demo-"):
        raise HTTPException(
            status_code=404,
            detail="No source-backed application guide is stored for this scheme.",
        )
    detail = get_demo_service(scheme_id)
    packet = build_guidance_packet(detail)
    packet["source"] = "catalogue"
    return packet
