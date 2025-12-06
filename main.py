import uuid
import requests
from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import tes fonctions existantes
from app.db.crud import get_or_create_user
from app.payments.service import start_payment, finalize_payment
from app.webhooks import router as webhooks_router

app = FastAPI()

# Autoriser ton site Netlify à appeler ce backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: mets ton domaine Netlify
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure tes webhooks existants
app.include_router(webhooks_router)

# Prix
WEEK_PRICE = 500
MONTH_PRICE = 2000

def price_for(plan: str) -> int:
    return WEEK_PRICE if plan == "week" else MONTH_PRICE

# 🔹 MTN MoMo
MTN_MOMO_API_KEY = "f7d6765b78714063b6e25f376c20cc79"
MTN_MOMO_BASE_URL = "https://sandbox.momodeveloper.mtn.com"  # change en prod

def requesttopay(external_id, phone, amount):
    headers = {
        "Ocp-Apim-Subscription-Key": MTN_MOMO_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "amount": str(amount),
        "currency": "XAF",
        "externalId": external_id,
        "payer": {
            "partyIdType": "MSISDN",
            "partyId": phone
        },
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

# 🔹 Route pour créer un paiement
@app.post("/api/pay/create")
async def api_pay_create(payload: dict = Body(...)):
    """
    payload: {provider, plan, tg_id, phone?}
    """
    provider = payload["provider"]
    plan = payload["plan"]
    tg_id = payload.get("tg_id")
    phone = payload.get("phone")

    # 1) Lier l'utilisateur Telegram -> user dans DB
    user = await get_or_create_user(int(tg_id or 0), lang="fr")

    # 2) Créer Payment
    external_id = f"{provider}_{uuid.uuid4().hex[:16]}"
    amount = price_for(plan)
    payment = await start_payment(
        user_id=user.id,
        provider=provider,
        plan=plan,
        amount=amount,
        external_id=external_id
    )

    # 3) Initier le provider
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
        # PayPal est géré par le bouton SDK + webhook
        return {"external_id": external_id}

    return {"external_id": external_id}

# 🔹 Exemple webhook direct (si tu veux tester sans passer par app/webhooks)
@app.post("/webhooks/test")
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
    return {"ok": True, "subscription_end": sub.end_at.isoformat()}
