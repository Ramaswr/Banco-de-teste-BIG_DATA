"""
Streamlit app para upload dos CSVs e execução do ETL.
- Permite upload local de dois arquivos (produto e data)
- Mostra previews, tabelas agregadas e gráficos simples
- Permite baixar os CSVs resultantes
"""

from typing import Any, Callable, Optional, Sequence, Tuple, cast

MATRIX_BG_URL = "https://copilot.microsoft.com/shares/dkK4eArDkauRtywfQq3VW"


try:
    import importlib
    import importlib.util
    import sys
    import types

    # Se pandas não estiver instalado, insere um stub mínimo em sys.modules
    if importlib.util.find_spec("pandas") is None:
        mod = types.ModuleType("pandas")

        def _missing(*args: Any, **kwargs: Any) -> None:
            raise ModuleNotFoundError(
                "pandas não encontrado. Instale via 'pip install pandas' para executar o ETL."
            )

        # funções/objetos usados no app -> lançam erro informativo ao serem chamados
        setattr(mod, "read_csv", _missing)
        setattr(mod, "DataFrame", type("DataFrameStub", (), {}))  # placeholder leve

        def _getattr(_: str) -> Any:
            return _missing()

        setattr(mod, "__getattr__", _getattr)
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
        def __enter__(self) -> "_Column":
            return self

        def __exit__(
            self,
            exc_type: Optional[type[BaseException]] = None,
            exc: Optional[BaseException] = None,
            tb: Optional[Any] = None,
        ) -> bool:
            return False

    class _Stub:
        def set_page_config(self, *args: Any, **kwargs: Any) -> None:
            pass

        def title(self, *args: Any, **kwargs: Any) -> None:
            pass

        def markdown(self, *args: Any, **kwargs: Any) -> None:
            pass

        def columns(self, n: int) -> Tuple[_Column, ...]:
            return tuple(_Column() for _ in range(n))

        def file_uploader(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def selectbox(
            self,
            label: str,
            options: Sequence[Any],
            index: int = 0,
            key: Optional[str] = None,
        ) -> Any:
            try:
                return options[index]
            except Exception:
                return options[0] if options else None

        def button(self, *args: Any, **kwargs: Any) -> bool:
            return False

        def warning(self, *args: Any, **kwargs: Any) -> None:
            pass

        def info(self, *args: Any, **kwargs: Any) -> None:
            pass

        def subheader(self, *args: Any, **kwargs: Any) -> None:
            pass

        def dataframe(self, *args: Any, **kwargs: Any) -> None:
            pass

        def success(self, *args: Any, **kwargs: Any) -> None:
            pass

        def download_button(self, *args: Any, **kwargs: Any) -> None:
            pass

        def error(self, *args: Any, **kwargs: Any) -> None:
            pass

    st = _Stub()

try:
    import importlib

    try:
        pd = importlib.import_module("pandas")
    except Exception:
        pd = None

    try:
        import etl as etl_module
        etl_module = cast(Any, etl_module)

        AggregateFn = Callable[..., Tuple[list[Any], dict[str, Any]]]
        GenericFn = Callable[..., Any]

        aggregate_and_save = cast(AggregateFn, etl_module.aggregate_and_save)
        clean_date_df = cast(GenericFn, etl_module.clean_date_df)
        clean_product_df = cast(GenericFn, etl_module.clean_product_df)
        read_sales_csv = cast(GenericFn, etl_module.read_sales_csv)
    except Exception:
        # Minimal fallbacks so the app can be analyzed/inspected without the etl module.
        def read_sales_csv(file_obj: Any, sep: str = ",") -> Any:
            if pd is None:
                raise ModuleNotFoundError(
                    "pandas não encontrado. Instale via 'pip install pandas' para executar o ETL."
                )
            return pd.read_csv(file_obj, sep=sep)

        def run_etl(*args: Any, **kwargs: Any) -> Any:
            raise ModuleNotFoundError("módulo etl não encontrado")

        def clean_product_df(df: Any) -> Any:
            return df

        def clean_date_df(df: Any) -> Any:
            return df

        def aggregate_and_save(
            df_prod: Any = None,
            df_date: Any = None,
            output_folder: str = "streamlit_output",
            save_prefix: str = "",
        ) -> Tuple[list[str], dict[str, Any]]:
            # Retorna estrutura vazia compatível com o restante do app
            return [], {}

except Exception:
    # Em caso de erro inesperado, garantir que variáveis existam
    pd = None

    def read_sales_csv(file_obj: Any, sep: str = ",") -> Any:
        raise ModuleNotFoundError("pandas não disponível")

    def run_etl(*args: Any, **kwargs: Any) -> Any:
        raise ModuleNotFoundError("etl não disponível")

    def clean_product_df(df: Any) -> Any:
        return df

    def clean_date_df(df: Any) -> Any:
        return df

    def aggregate_and_save(
        df_prod: Any = None,
        df_date: Any = None,
        output_folder: str = "streamlit_output",
        save_prefix: str = "",
    ) -> Tuple[list[str], dict[str, Any]]:
        return [], {}


st.set_page_config(page_title="ETL Vendas - Análise", layout="wide")

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url('{MATRIX_BG_URL}');
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
        color: #d4ffd4;
    }}
    .css-1d391kg, .block-container {{
        background: rgba(0, 0, 0, 0.75);
        border-radius: 12px;
        padding: 32px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

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
                prod_df_raw = read_sales_csv(prod_file, sep=sep_prod)
                prod_df = clean_product_df(prod_df_raw)
                st.subheader("Preview - produto (limpo)")
                st.dataframe(prod_df.head(50))
            if date_file:
                date_df_raw = read_sales_csv(date_file, sep=sep_date)
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
