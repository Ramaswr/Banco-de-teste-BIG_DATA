"""
OCR and PDF helpers: image -> text, pdf -> csv using pytesseract and pdfplumber.
"""
from PIL import Image
import pytesseract
import pdfplumber
import io
import csv
import os
import time
import pandas as pd


def image_to_text(image_file):
    """Recebe um file-like (BytesIO) ou caminho e retorna texto extraído."""
    if hasattr(image_file, 'read'):
        image_file.seek(0)
        img = Image.open(image_file).convert('RGB')
    else:
        img = Image.open(image_file).convert('RGB')
    text = pytesseract.image_to_string(img, lang='por+eng')
    return text


def pdf_to_tables_csv(pdf_file, out_dir, prefix='pdf'):
    """Extrai tabelas de PDF e salva CSVs em out_dir. Retorna lista de caminhos."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    if hasattr(pdf_file, 'read'):
        # pdfplumber aceita path ou file-like via opener
        pdf_bytes = pdf_file.read()
        pdf_stream = io.BytesIO(pdf_bytes)
        pdf = pdfplumber.open(pdf_stream)
    else:
        pdf = pdfplumber.open(pdf_file)

    for i, page in enumerate(pdf.pages, start=1):
        tables = page.extract_tables()
        for j, table in enumerate(tables, start=1):
            if not table:
                continue
            df = pd.DataFrame(table[1:], columns=table[0]) if len(table) > 1 else pd.DataFrame(table)
            out_path = os.path.join(out_dir, f"{prefix}_p{i}_t{j}_{int(time.time())}.csv")
            df.to_csv(out_path, index=False)
            paths.append(out_path)
    pdf.close()
    return paths


def save_text_as_csv_for_user(username, text, out_dir='secure_uploads'):
    os.makedirs(out_dir, exist_ok=True)
    user_dir = os.path.join(out_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    fname = f"ocr_{int(time.time())}.csv"
    path = os.path.join(user_dir, fname)
    # salvar texto em uma coluna
    import pandas as pd
    df = pd.DataFrame([{'text': text}])
    df.to_csv(path, index=False)
    return path
