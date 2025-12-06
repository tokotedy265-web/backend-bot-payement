import uuid
import requests
from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from db import get_or_create_user
from payments import start_payment, finalize_payment
from webhooks import router as webhooks_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: mets ton domaine Netlify
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks_router)

WEEK_PRICE = 500
MONTH_PRICE = 2000

def price_for(plan: str) -> int:
    return WEEK_PRICE if plan == "week" else MONTH_PRICE

# 🔹 MTN MoMo
MTN_MOMO_API_KEY = "REMPLACE_PAR_TA_CLE"
MTN_MOMO_BASE_URL = "https://sandbox.momodeveloper.mtn.com"

def requesttopay(external_id, phone, amount):
    headers = {
        "Ocp-Apim-Subscription-Key": MTN_MOMO_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "amount": str(amount),
        "currency": "XAF",
        "externalId": external_id,
        "payer": {"partyIdType": "MSISDN", "partyId": phone},
        "payerMessage": "Paiement GDM237",
        "payeeNote": "Merci pour votre achat"
    }
    r = requests.post(f"{MTN_MOMO_BASE_URL}/collection/v1_0/requesttopay", json=payload, headers=headers)
    return r.status_code, r.text

# 🔹 Orange Money
ORANGE_MONEY_API_KEY = "REMPLACE_PAR_TA_CLE"
ORANGE_MONEY_BASE_URL = "https://api.orange.com/orange-money-webpay/v1/payments"

def orange_init_payment(external_id, phone, amount):
    headers = {
        "Authorization": f"Bearer {ORANGE_MONEY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "amount": str(amount),
        "currency": "XAF",
        "externalId": external_id,
        "payer": phone,
        "message": "Paiement GDM237"
    }
    r = requests.post(ORANGE_MONEY_BASE_URL, json=payload, headers=headers)
    return r.status_code, r.text

@app.post("/api/pay/create")
async def api_pay_create(payload: dict = Body(...)):
    provider = payload["provider"]
    plan = payload["plan"]
    tg_id = payload.get("tg_id")
    phone = payload.get("phone")

    user = await get_or_create_user(int(tg_id or 0), lang="fr")

    external_id = f"{provider}_{uuid.uuid4().hex[:16]}"
    amount = price_for(plan)
    payment = await start_payment(user_id=user["id"], provider=provider, plan=plan, amount=amount, external_id=external_id)

    if provider == "mtn":
        status, text = requesttopay(external_id, phone, amount)
        return {"external_id": external_id, "status": status, "response": text}

    if provider == "orange":
        status, text = orange_init_payment(external_id, phone, amount)
        return {"external_id": external_id, "status": status, "response": text}

    if provider == "visa":
        provider_redirect = f"https://psp.example/pay?ext={external_id}&amount={amount}"
        return {"external_id": external_id, "provider_redirect": provider_redirect}

    if provider == "paypal":
        return {"external_id": external_id}

    return {"external_id": external_id}
