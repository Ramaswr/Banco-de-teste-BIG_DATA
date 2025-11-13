"""Helpers para envio de alertas por e-mail (SMTP)."""

import os
import smtplib
from email.message import EmailMessage

ENV_PATH = os.path.expanduser(".secrets/email.env")


def _load_smtp_config():
    cfg = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def send_alert(subject: str, body: str, to_email: str):
    cfg = _load_smtp_config()
    host = cfg.get("SMTP_HOST")
    port = int(cfg.get("SMTP_PORT", "587"))
    user = cfg.get("SMTP_USER")
    password = cfg.get("SMTP_PASS")
    from_addr = cfg.get("FROM_EMAIL", user)

    if not host or not user or not password or not to_email:
        # Configuração de email não encontrada — não falhar, apenas logar
        print("SMTP não configurado. Skipping send_alert()")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            s.login(user, password)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"Falha ao enviar alerta por e-mail: {e}")
        return False
