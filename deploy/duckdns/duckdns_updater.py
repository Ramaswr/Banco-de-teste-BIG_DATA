#!/usr/bin/env python3
"""DuckDNS updater moved out of app.py into deploy utilities."""
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Prefer project-level .secrets/duckdns.env, then fallback to home
PROJECT_ENV = os.path.join(os.getcwd(), ".secrets", "duckdns.env")
ENV_PATH = (
    PROJECT_ENV
    if os.path.exists(PROJECT_ENV)
    else os.path.expanduser("~/.secrets/duckdns.env")
)

DOMAINS = os.getenv("DUCKDNS_DOMAINS")
TOKEN = os.getenv("DUCKDNS_TOKEN")

if not (DOMAINS and TOKEN) and os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            if k == "DOMAIN" and not DOMAINS:
                DOMAINS = v.strip()
            if k == "TOKEN" and not TOKEN:
                TOKEN = v.strip()

if not (DOMAINS and TOKEN):
    raise SystemExit("DUCKDNS_DOMAINS e DUCKDNS_TOKEN não configurados.")

log_dir = os.path.expanduser("~/duckdns_py")
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "duck.log")

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=(500, 502, 503, 504))
session.mount("https://", HTTPAdapter(max_retries=retries))


def update_duckdns():
    url = f"https://www.duckdns.org/update?domains={DOMAINS}&token={TOKEN}"
    try:
        resp = session.get(url, timeout=10)
        body = resp.text.strip()
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        with open(log_path, "a") as log_file:
            log_file.write(f"{now} - {body} (status {resp.status_code})\\n")

        print(f"Update response: {body}")
        return body, resp.status_code
    except requests.RequestException as e:
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        with open(log_path, "a") as log_file:
            log_file.write(f"{now} - ERROR - {e}\\n")
        print(f"Erro na requisição: {e}")
        return None, None


if __name__ == "__main__":
    update_duckdns()
