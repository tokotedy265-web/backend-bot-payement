from datetime import datetime, timedelta
from db import PAYMENTS

async def start_payment(user_id: int, provider: str, plan: str, amount: int, external_id: str):
    payment = {
        "user_id": user_id,
        "provider": provider,
        "plan": plan,
        "amount": amount,
        "external_id": external_id,
        "status": "created",
        "created_at": datetime.utcnow()
    }
    PAYMENTS[external_id] = payment
    return payment

async def finalize_payment(external_id: str, provider: str, auto_renew: bool, has_7_channels: bool, current_time_left_hours: int):
    payment = PAYMENTS.get(external_id)
    if not payment:
        return None
    payment["status"] = "success"
    # Simule une subscription
    sub = {
        "user_id": payment["user_id"],
        "provider": provider,
        "plan": payment["plan"],
        "end_at": datetime.utcnow() + timedelta(days=7 if payment["plan"] == "week" else 30)
    }
    return sub
