"""
ETL standalone adapted from the provided Colab script.
- Reads product and date CSVs (local paths or file-like objects)
- Cleans and normalizes data
- Produces aggregated CSV outputs in an output folder
- Can be used as a CLI or imported by a web app
"""

import argparse
import os
from io import BytesIO

import pandas as pd


def read_sales_csv(
    path_or_buf, sep=";", encoding_candidates=("utf-8", "latin1", "cp1252")
):
    """Leia um CSV tentando várias codificações.
    path_or_buf pode ser um caminho (str) ou file-like (BytesIO / UploadedFile).
    Retorna DataFrame com colunas com strip nos nomes.
    """
    last_err = None
    # Se for buffer em bytes, precisamos tentar decodificá-lo para string antes de passar
    if hasattr(path_or_buf, "read") and not isinstance(path_or_buf, str):
        raw = path_or_buf.read()
        # reset pointer se possível
        try:
            path_or_buf.seek(0)
        except Exception:
            pass
        for enc in encoding_candidates:
            try:
                s = raw.decode(enc)
                df = pd.read_csv(BytesIO(s.encode("utf-8")), sep=sep)
                df.columns = [c.strip() for c in df.columns]
                return df
            except Exception as e:
                last_err = e
        if last_err is not None:
            raise last_err
        else:
            raise RuntimeError("Falha no ETL: erro não capturado detalhadamente.")
    else:
        for enc in encoding_candidates:
            try:
                df = pd.read_csv(path_or_buf, sep=sep, encoding=enc)
                df.columns = [c.strip() for c in df.columns]
                return df
            except Exception as e:
                last_err = e
        if last_err is not None:
            raise last_err
        else:
            raise RuntimeError("Falha no ETL: erro não capturado detalhadamente.")


def to_int_safe(x):
    if pd.isna(x):
        return 0
    s = str(x).strip().replace(".", "")
    s = "".join(ch for ch in s if ch.isdigit())
    return int(s) if s else 0


def to_float_safe(x):
    if pd.isna(x):
        return 0.0
    s = str(x).strip().replace(".", "").replace(",", ".")
    s2 = "".join(ch for ch in s if ch.isdigit() or ch == ".")
    try:
        return float(s2) if s2 else 0.0
    except Exception:
        return 0.0


def clean_product_df(df):
    expected = ["Categoria", "Codigo", "Produto", "Quantidade", "Valor"]
    if "Categoria" not in df.columns:
        if df.shape[1] >= 5:
            df = df.iloc[:, :5]
            df.columns = expected
        else:
            raise ValueError(
                "Formato do CSV de produto inesperado: colunas insuficientes."
            )
    df = df.rename(columns=lambda x: x.strip())
    df = df.dropna(how="all")
    if "Produto" in df.columns:
        df = df[~df["Produto"].astype(str).str.contains("Relat", na=False)]
    # Converter
    df["Quantidade"] = df["Quantidade"].apply(to_int_safe).astype(int)
    df["Valor"] = df["Valor"].apply(to_float_safe).astype(float)
    df["Categoria"] = df["Categoria"].fillna("SEM_CATEGORIA").astype(str)
    df["Produto"] = df["Produto"].astype(str).str.strip()
    df["Codigo"] = df["Codigo"].astype(str).str.strip()
    return df


def clean_date_df(df):
    df = df.dropna(how="all")
    date_col = next(
        (c for c in df.columns if "data" in c.lower() or "date" in c.lower()), None
    )
    qty_col = next((c for c in df.columns if "quant" in c.lower()), None)
    val_col = next(
        (
            c
            for c in df.columns
            if ("valor" in c.lower())
            or ("value" in c.lower())
            or ("preco" in c.lower())
        ),
        None,
    )
    if date_col is None and df.shape[1] >= 1:
        date_col = df.columns[0]
    if qty_col is None and df.shape[1] >= 2:
        qty_col = df.columns[-2]
    if val_col is None and df.shape[1] >= 2:
        val_col = df.columns[-1]
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
    df[qty_col] = df[qty_col].apply(to_int_safe).astype(int)
    df[val_col] = df[val_col].apply(to_float_safe).astype(float)
    df = df.rename(columns={date_col: "Data", qty_col: "Quantidade", val_col: "Valor"})
    if "Produto" not in df.columns:
        df["Produto"] = ""
    if "Categoria" not in df.columns:
        df["Categoria"] = "SEM_CATEGORIA"
    return df


def aggregate_and_save(
    df_prod=None, df_date=None, output_folder="output", save_prefix=""
):
    os.makedirs(output_folder, exist_ok=True)
    reports = {}
    if df_prod is not None:
        prod_agg = (
            df_prod.groupby(["Produto", "Codigo", "Categoria"], dropna=False)
            .agg(Quantidade_Total=("Quantidade", "sum"), Receita_Total=("Valor", "sum"))
            .reset_index()
            .sort_values(by="Receita_Total", ascending=False)
        )
        reports["produto_agg"] = prod_agg

        cat_agg = (
            df_prod.groupby("Categoria", dropna=False)
            .agg(Quantidade_Total=("Quantidade", "sum"), Receita_Total=("Valor", "sum"))
            .reset_index()
            .sort_values(by="Receita_Total", ascending=False)
        )
        reports["categoria_agg"] = cat_agg

    if df_date is not None:
        df_date = df_date.dropna(subset=["Data"])
        daily = (
            df_date.groupby("Data")
            .agg(Quantidade_Total=("Quantidade", "sum"), Receita_Total=("Valor", "sum"))
            .reset_index()
            .sort_values("Data")
        )
        if len(daily) > 60:
            daily_60 = daily.tail(60).reset_index(drop=True)
        else:
            daily_60 = daily.copy()
        reports["daily"] = daily_60

    # salvar
    out_paths = {}
    for name, df in reports.items():
        out_path = os.path.join(output_folder, f"{save_prefix}{name}.csv")
        df.to_csv(out_path, index=False, sep=",", encoding="utf-8")
        out_paths[name] = out_path
    return out_paths, reports


def run_etl(
    product_path=None,
    date_path=None,
    output_folder="output",
    sep=";",
    encoding_candidates=("utf-8", "latin1", "cp1252"),
):
    df_prod = None
    df_date = None
    if product_path:
        df_prod_raw = read_sales_csv(
            product_path, sep=sep, encoding_candidates=encoding_candidates
        )
        df_prod = clean_product_df(df_prod_raw)
    if date_path:
        df_date_raw = read_sales_csv(
            date_path, sep=sep, encoding_candidates=encoding_candidates
        )
        df_date = clean_date_df(df_date_raw)
    out_paths, reports = aggregate_and_save(
        df_prod=df_prod, df_date=df_date, output_folder=output_folder
    )
    return out_paths, reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ETL para vendas (produto + data) - gera CSVs agregados"
    )
    parser.add_argument(
        "--product",
        help="Caminho para CSV de produto (categoria, codigo, produto, quantidade, valor)",
    )
    parser.add_argument("--date", help="Caminho para CSV por data")
    parser.add_argument(
        "--output", default="output", help="Pasta de saída (será criada)"
    )
    parser.add_argument(
        "--sep", default=";", help="Separador dos CSVs de entrada (padrão: ; )"
    )
    args = parser.parse_args()

    out, reports = run_etl(
        product_path=args.product,
        date_path=args.date,
        output_folder=args.output,
        sep=args.sep,
    )
    print("Arquivos gerados:")
    for k, v in out.items():
        print("-", k, v)
