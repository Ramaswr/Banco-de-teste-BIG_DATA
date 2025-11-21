#!/usr/bin/env python3
"""
Script para criar uma Release no GitHub via API REST.
Uso: python create_release.py <token> <owner> <repo> <tag> <zip_file> [release_notes.md]
Exemplo: python create_release.py ghp_xxxxx Ramaswr Banco-de-teste-BIG_DATA v1.1 zip_Jerr.js RELEASE_NOTES.md
"""

import os
import sys

import requests


def _load_body(tag: str, notes_path: str | None) -> str:
    if notes_path and os.path.exists(notes_path):
        with open(notes_path, "r", encoding="utf-8") as handle:
            notes = handle.read()
        return notes

    return f"""# {tag} — Banco de teste BIG_DATA

Pacote para análises seguras e execuções da plataforma BIG DATA.

## Instruções rápidas
```bash
unzip zip_Jerr.js
cd z_ip
./bootstrap.sh
source .venv/bin/activate
streamlit run app.py
```

Consulte RELEASE_NOTES.md para o changelog completo.
"""


def create_release(
    token: str,
    owner: str,
    repo: str,
    tag: str,
    zip_file: str,
    notes_path: str | None = None,
) -> None:
    """Criar release no GitHub com arquivo anexado."""

    if not os.path.exists(zip_file):
        print(f"Erro: arquivo '{zip_file}' não encontrado.")
        sys.exit(1)

    # URL da API
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases"

    # Headers com autenticação
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Dados da release
    release_data: dict[str, str | bool] = {
        "tag_name": tag,
        "name": f"{tag} — Banco de teste BIG_DATA",
        "body": _load_body(tag, notes_path),
        "draft": False,
        "prerelease": False,
    }

    print(f"Criando release '{tag}' em {owner}/{repo}...")

    # Criar release
    try:
        response = requests.post(api_url, headers=headers, json=release_data)
        if response.status_code != 201:
            print(f"Erro ao criar release: {response.status_code}")
            print(f"Resposta: {response.text}")
            sys.exit(1)

        release = response.json()
        release_id = release["id"]
        upload_url = release["upload_url"].split("{")[0]  # Remove template
        print(f"✓ Release criada com ID {release_id}")

    except Exception as e:
        print(f"Erro ao criar release: {e}")
        sys.exit(1)

    # Upload do arquivo
    print(f"Anexando arquivo '{zip_file}'...")

    with open(zip_file, "rb") as f:
        file_data = f.read()

    upload_headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream",
    }

    try:
        response = requests.post(
            f"{upload_url}?name={os.path.basename(zip_file)}",
            headers=upload_headers,
            data=file_data,
        )

        if response.status_code not in [200, 201]:
            print(f"Erro ao fazer upload: {response.status_code}")
            print(f"Resposta: {response.text}")
            sys.exit(1)

        print(f"✓ Arquivo '{zip_file}' anexado com sucesso")

    except Exception as e:
        print(f"Erro ao fazer upload: {e}")
        sys.exit(1)

    # Resultado final
    release_url = f"https://github.com/{owner}/{repo}/releases/tag/{tag}"
    print("\n✅ Release publicada com sucesso!")
    print(f"URL: {release_url}")
    print(f"Download: {release_url}/download/{os.path.basename(zip_file)}")


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    token = sys.argv[1]
    owner = sys.argv[2]
    repo = sys.argv[3]
    tag = sys.argv[4]
    zip_file = sys.argv[5]
    notes_file = sys.argv[6] if len(sys.argv) >= 7 else None

    create_release(token, owner, repo, tag, zip_file, notes_file)
