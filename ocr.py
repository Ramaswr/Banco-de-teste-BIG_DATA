"""
OCR and PDF helpers: image -> text, pdf -> csv using pytesseract and pdfplumber.
"""

import io
import os
import time
import importlib

import pandas as pd
try:
    pdfplumber = importlib.import_module("pdfplumber")
    _PDFPLUMBER_AVAILABLE = True
except Exception:
    pdfplumber = None
    _PDFPLUMBER_AVAILABLE = False

try:
    pytesseract = importlib.import_module("pytesseract")
    _PYTESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None
    _PYTESSERACT_AVAILABLE = False

from PIL import Image
from typing import Any, cast


def image_to_text(image_file):
    """Recebe um file-like (BytesIO) ou caminho e retorna texto extraído."""
    if not _PYTESSERACT_AVAILABLE:
        raise ModuleNotFoundError(
            "pytesseract não está instalado no ambiente. Instale com: "
            "python -m pip install pytesseract pillow e instale o binário do tesseract: "
            "sudo apt install tesseract-ocr"
        )
    if hasattr(image_file, "read"):
        image_file.seek(0)
        img = Image.open(image_file).convert("RGB")
    else:
        img = Image.open(image_file).convert("RGB")
    # cast to Any so static type checkers know pytesseract implements image_to_string
    pyt = cast(Any, pytesseract)
    text = pyt.image_to_string(img, lang="por+eng")
    return text


def pdf_to_tables_csv(pdf_file, out_dir, prefix="pdf"):
    """Extrai tabelas de PDF e salva CSVs em out_dir. Retorna lista de caminhos."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    if not _PDFPLUMBER_AVAILABLE:
        raise ModuleNotFoundError(
            "pdfplumber não está instalado. Instale com: pip install pdfplumber"
        )

    pdf_stream = io.BytesIO(pdf_file.read()) if hasattr(pdf_file, "read") else pdf_file

    with cast(Any, pdfplumber).open(pdf_stream) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            for j, table in enumerate(tables, start=1):
                if not table:
                    continue
                df = (
                    pd.DataFrame(table[1:], columns=table[0])
                    if len(table) > 1
                    else pd.DataFrame(table)
                )
                out_path = os.path.join(
                    out_dir, f"{prefix}_p{i}_t{j}_{int(time.time())}.csv"
                )
                df.to_csv(out_path, index=False)
                paths.append(out_path)
    return paths


def save_text_as_csv_for_user(username, text, out_dir="secure_uploads"):
    os.makedirs(out_dir, exist_ok=True)
    user_dir = os.path.join(out_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    fname = f"ocr_{int(time.time())}.csv"
    path = os.path.join(user_dir, fname)
    df = pd.DataFrame([{"text": text}])
    df.to_csv(path, index=False)
    return path
