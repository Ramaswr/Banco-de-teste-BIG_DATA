"""Assistente textual local para descrever funcionalidades do app."""

from __future__ import annotations

from typing import Iterable, List


def build_virtual_assistant_answer(
    events: Iterable[str] | None = None,
    *,
    has_dataframe: bool,
    binary_enabled: bool,
    zip_entries: int,
) -> str:
    """Gera uma resposta textual simulando um assistente IA offline."""
    notes: List[str] = [
        "Sou o assistente IA local do painel BIG DATA e posso te lembrar como usar os recursos com segurança.",
        "Funcionalidades principais disponíveis agora:",
        "1. Upload e limpeza de CSV/Excel/Parquet, com prévias imediatas.",
        "2. Parser BIN exclusivo (QuantumBinaryParser) para admins.",
        "3. Scanner de links e extrator ZIP com inspeção anti-malware.",
    ]

    if has_dataframe:
        notes.append("- Já existe um dataset carregado; você pode gerar agregações ou baixar CSVs filtrados.")
    else:
        notes.append("- Nenhum dataset está ativo neste momento; faça upload para habilitar análises.")

    if binary_enabled:
        notes.append("- O modo BIN segue ativo, lembre-se de validar o layout `<IQIq32s>` antes do upload.")

    if zip_entries:
        notes.append(f"- {zip_entries} arquivos foram extraídos do último ZIP seguro.")

    evt_list = list(events or [])
    if evt_list:
        notes.append("Eventos de segurança recentes:")
        notes.extend(f"  • {evt}" for evt in evt_list[-5:])

    notes.append(
        "Dica: use o botão 'Rodar ETL' para consolidar tudo em `streamlit_output/` e compartilhe com sua equipe."
    )
    notes.append("Estou disponível apenas para leitura/guias; não executo ações por você.")
    return "\n".join(notes)
