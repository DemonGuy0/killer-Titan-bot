try:
    from pyrogram import Client
    from utils.config import API_HASH, API_ID, MOBILE_NUMBER #, SESION
except Exception as e:
    print(e)
    print("\nInstall pyrogram: pip3 install pyrogram")
    exit(1)

print("Required pyrogram V2 or greater.")
API_KEY = API_ID
API_HASH = API_HASH
PHONE = MOBILE_NUMBER
PASSWORD = 'killerj002005_14'

with Client("userbot_session", api_id=API_KEY, api_hash=API_HASH, phone_number=PHONE, password=PASSWORD, in_memory=True) as app:
    print(app.export_session_string())
