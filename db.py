USERS = {}
PAYMENTS = {}

async def get_or_create_user(tg_id: int, lang: str = "fr"):
    if tg_id in USERS:
        return USERS[tg_id]
    user = {"id": tg_id, "tg_id": tg_id, "lang": lang}
    USERS[tg_id] = user
    return user
