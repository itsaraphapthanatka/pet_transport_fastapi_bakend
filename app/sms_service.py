from twilio.rest import Client
from app.config import settings

client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

def send_sms(to: str, message: str):
    client.messages.create(
        body=message,
        from_="+17083160731",
        to="+66942519661"
    )
