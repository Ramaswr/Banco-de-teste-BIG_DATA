"""Helpers para envio de e-mails de verificação (usa utils.alerts.send_alert).

This module provides a simple wrapper to compose verification emails.
"""
from typing import Optional
from urllib.parse import urlencode
import os
from utils.alerts import send_alert


def send_verification_email(to_email: str, username: str, token: str, site_base: Optional[str] = None) -> bool:
    subject = "Verificação de e-mail - Jerr_BIG-DATE"
    if site_base:
        # token delivered as query param
        url = f"{site_base.rstrip('/')}/?verify_email={token}"
        body = f"Olá {username},\n\nClique no link abaixo para verificar seu e-mail (expira em ~1 hora):\n{url}\n\nSe você não solicitou, ignore esta mensagem."
    else:
        body = f"Olá {username},\n\nUse este código para verificar seu e-mail: {token}\n\nSe você não solicitou, ignore esta mensagem."
    return send_alert(subject, body, to_email)


def send_phone_otp(phone: str, username: str, otp: str) -> bool:
    # Placeholder: no SMS provider configured. For now log to stdout.
    print(f"[OTP] user={username} phone={phone} otp={otp}")
    return False
