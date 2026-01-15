"""
Streamlit app para upload dos CSVs e execução do ETL.
- Permite upload local de dois arquivos (produto e data)
- Mostra previews, tabelas agregadas e gráficos simples
- Permite baixar os CSVs resultantes
"""

import importlib

try:
    import importlib.util
    import sys
    import types
    from typing import Any, Callable, cast

    # Se pandas não estiver instalado, insere um stub mínimo em sys.modules
    if importlib.util.find_spec("pandas") is None:
        mod: Any = types.ModuleType("pandas")

        def _missing(*a, **k):
            raise ModuleNotFoundError(
                "pandas não encontrado. Instale via 'pip install pandas' para executar o ETL."
            )

        # funções/objetos usados no app -> lançam erro informativo ao serem chamados
        setattr(mod, "read_csv", _missing)
        setattr(mod, "DataFrame", type("DataFrameStub", (), {}))  # placeholder leve

        def __getattr__(name):
            raise ModuleNotFoundError(
                "pandas não encontrado. Instale via 'pip install pandas' para executar o ETL."
            )

        setattr(mod, "__getattr__", __getattr__)
        sys.modules["pandas"] = mod

    # Importa streamlit (se não existir, gera exceção para cair no except e usar o stub de UI)
    if importlib.util.find_spec("streamlit") is None:
        raise ModuleNotFoundError(
            "streamlit não encontrado. Instale via 'pip install streamlit' ou execute o app em um ambiente que tenha streamlit."
        )

    st = importlib.import_module("streamlit")
except Exception:
    # Streamlit não está disponível: fornecer um stub mínimo para permitir análise/execução não interativa.
    class _Column:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Stub:
        def set_page_config(self, *a, **k):
            pass

        def title(self, *a, **k):
            pass

        def markdown(self, *a, **k):
            pass

        def columns(self, n):
            return tuple(_Column() for _ in range(n))

        def file_uploader(self, *a, **k):
            return None

        def selectbox(self, label, options, index=0, key=None):
            try:
                return options[index]
            except Exception:
                return options[0] if options else None

        def button(self, *a, **k):
            return False

        def warning(self, *a, **k):
            pass

        def info(self, *a, **k):
            pass

        def subheader(self, *a, **k):
            pass

        def dataframe(self, *a, **k):
            pass

        def success(self, *a, **k):
            pass

        def download_button(self, *a, **k):
            # retornar False para compatibilidade com comportamento interativo esperado
            return False

        def error(self, *a, **k):
            pass

    st = _Stub()

try:
    # importlib já importado acima
 
    try:
        pd = importlib.import_module("pandas")
    except Exception:
        pd = None

    try:
        # Import the etl module itself and adapt read_sales_csv to a stable local signature.
        etl_mod = importlib.import_module("etl")
    except Exception:
        etl_mod = None

    if etl_mod is not None:
        import typing
        def _missing_aggregate_and_save(df_prod=None, df_date=None, output_folder="output", save_prefix=""):
            return {}, {}
        aggregate_and_save: typing.Callable[..., tuple[dict[typing.Any, typing.Any], dict[typing.Any, typing.Any]]] = typing.cast(
            typing.Callable[..., tuple[dict[typing.Any, typing.Any], dict[typing.Any, typing.Any]]],
            getattr(etl_mod, "aggregate_and_save", _missing_aggregate_and_save),
        )
        def _missing_clean(df):
            return df
        _clean_date_df = typing.cast(
            typing.Callable[..., typing.Any],
            getattr(etl_mod, "clean_date_df", _missing_clean),
        )
        _clean_product_df = typing.cast(
            typing.Callable[..., typing.Any],
            getattr(etl_mod, "clean_product_df", _missing_clean),
        )
        clean_date_df = _clean_date_df
        clean_product_df = _clean_product_df
        def _missing_run_etl(*a, **k):
            raise ModuleNotFoundError("run_etl não disponível no etl")
        run_etl_mod: typing.Callable[..., typing.Any] = typing.cast(
            typing.Callable[..., typing.Any],
            getattr(etl_mod, "run_etl", _missing_run_etl),
        )

        # If etl exposes a read_sales_csv, wrap it so the local function has the expected parameter names/signature.
        if hasattr(etl_mod, "read_sales_csv"):
            _etl_read = etl_mod.read_sales_csv

            def _read_sales_csv_wrapper(file_obj, sep=","):
                """Wrapper robusto: tenta passar file_obj direto; se falhar e for file-like,
                grava temporariamente e passa caminho para função do etl."""
                try:
                    # tenta usar diretamente (muitos leitores aceitam file-like ou path)
                    return _etl_read(file_obj, sep=sep)
                except Exception:
                    # se for file-like, tente salvar em arquivo temporário e chamar por caminho
                    if hasattr(file_obj, "read"):
                        import tempfile
                        import os

                        # leia bytes/str
                        data = file_obj.read()
                        if isinstance(data, str):
                            data_bytes = data.encode("utf-8")
                        else:
                            data_bytes = data

                        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
                        try:
                            tf.write(data_bytes)
                            tf.flush()
                            tf.close()
                            return _etl_read(tf.name, sep=sep)
                        finally:
                            try:
                                os.unlink(tf.name)
                            except Exception:
                                pass
                    # se não for possível recuperar, repropaga
                    raise

            # Expose a single stable name
            read_sales_csv = _read_sales_csv_wrapper
        else:
            # Fallback that uses pandas if available.
            def _read_sales_csv_fallback(file_obj, sep=","):
                if pd is None:
                    raise ModuleNotFoundError(
                        "pandas não encontrado. Instale via 'pip install pandas' para executar o ETL."
                    )
                # pandas.read_csv aceita file-like; garantir ponteiro no início
                try:
                    if hasattr(file_obj, "seek"):
                        file_obj.seek(0)
                except Exception:
                    pass
                return pd.read_csv(file_obj, sep=sep)
            # Expose a single stable name
            read_sales_csv = _read_sales_csv_fallback
    else:
        # Minimal fallbacks so the app can be analyzed/inspected without the etl module.
        def _read_sales_csv_minimal(file_obj, sep=","):
            if pd is None:
                raise ModuleNotFoundError(
                    "pandas não encontrado. Instale via 'pip install pandas' para executar o ETL."
                )
            return pd.read_csv(file_obj, sep=sep)

        read_sales_csv = _read_sales_csv_minimal

        def run_etl(*args, **kwargs):
            raise ModuleNotFoundError("módulo etl não encontrado")

        def _default_clean(df):
            return df

        clean_product_df = _default_clean
        clean_date_df = _default_clean

        def _aggregate_and_save_minimal(
            df_prod=None, df_date=None, output_folder="output", save_prefix=""
        ):
            # Retorna estrutura vazia compatível com o restante do app
            return {}, {}

        aggregate_and_save = _aggregate_and_save_minimal

except Exception:
    # Em caso de erro inesperado, garantir que variáveis existam
    pd = None

    def _read_sales_csv_error(file_obj, sep=","):
        raise ModuleNotFoundError("pandas não disponível")

    read_sales_csv = _read_sales_csv_error

    def run_etl(*args, **kwargs):
        raise ModuleNotFoundError("etl não disponível")

    def clean_product_df(df):
        return df

    def clean_date_df(df):
        return df

    def _aggregate_and_save_error(
        df_prod=None, df_date=None, output_folder="output", save_prefix=""
    ):
        return {}, {}

    aggregate_and_save = _aggregate_and_save_error


st.set_page_config(page_title="ETL Vendas - Análise", layout="wide")

st.title("ETL de Vendas — Upload e Análise")

st.markdown(
    "Carregue os arquivos CSV (produto e/ou data). O aplicativo limpará, agregará e permitirá baixar os resultados em CSV (padrão UTF-8, separador ,)."
)

col1, col2 = st.columns(2)

with col1:
    prod_file = st.file_uploader(
        "CSV - Vendas por Produto (Categoria, Codigo, Produto, Quantidade, Valor)",
        type=["csv", "txt"],
        key="prod",
    )
    sep_prod = st.selectbox("Separador (produto)", [";", ","], index=0, key="sep_prod")
with col2:
    date_file = st.file_uploader(
        "CSV - Vendas por Data", type=["csv", "txt"], key="date"
    )
    sep_date = st.selectbox("Separador (data)", [";", ","], index=0, key="sep_date")

output_folder = "streamlit_output"

if st.button("Rodar ETL"):
    if not prod_file and not date_file:
        st.warning("Faça upload de pelo menos um dos arquivos (produto ou data).")
    else:
        st.info("Processando...")
        prod_df = None
        date_df = None
        try:
            if prod_file:
                prod_df_raw = read_sales_csv(prod_file, sep=str(sep_prod))
                prod_df = clean_product_df(prod_df_raw)
                st.subheader("Preview - produto (limpo)")
                st.dataframe(prod_df.head(50))
            if date_file:
                date_df_raw = read_sales_csv(date_file, sep=str(sep_date))
                date_df = clean_date_df(date_df_raw)
                st.subheader("Preview - data (limpo)")
                st.dataframe(date_df.head(50))

            out_paths, reports = aggregate_and_save(
                df_prod=prod_df,
                df_date=date_df,
                output_folder=output_folder,
                save_prefix="",
            )

            st.success("ETL concluído. Resultados abaixo.")

            if "produto_agg" in reports:
                st.subheader("Top produtos por receita")
                st.dataframe(reports["produto_agg"].head(50))
                csv_buf = reports["produto_agg"].to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Baixar produto_agg.csv",
                    data=csv_buf,
                    file_name="produto_agg.csv",
                    mime="text/csv",
                )

            if "categoria_agg" in reports:
                st.subheader("Categorias por receita")
                st.dataframe(reports["categoria_agg"].head(50))
                csv_buf = reports["categoria_agg"].to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Baixar categoria_agg.csv",
                    data=csv_buf,
                    file_name="categoria_agg.csv",
                    mime="text/csv",
                )

            if "daily" in reports:
                st.subheader("Últimos registros diários (até 60)")
                st.dataframe(reports["daily"].tail(60))
                csv_buf = reports["daily"].to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Baixar daily.csv",
                    data=csv_buf,
                    file_name="daily.csv",
                    mime="text/csv",
                )

        except Exception as e:
            st.error(f"Erro durante o processamento: {e}")

st.markdown("---")
st.markdown(
    "Dica: se você tem seus arquivos no Google Drive, primeiro faça download para o seu computador e depois faça upload aqui para preservar privacidade e segurança."
)
