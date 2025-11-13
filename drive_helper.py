"""Placeholder helpers para integração com Google Drive (OAuth flows devem ser configurados pelo usuário).
Este módulo contém placeholders e exemplos de como autenticar e enviar arquivos para o Drive.
Não contém credenciais; configure em `.secrets/drive.env`.
"""

# Placeholder: use google-auth and googleapiclient for implementação real
# pip install google-auth google-auth-oauthlib google-api-python-client


def upload_file_to_drive(file_path, folder_id=None, creds=None):
    """Placeholder: faça upload usando as credenciais OAuth e retorne file id."""
    raise NotImplementedError(
        "Configure Google Drive API e implemente upload com googleapiclient"
    )
