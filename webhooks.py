from fastapi import APIRouter, Request, HTTPException
from payments import finalize_payment

router = APIRouter()

@router.post("/webhooks/test")
async def webhook_test(request: Request):
    data = await request.json()
    provider = data.get("provider")
    external_id = data.get("external_id")
    status = data.get("status")

    if status != "success":
        raise HTTPException(status_code=400, detail="Paiement échoué")

    sub = await finalize_payment(
        external_id=external_id,
        provider=provider,
        auto_renew=False,
        has_7_channels=False,
        current_time_left_hours=0
    )
    if not sub:
        raise HTTPException(status_code=400, detail="No payment found")
    return {"ok": True, "subscription_end": sub["end_at"].isoformat()}
