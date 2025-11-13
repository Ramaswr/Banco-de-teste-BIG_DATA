"""SMS integration using Twilio with fallback logging."""

import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Twilio config from .secrets/twilio.env
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

ENV_PATH = os.path.expanduser(".secrets/twilio.env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            if k == "TWILIO_ACCOUNT_SID" and not TWILIO_ACCOUNT_SID:
                TWILIO_ACCOUNT_SID = v.strip()
            if k == "TWILIO_AUTH_TOKEN" and not TWILIO_AUTH_TOKEN:
                TWILIO_AUTH_TOKEN = v.strip()
            if k == "TWILIO_FROM_NUMBER" and not TWILIO_FROM_NUMBER:
                TWILIO_FROM_NUMBER = v.strip()

TWILIO_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER)


def send_otp(phone: str, otp: str, username: str = "") -> tuple[bool, str]:
    """
    Send OTP via SMS using Twilio.
    Returns (success: bool, message: str)
    """
    if not TWILIO_ENABLED:
        # Fallback: log OTP locally
        msg = f"[OTP-LOG] user={username} phone={phone} otp={otp}"
        logger.warning(msg)
        return False, msg

    try:
        from twilio.rest import Client

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        body_text = f"Seu código OTP para Jerr_BIG-DATE: {otp} (válido por 5 minutos)"
        message = client.messages.create(
            body=body_text, from_=TWILIO_FROM_NUMBER, to=phone
        )
        logger.info(f"SMS enviado para {phone}: SID={message.sid}")
        return True, f"OTP enviado para {phone}"
    except Exception as e:
        logger.error(f"Erro ao enviar SMS: {e}")
        # Fallback
        msg = f"[OTP-LOG-FALLBACK] user={username} phone={phone} otp={otp} error={e}"
        logger.warning(msg)
        return False, f"SMS falhou (fallback para log): {e}"
