"""Ferramentas auxiliares para validar URLs e extrair arquivos ZIP com segurança."""

from __future__ import annotations

import hashlib
import io
import ipaddress
from pathlib import Path, PurePosixPath
from typing import Dict, List
from urllib.parse import urlparse
import zipfile

MAX_ZIP_BYTES = 12 * 1024 * 1024  # 12 MB limite lógico
MAX_MEMBER_BYTES = 4 * 1024 * 1024  # 4 MB por arquivo individual
ALLOWED_TEXT_SUFFIXES = {".txt", ".csv", ".json", ".log", ".md"}
BLOCKED_TLDS = {".ru", ".cn", ".su", ".zip", ".mov"}
SUSPICIOUS_KEYWORDS = {"login", "bank", "verify", "credential", "torrent"}


def analyze_url(target_url: str) -> Dict[str, object]:
    """Retorna um relatório simples de veracidade para um link fornecido."""
    url = target_url.strip()
    parsed = urlparse(url)
    reasons: List[str] = []
    safe = True

    if parsed.scheme not in {"http", "https"}:
        safe = False
        reasons.append("Esquema não suportado (use http/https).")

    if not parsed.netloc:
        safe = False
        reasons.append("Domínio vazio ou inválido.")

    if "@" in parsed.netloc:
        safe = False
        reasons.append("Credenciais embutidas no domínio são proibidas.")

    hostname = parsed.hostname or ""
    if hostname:
        tld = "." + hostname.split(".")[-1]
        if tld.lower() in BLOCKED_TLDS:
            safe = False
            reasons.append(f"TLD bloqueado: {tld}")
        if any(keyword in hostname.lower() for keyword in SUSPICIOUS_KEYWORDS):
            safe = False
            reasons.append("Domínio contém palavras associadas a phishing.")
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                safe = False
                reasons.append("IP não roteável detectado (rede interna/loopback).")
        except ValueError:
            pass

    if parsed.path and any(segment.startswith("..") for segment in parsed.path.split("/")):
        safe = False
        reasons.append("Caminho contém tentativa de directory traversal.")

    digest = hashlib.sha256(url.encode("utf-8", errors="ignore")).hexdigest()[:16]

    return {
        "input": url,
        "safe": safe,
        "reasons": reasons or ["Sem indicadores críticos; continue monitorando."],
        "hostname": hostname,
        "hash": digest,
    }


def _normalize_member_path(root: Path, name: str) -> Path:
    member = PurePosixPath(name)
    normalized = root
    for part in member.parts:
        if part in {"..", ""}:
            continue
        normalized = normalized / part
    return normalized


def safe_extract_zip(data: bytes, dest_dir: Path) -> List[Dict[str, object]]:
    """Extrai arquivos de forma segura e retorna metadados e prévias."""
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("ZIP excede limite de 12 MB.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        import os

        os.chmod(dest_dir, 0o700)
    except Exception:
        pass

    entries: List[Dict[str, object]] = []

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if member.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"Arquivo interno muito grande: {member.filename}")
            target_path = _normalize_member_path(dest_dir, member.filename)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_root = dest_dir.resolve()
            resolved_target = target_path.resolve()
            if not str(resolved_target).startswith(str(resolved_root)):
                raise ValueError("Entrada ZIP tenta escapar do diretório destino.")
            suffix = target_path.suffix.lower()
            with archive.open(member, "r") as source, open(target_path, "wb") as dst:
                content = source.read()
                dst.write(content)
            preview = ""
            if suffix in ALLOWED_TEXT_SUFFIXES:
                try:
                    preview = content[:2048].decode("utf-8", errors="replace")
                except Exception:
                    preview = "[Texto não decodificável em UTF-8]"
            entries.append(
                {
                    "name": member.filename,
                    "bytes": member.file_size,
                    "path": str(target_path),
                    "allowed": suffix in ALLOWED_TEXT_SUFFIXES,
                    "preview": preview,
                }
            )

    return entries