"""
Streamlit app robusto com painel de controle para leitura de múltiplos formatos.
- Suporta CSV, Excel (.xlsx, .xls), e binários (Parquet)
- Interface estilo dashboard com botões iniciar/desligar
- Preview de dados, limpeza, agregação e download
- Análise robusta com Pandas
- SEGURANÇA: Autenticação, validação de arquivos, rate limiting
"""

import importlib
import io
import os
import secrets

import users as user_mgmt
from ocr import image_to_text, pdf_to_tables_csv, save_text_as_csv_for_user
from security import (
    credentials,
    file_validator,
    rate_limiter,
    session_manager,
    setup_secure_environment,
)
from utils.mailer import send_phone_otp, send_verification_email
from utils.password_strength import (
    check_password_strength,
    get_strength_color,
    get_strength_label,
)

# Importar dependências
try:
    st = importlib.import_module("streamlit")
except Exception:
    raise ModuleNotFoundError(
        "streamlit não encontrado. Instale: pip install streamlit"
    )

try:
    pd = importlib.import_module("pandas")
except Exception:
    raise ModuleNotFoundError("pandas não encontrado. Instale: pip install pandas")

# numpy é opcional e não é usado diretamente neste arquivo; definir como None evita erros
np = None

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

try:
    from etl import aggregate_and_save, clean_date_df, clean_product_df, read_sales_csv
except Exception:
    # Fallbacks
    def read_sales_csv(file_obj, sep=","):
        return pd.read_csv(file_obj, sep=sep)

    def clean_product_df(df):
        return df

    def clean_date_df(df):
        return df

    def aggregate_and_save(
        df_prod=None, df_date=None, output_folder="streamlit_output", save_prefix=""
    ):
        return [], {}


# ==================== CONFIGURAÇÃO ====================
st.set_page_config(
    page_title="📊 Jerr_BIG-DATE", layout="wide", initial_sidebar_state="expanded"
)

# Configurar ambiente seguro na primeira execução
if "setup_done" not in st.session_state:
    setup_secure_environment()
    st.session_state.setup_done = True

# CSS customizado para aparência Dark
st.markdown(
    """
<style>
  :root { --bg:#0b1220; --card:#0f1724; --muted:#94a3b8; --accent:#7c3aed; --ok:#22c55e; }
  .main .block-container{background-color:var(--bg); color:#e6eef8}
  .dashboard-header{ background: linear-gradient(135deg,#0f1724 0%, #0b1220 100%); color: #e6eef8; padding:1.5rem; border-radius:8px; }
  .control-panel{ background:var(--card); color:#dbeafe; padding:1rem; border-radius:8px; border-left:4px solid var(--accent); }
  .status-badge{ display:inline-block; padding:0.4rem 0.8rem; border-radius:16px; font-weight:600 }
  .status-active{ background:var(--ok); color:#032103 }
  .status-inactive{ background:#ef4444; color:#2b0505 }
  .security-banner{ background:#071029; border-left:4px solid #f59e0b; padding:0.8rem; border-radius:6px; margin-bottom:1rem }
  /* small top-right supporter badge */
  .supporter-badge{ position:relative; font-size:0.9rem; color:#a3e635; font-weight:600 }
</style>
""",
    unsafe_allow_html=True,
)


# ==================== AUTENTICAÇÃO ====================
def login_page():
    """Página de login segura."""
    st.markdown(
        """
    <div class='dashboard-header'>
        <h1>🔐 Jerr_BIG-DATE - Login</h1>
        <p>Acesso seguro e protegido ao Jerr_BIG-DATE</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Credenciais de Acesso")

        username = st.text_input("👤 Usuário", key="login_user")
        password = st.text_input("🔑 Senha", type="password", key="login_pass")

        # Rate limiting por IP (usando session como proxy)
        session_id = st.session_state.get("session_id", "guest")
        if not rate_limiter.is_allowed(session_id):
            st.error("❌ Muitas tentativas de login. Tente novamente mais tarde.")
            st.stop()

        if st.button("🔓 Entrar", use_container_width=True, key="btn_login"):
            if username and password:
                if credentials.authenticate(username, password):
                    # Criar sessão
                    session_id = session_manager.create_session(username)
                    st.session_state.session_id = session_id
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"Sejam bem-vindo a Jerr_BIG-DATE, {username}!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos")
                    rate_limiter.is_allowed(session_id)  # Contar tentativa falha
            else:
                st.warning("⚠️ Preencha usuário e senha")

    # ---------- Formulário de Registro (simples, amigável) ----------
    with st.expander("Criar nova conta", expanded=False):
        st.info(
            "Crie uma conta local — os dados ficam armazenados localmente em `.secrets/users.db`"
        )
        r_username = st.text_input("Nome de usuário", key="reg_user")
        r_name = st.text_input("Nome completo (opcional)", key="reg_name")
        r_email = st.text_input("Email (opcional)", key="reg_email")
        r_phone = st.text_input("Telefone (opcional)", key="reg_phone")
        r_password = st.text_input("Senha", type="password", key="reg_pass")

        # Password strength meter
        if r_password:
            strength = check_password_strength(
                r_password,
                user_inputs=[r_username, r_email] if r_username or r_email else [],
            )
            score = strength["score"]
            label = get_strength_label(score)
            color = get_strength_color(score)
            st.markdown(
                f"<p style='color:{color};font-weight:bold;'>Força: {label}</p>",
                unsafe_allow_html=True,
            )
            if strength["warning"]:
                st.warning(f"⚠️ {strength['warning']}")
            if strength["feedback"]:
                st.info(f"Sugestões: {', '.join(strength['feedback'][:2])}")

        r_password2 = st.text_input(
            "Confirme a senha", type="password", key="reg_pass2"
        )
        r_role = st.selectbox(
            "Tipo de conta", ["user", "super_admin"], index=0, key="reg_role"
        )
        if st.button("Criar conta", key="btn_create_account"):
            if not r_username or not r_password:
                st.error("Usuário e senha são obrigatórios")
            elif r_password != r_password2:
                st.error("As senhas não coincidem")
            else:
                try:
                    user_mgmt.create_user(
                        username=r_username,
                        password=r_password,
                        name=r_name or None,
                        email=r_email or None,
                        phone=r_phone or None,
                        role=r_role,
                    )
                    # send verification email if provided
                    if r_email:
                        token = user_mgmt.create_verification_token(
                            r_username, token_type="email", ttl_seconds=3600
                        )
                        sent = send_verification_email(
                            r_email, r_username, token, site_base=None
                        )
                        if sent:
                            st.success(
                                "Conta criada. Enviamos um e-mail de verificação."
                            )
                        else:
                            st.warning(
                                "Conta criada. Não foi possível enviar e-mail de verificação (SMTP não configurado)."
                            )
                    else:
                        st.success("Conta criada com sucesso! Faça login.")

                    # phone OTP flow (optional)
                    if r_phone:
                        otp = str(secrets.randbelow(10**6)).zfill(6)
                        user_mgmt.create_verification_token(
                            r_username, token_type="phone", ttl_seconds=300, token=otp
                        )
                        sms_sent = send_phone_otp(r_phone, r_username, otp)
                        if sms_sent:
                            st.info("OTP enviado por SMS para verificação de telefone.")
                        else:
                            st.info(
                                f"OTP (teste): {otp} — em produção integre um provedor SMS para envio real."
                            )
                except Exception as e:
                    st.error(f"Erro ao criar conta: {e}")

    # ---------- Verificação de token (email / phone) ----------
    with st.expander("Confirmar conta / Verificar token", expanded=False):
        st.write("Cole o código de verificação recebido por e-mail ou SMS.")
        v_token = st.text_input("Código / Token", key="verify_token")
        v_type = st.selectbox(
            "Tipo de token", ["email", "phone"], index=0, key="verify_type"
        )
        if st.button("Verificar", key="btn_verify_token"):
            if not v_token:
                st.error("Insira o token recebido.")
            else:
                ok = user_mgmt.verify_and_consume_token(
                    v_token.strip(), token_type=v_type
                )
                if ok:
                    st.success("Verificação concluída com sucesso!")
                else:
                    st.error("Token inválido ou expirado.")

    st.markdown("---")
    st.info(
        "**Demo Credentials:**\n- Username: `admin` | Password: `admin123`\n- Username: `usuario` | Password: `senha123`\n\n⚠️ **ALTERE ESTAS CREDENCIAIS EM PRODUÇÃO!**"
    )
    st.markdown("🔒 Todos os acessos são registrados em `security.log`")


# ==================== ESTADO DO APP ====================
if "app_active" not in st.session_state:
    st.session_state.app_active = True
if "current_df" not in st.session_state:
    st.session_state.current_df = None
if "file_info" not in st.session_state:
    st.session_state.file_info = {}
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None

# ==================== VERIFICAÇÃO DE AUTENTICAÇÃO ====================
if not st.session_state.authenticated:
    login_page()
    st.stop()

# Validar sessão
session_id = st.session_state.session_id
username = session_manager.validate_session(session_id)
if not username:
    st.error("❌ Sessão expirada. Faça login novamente.")
    st.session_state.authenticated = False
    st.rerun()

# ==================== CABEÇALHO ====================
st.markdown(
    """
<div class='dashboard-header'>
    <h1>📊 Painel de Análise de Dados</h1>
    <p>Ferramenta robusta para leitura, limpeza e análise de arquivos (CSV, Excel, Parquet)</p>
</div>
""",
    unsafe_allow_html=True,
)

# Mostrar usuário logado
col_user, col_logout = st.columns([9, 1])
with col_user:
    st.markdown(f"👤 **Usuário:** {st.session_state.username}")
    # Mostrar badge de apoiador PIX no canto superior do perfil (se configurado)
    try:
        meta = credentials.get_user_metadata(st.session_state.username)
        pix_key = meta.get("pix_key")
        role = meta.get("role")
    except Exception:
        pix_key = None
        role = "user"
    if pix_key:
        if pix_key == "71281802140":
            st.markdown(
                "<div class='supporter-badge'>🔑 Apoiador confirmado (PIX)</div>",
                unsafe_allow_html=True,
            )
    # armazenar role em session_state para uso posterior
    st.session_state.user_role = role
with col_logout:
    if st.button("🚪 Sair", key="btn_logout", use_container_width=True):
        session_manager.destroy_session(session_id)
        st.session_state.authenticated = False
        st.session_state.username = None
        st.success("Logout realizado com sucesso!")
        st.rerun()

st.markdown(
    """
<div class='security-banner'>
    <strong>🔒 Segurança Ativa:</strong> Autenticação habilitada | Validação de arquivos | Rate limiting | Logging de acessos
</div>
""",
    unsafe_allow_html=True,
)

# ==================== PAINEL DE CONTROLE ====================
st.markdown("<div class='control-panel'>", unsafe_allow_html=True)

col_status, col_btn_start, col_btn_stop = st.columns([2, 1, 1])

with col_status:
    status_class = "status-active" if st.session_state.app_active else "status-inactive"
    status_text = "🟢 ATIVO" if st.session_state.app_active else "🔴 INATIVO"
    st.markdown(
        f"<span class='status-badge {status_class}'>{status_text}</span>",
        unsafe_allow_html=True,
    )

with col_btn_start:
    if st.button("▶️ INICIAR", key="btn_start", use_container_width=True):
        st.session_state.app_active = True
        st.success("✅ Aplicação iniciada!")
        st.rerun()

with col_btn_stop:
    if st.button("⏹️ DESLIGAR", key="btn_stop", use_container_width=True):
        st.session_state.app_active = False
        st.warning("🛑 Aplicação desligada!")
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ==================== VERIFICAR SE ESTÁ ATIVO ====================
if not st.session_state.app_active:
    st.warning('⚠️ A aplicação está desligada. Clique em "INICIAR" para continuar.')
    st.stop()

# ==================== BARRA LATERAL - CONFIGURAÇÕES ====================
st.sidebar.title("⚙️ Configurações")

file_format = st.sidebar.selectbox(
    "Formato do arquivo",
    ["CSV", "Excel (.xlsx/.xls)", "Parquet (.parquet)", "Texto (.txt)"],
    key="file_format",
)

separator = st.sidebar.selectbox(
    "Separador de coluna (CSV/TXT)", [";", ",", "\t", "|"], index=0, key="separator"
)

encoding = st.sidebar.selectbox(
    "Codificação", ["utf-8", "latin-1", "cp1252", "iso-8859-1"], index=0, key="encoding"
)

st.sidebar.markdown("---")
st.sidebar.markdown("**📌 Sobre:**")
st.sidebar.info(
    "Painel robusto para análise de dados com suporte a múltiplos formatos e processamento ETL."
)

# ==================== SEÇÃO PRINCIPAL ====================
st.markdown("## 📁 Carregar Arquivo")

# Mapa de tipos de arquivo
file_type_map = {
    "CSV": ["csv", "txt"],
    "Excel (.xlsx/.xls)": ["xlsx", "xls"],
    "Parquet (.parquet)": ["parquet"],
    "Texto (.txt)": ["txt"],
}

allowed_types = file_type_map.get(file_format, ["csv"])

# Upload
uploaded_file = st.file_uploader(
    f'Selecione um arquivo ({", ".join(allowed_types)})',
    type=allowed_types,
    key="file_upload",
)

# Limite estrito do cliente (defesa em profundidade)
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


# ==================== PROCESSAR ARQUIVO ====================
if uploaded_file is not None:
    # Checagem rápida do tamanho (client-side validation)
    try:
        # Alguns file-like objects expõem getbuffer/getvalue
        if hasattr(uploaded_file, "getbuffer"):
            size_bytes = len(uploaded_file.getbuffer())
        elif hasattr(uploaded_file, "getvalue"):
            size_bytes = len(uploaded_file.getvalue())
        else:
            # fallback: seek/tell
            cur = None
            try:
                cur = uploaded_file.tell()
            except Exception:
                cur = None
            try:
                uploaded_file.seek(0, io.SEEK_END)
                size_bytes = uploaded_file.tell()
            finally:
                if cur is not None:
                    try:
                        uploaded_file.seek(cur)
                    except Exception:
                        pass
    except Exception:
        size_bytes = None

    if size_bytes is not None and size_bytes > MAX_BYTES:
        st.error(
            "❌ Arquivo maior que 10 MB. Por favor envie arquivos menores ou utilize o fluxo de upload para datasets grandes (presigned upload)."
        )
        st.stop()

    # Validar arquivo com rotina de segurança
    is_valid, result = file_validator.validate_file(uploaded_file, uploaded_file.name)

    if not is_valid:
        st.error(f"❌ Arquivo rejeitado: {result}")
        st.stop()

    safe_filename = result
    st.success(f"✅ Arquivo validado: {safe_filename}")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "🔄 Carregar e Visualizar", use_container_width=True, key="btn_load"
        ):
            try:
                st.info("Carregando arquivo...")

                # Detectar formato e carregar
                if file_format == "CSV":
                    df = pd.read_csv(uploaded_file, sep=separator, encoding=encoding)
                elif file_format == "Excel (.xlsx/.xls)":
                    df = pd.read_excel(uploaded_file)
                elif file_format == "Parquet (.parquet)":
                    df = pd.read_parquet(uploaded_file)
                else:  # Texto
                    df = pd.read_csv(uploaded_file, sep=separator, encoding=encoding)

                st.session_state.current_df = df
                st.session_state.file_info = {
                    "name": uploaded_file.name,
                    "size": len(df),
                    "columns": len(df.columns),
                    "format": file_format,
                }

                st.success("✅ Arquivo carregado com sucesso!")

            except Exception as e:
                st.error(f"❌ Erro ao carregar: {str(e)}")
                # Se falhar na leitura e o usuário for super_admin, oferecer OCR/PDF processing
                try:
                    meta = credentials.get_user_metadata(st.session_state.username)
                    if meta.get("role") == "super_admin":
                        st.info("Tentando processamento OCR/PDF para super admin...")
                        try:
                            upload_dir = os.path.join(
                                "secure_uploads", st.session_state.username
                            )
                            os.makedirs(upload_dir, exist_ok=True)
                            csvs = []
                            try:
                                uploaded_file.seek(0)
                                csvs = pdf_to_tables_csv(
                                    uploaded_file,
                                    upload_dir,
                                    prefix=st.session_state.username,
                                )
                            except Exception:
                                # tentar OCR de imagem para texto simples
                                try:
                                    uploaded_file.seek(0)
                                    txt = image_to_text(uploaded_file)
                                    path = save_text_as_csv_for_user(
                                        st.session_state.username,
                                        txt,
                                        out_dir="secure_uploads",
                                    )
                                    csvs = [path]
                                except Exception as e2:
                                    st.error(f"❌ OCR falhou: {e2}")
                            if csvs:
                                st.success(
                                    f"✅ Conversão concluída: {len(csvs)} arquivos gerados em secure_uploads/{st.session_state.username}"
                                )
                        except Exception as e3:
                            st.error(f"❌ Erro no processamento OCR: {e3}")
                except Exception:
                    pass

    with col2:
        if st.button("🧹 Limpar Dados", use_container_width=True, key="btn_clean"):
            if st.session_state.current_df is not None:
                try:
                    df = st.session_state.current_df.copy()

                    # Limpeza básica
                    df = df.dropna(how="all")  # Remove linhas completamente vazias
                    df = df.fillna("")  # Preenche NaN com strings vazias

                    st.session_state.current_df = df
                    st.success("✅ Dados limpos!")
                except Exception as e:
                    st.error(f"❌ Erro na limpeza: {str(e)}")
            else:
                st.warning("⚠️ Carregue um arquivo primeiro.")

    with col3:
        if st.button("📊 Análise Rápida", use_container_width=True, key="btn_analyze"):
            if st.session_state.current_df is not None:
                st.write("**Análise do conjunto de dados:**")
                st.write(st.session_state.current_df.describe())
            else:
                st.warning("⚠️ Carregue um arquivo primeiro.")

# ==================== PREVIEW E DETALHES ====================
if st.session_state.current_df is not None:
    st.markdown("---")
    st.markdown("## 📋 Visualização de Dados")

    # Informações do arquivo
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Linhas", st.session_state.file_info.get("size", 0))
    with col2:
        st.metric("Colunas", st.session_state.file_info.get("columns", 0))
    with col3:
        st.metric("Formato", st.session_state.file_info.get("format", "N/A"))
    with col4:
        st.metric("Arquivo", st.session_state.file_info.get("name", "N/A")[:20] + "...")

    # Tabs para diferentes visualizações
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 Dados", "📈 Estatísticas", "🔍 Info", "💾 Exportar", "ETL"]
    )

    with tab1:
        st.markdown("### Primeiras linhas")
        rows_to_show = st.slider("Número de linhas", 5, 100, 10)
        st.dataframe(
            st.session_state.current_df.head(rows_to_show), use_container_width=True
        )

    with tab2:
        st.markdown("### Estatísticas descritivas")
        st.dataframe(st.session_state.current_df.describe(), use_container_width=True)

    with tab3:
        st.markdown("### Informações do dataset")
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("**Tipo de dados:**")
            st.write(st.session_state.current_df.dtypes)
        with col_right:
            st.write("**Valores nulos:**")
            st.write(st.session_state.current_df.isnull().sum())

    with tab4:
        st.markdown("### Exportar dados")
        col_csv, col_excel, col_parquet = st.columns(3)

        with col_csv:
            csv_buffer = st.session_state.current_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 CSV",
                data=csv_buffer,
                file_name=f'dados_{st.session_state.file_info.get("name", "export")}.csv',
                mime="text/csv",
                use_container_width=True,
            )

        with col_excel:
            buffer = io.BytesIO()
            st.session_state.current_df.to_excel(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                "📥 Excel",
                data=buffer,
                file_name=f'dados_{st.session_state.file_info.get("name", "export")}.xlsx',
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with col_parquet:
            parquet_buffer = io.BytesIO()
            st.session_state.current_df.to_parquet(parquet_buffer, index=False)
            parquet_buffer.seek(0)
            st.download_button(
                "📥 Parquet",
                data=parquet_buffer,
                file_name=f'dados_{st.session_state.file_info.get("name", "export")}.parquet',
                mime="application/octet-stream",
                use_container_width=True,
            )

    with tab5:
        st.markdown("### Processamento ETL")
        st.info("Execute a limpeza e agregação de dados de vendas (produto/data)")

        col_etl1, col_etl2 = st.columns(2)

        with col_etl1:
            if st.button("🔄 Aplicar ETL - Limpeza", use_container_width=True):
                try:
                    df_cleaned = clean_product_df(st.session_state.current_df.copy())
                    st.session_state.current_df = df_cleaned
                    st.success("✅ Limpeza ETL aplicada!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro no ETL: {str(e)}")

        with col_etl2:
            if st.button("📊 Aplicar ETL - Agregação", use_container_width=True):
                try:
                    out_paths, reports = aggregate_and_save(
                        df_prod=st.session_state.current_df.copy(),
                        output_folder="streamlit_output",
                    )
                    st.success("✅ Agregação concluída!")
                    if reports:
                        for key, val in reports.items():
                            st.write(f"**{key}**: {len(val)} registros")
                except Exception as e:
                    st.error(f"❌ Erro na agregação: {str(e)}")

st.markdown("---")
st.markdown(
    "**🔒 Privacidade:** Todos os dados são processados localmente. Nenhum arquivo é enviado para servidores remotos."
)
st.markdown(
    "**📧 Suporte:** Desenvolvido com ❤️ para análise segura e independente de dados."
)
st.markdown(
    "**📋 Logs de Segurança:** Verifique `security.log` para auditoria de acessos."
)
st.markdown(
    """
---
## 🛡️ Medidas de Segurança Implementadas:

1. **🔐 Autenticação** — Login com hash PBKDF2
2. **⏱️ Rate Limiting** — Limite de 30 requisições por minuto
3. **📁 Validação de Arquivos** — Verificação de extensão, tamanho e conteúdo
4. **🛡️ Isolamento** — Uploads em diretório seguro (mode 700)
5. **📊 Logging** — Todos os acessos registrados em `security.log`
6. **🧹 Sanitização** — Remoção de caracteres perigosos
7. **⏳ Sessão com Timeout** — Sessões expiram após 1 hora

**⚠️ Próximos passos:**
- Altere as credenciais padrão em `security.py`
- Configure `.secrets/credentials.json` para produção
- Use HTTPS em produção (não HTTP)
- Configure firewall adequado
"""
)

# deploy utilities (DuckDNS updater moved to deploy/duckdns/duckdns_updater.py)
