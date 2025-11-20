"""SMS integration using Twilio with fallback logging."""

from __future__ import annotations

import hashlib
import logging
import os
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Twilio config from .secrets/twilio.env
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_from_number = os.getenv("TWILIO_FROM_NUMBER")

ENV_PATH = os.path.expanduser(".secrets/twilio.env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            if k == "TWILIO_ACCOUNT_SID" and not twilio_account_sid:
                twilio_account_sid = v.strip()
            if k == "TWILIO_AUTH_TOKEN" and not twilio_auth_token:
                twilio_auth_token = v.strip()
            if k == "TWILIO_FROM_NUMBER" and not twilio_from_number:
                twilio_from_number = v.strip()

TWILIO_ACCOUNT_SID = twilio_account_sid
TWILIO_AUTH_TOKEN = twilio_auth_token
TWILIO_FROM_NUMBER = twilio_from_number

TWILIO_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER)


def _mask_phone(phone: str) -> str:
    digits = re.sub(r"[^0-9]", "", phone)
    if len(digits) <= 4:
        return "***"
    return f"***{digits[-4:]}"


def _otp_fingerprint(otp: str) -> str:
    digest = hashlib.sha256(otp.encode()).hexdigest()
    return digest[:12]


def _masked_otp(otp: str) -> str:
    if len(otp) <= 2:
        return "*" * len(otp)
    return f"{otp[0]}***{otp[-1]}"


def send_otp(phone: str, otp: str, username: str = "") -> tuple[bool, str]:
    """
    Send OTP via SMS using Twilio.
    Returns (success: bool, message: str)
    """
    if not TWILIO_ENABLED:
        # Fallback: log de baixa sensibilidade (sem OTP completo)
        masked_phone = _mask_phone(phone)
        otp_hash = _otp_fingerprint(otp)
        msg = (
            f"[OTP-LOG] user={username or '-'} phone={masked_phone}"
            f" otp_hash={otp_hash} masked={_masked_otp(otp)}"
        )
        logger.warning(msg)
        return False, "SMS desativado; contate o suporte para verificação manual."

    try:
        from twilio.rest import Client  # type: ignore[import-not-found]

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        body_text = f"Seu código OTP para Jerr_BIG-DATE: {otp} (válido por 5 minutos)"
        message = client.messages.create(
            body=body_text, from_=TWILIO_FROM_NUMBER, to=phone
        )
        logger.info(f"SMS enviado para {phone}: SID={message.sid}")
        return True, f"OTP enviado para {phone}"
    except Exception as e:
        logger.error(f"Erro ao enviar SMS: {e}")
        masked_phone = _mask_phone(phone)
        otp_hash = _otp_fingerprint(otp)
        msg = (
            f"[OTP-LOG-FALLBACK] user={username or '-'} phone={masked_phone}"
            f" otp_hash={otp_hash} masked={_masked_otp(otp)} error={e}"
        )
        logger.warning(msg)
        return False, "SMS falhou; suporte notificado (OTP não persistido)."
