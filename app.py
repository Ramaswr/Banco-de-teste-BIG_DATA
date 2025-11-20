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
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, TypedDict, cast

import users as user_mgmt
from ocr import image_to_text, pdf_to_tables_csv, save_text_as_csv_for_user
from security import (
    credentials,
    file_validator,
    rate_limiter,
    session_manager,
    setup_secure_environment,
)
from utils.ai_helper import build_virtual_assistant_answer
from utils.file_guard import analyze_url, safe_extract_zip
from utils.mailer import send_phone_otp, send_verification_email
from utils.password_strength import (
    check_password_strength,
    get_strength_color,
    get_strength_label,
)

try:
    from etl_batch.etl_core import QuantumBinaryParser
except Exception:
    QuantumBinaryParser = None  # type: ignore[assignment]

credentials = cast(Any, credentials)
file_validator = cast(Any, file_validator)

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

# numpy é opcional e não é usado diretamente neste arquivo; tentar importar
try:
    import numpy as np  # type: ignore
except Exception:
    np = None

# matplotlib.pyplot é reservado para futuras melhorias de visualização de dados
try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:
    plt = None


# Funções fallback quando dependências não estão disponíveis
def clean_product_df(df: Any) -> Any:
    return df


def aggregate_and_save(
    df_prod: Any = None,
    df_date: Any = None,
    output_folder: str = "streamlit_output",
    save_prefix: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    # Retorna dicionários vazios por padrão; implementar ETL real se necessário
    return {}, {}


class FileInfoDict(TypedDict, total=False):
    name: str
    size: int
    columns: int
    format: str


ValidateFileFn = Callable[[Any, str], Tuple[bool, str]]
GetUserMetadataFn = Callable[[str], Dict[str, Any]]
FileInfoIntKey = Literal["size", "columns"]
FileInfoStrKey = Literal["name", "format"]


def get_current_username() -> Optional[str]:
    """Retorna o usuário atual se definido corretamente na sessão."""
    username_val = st.session_state.get("username")
    return username_val if isinstance(username_val, str) and username_val else None


def get_file_info_state() -> FileInfoDict:
    """Garante acesso tipado ao dicionário de metadados do arquivo."""
    data = st.session_state.get("file_info")
    return cast(FileInfoDict, data) if isinstance(data, dict) else {}


def file_info_int(key: FileInfoIntKey, default: int = 0) -> int:
    value = get_file_info_state().get(key)
    if isinstance(value, (int, float)):
        return int(value)
    return default


def file_info_str(key: FileInfoStrKey, default: str = "N/A") -> str:
    value = get_file_info_state().get(key)
    if isinstance(value, str):
        return value
    return default


def validate_uploaded_file(file_obj: Any, filename: str) -> tuple[bool, str]:
    """Proxy tipado para file_validator.validate_file."""
    validate_fn = cast(
        ValidateFileFn, file_validator.validate_file  # type: ignore[assignment]
    )
    return validate_fn(file_obj, filename)


def get_user_metadata(username: str) -> dict[str, Any]:
    """Proxy tipado para credentials.get_user_metadata."""
    metadata_fn = cast(
        GetUserMetadataFn, credentials.get_user_metadata  # type: ignore[assignment]
    )
    return metadata_fn(username)


def authenticate_user(username: str, password: str) -> bool:
    """
    Autentica usuário usando 3 sistemas:
    1. Credentials.json (usuários locais pré-configurados)
    2. SQLite (banco de usuários registrados)
    3. Se falhar em ambos, retorna False
    """
    # Tentar autenticação em credentials.json
    if credentials.authenticate(username, password):
        return True

    # Tentar autenticação em SQLite (usuários registrados)
    if user_mgmt.authenticate(username, password):
        return True

    return False


# ==================== CONFIGURAÇÃO ====================
st.set_page_config(
    page_title="📊 Jerr_BIG-DATE", layout="wide", initial_sidebar_state="expanded"
)

# Configurar ambiente seguro na primeira execução
if "setup_done" not in st.session_state:
    setup_secure_environment()
    st.session_state.setup_done = True

SECURE_UPLOAD_ROOT = Path("secure_uploads")
SECURE_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(SECURE_UPLOAD_ROOT, 0o700)
except Exception:
    pass

SANDBOX_QUEUE_DIR = SECURE_UPLOAD_ROOT / "sandbox_queue"
SANDBOX_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
try:
    os.chmod(SANDBOX_QUEUE_DIR, 0o700)
except Exception:
    pass

ANYRUN_PUBLIC_URL = "https://any.run/malware-trends/"
ANYRUN_APP_URL = (
    "https://app.any.run/?_gl=1*1vm9x5j*_ga*ODg2MzgyMDA3LjE3NjM2MTY1MjM.*_ga_53KB74YDZR*"
    "czE3NjM2MTY1MjIkbzEkZzEkdDE3NjM2MTc2MDIkajIwJGwwJGgxMzMwNzIxMjM5#register"
)
MAX_SANDBOX_BYTES = 15 * 1024 * 1024  # 15 MB

st.session_state.setdefault("security_events", [])
st.session_state.setdefault("zip_last_entries", 0)
st.session_state.setdefault("sandbox_files", 0)

# CSS customizado para aparência Dark
st.markdown(
    """
<style>
  /* Variáveis de cores */
  :root {
    --bg-primary: #0a0e27;
    --bg-secondary: #0f1428;
    --bg-tertiary: #1a1f3a;
    --text-primary: #e6f0ff;
    --text-secondary: #a8b5cc;
    --accent-primary: #7c3aed;
    --accent-secondary: #6366f1;
    --success: #22c55e;
    --warning: #f59e0b;
    --error: #ef4444;
    --border-color: #2d3748;
  }

  /* Fundo com padrão de códigos binários */
  @keyframes binaryFlow {
    0% { transform: translateY(0); opacity: 0.3; }
    100% { transform: translateY(20px); opacity: 0; }
  }

  body, .main, .stApp {
    background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
    color: var(--text-primary);
    font-family: 'Inter', 'Segoe UI', sans-serif;
  }

  /* Fundo com códigos binários animados */
  .main::before {
    content: '01010101 10101010 11001100 00110011 01010101 10101010 11001100 00110011';
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    font-size: 14px;
    color: rgba(124, 58, 237, 0.05);
    white-space: pre-wrap;
    word-wrap: break-word;
    pointer-events: none;
    z-index: -1;
    font-family: 'Courier New', monospace;
    line-height: 1.5;
    overflow: hidden;
  }

  .main .block-container {
    background-color: rgba(10, 14, 39, 0.8);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    padding: 2rem;
    margin-top: 1rem;
  }

    body::after {
        content: "";
        position: fixed;
        inset: 0;
        background-image:
            linear-gradient(180deg, rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.9)),
            url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Crect width='400' height='400' fill='%23010718'/%3E%3Ctext x='20' y='40' fill='%2300ff9d' font-size='18' font-family='Courier New, Courier, monospace'%3E010010110101001101010010%0A101001011010100101010010%0A010101101001010010101010%0A101001010101101001010101%0A010110100101001010101010%3C/text%3E%3C/svg%3E");
        background-size: cover, 400px 400px;
        opacity: 0.2;
        pointer-events: none;
        z-index: -2;
        animation: matrixDrift 22s linear infinite;
    }

    @keyframes matrixDrift {
        from {
            background-position: 0 0, 0 0;
        }
        to {
            background-position: 0 0, 0 600px;
        }
    }

  /* Header do dashboard */
  .dashboard-header {
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.2) 0%, rgba(99, 102, 241, 0.1) 100%);
    border: 1px solid rgba(124, 58, 237, 0.3);
    color: var(--text-primary);
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.1);
    backdrop-filter: blur(10px);
  }

  .dashboard-header h1 {
    color: var(--accent-primary);
    text-shadow: 0 0 20px rgba(124, 58, 237, 0.3);
    margin-bottom: 0.5rem;
  }

  .dashboard-header p {
    color: var(--text-secondary);
    font-size: 0.95rem;
  }

  /* Painel de controle */
  .control-panel {
    background: linear-gradient(135deg, rgba(15, 20, 40, 0.9) 0%, rgba(26, 31, 58, 0.9) 100%);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 1.5rem;
    border-radius: 10px;
    border-left: 4px solid var(--accent-primary);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    margin-bottom: 1rem;
  }

  /* Badges de status */
  .status-badge {
    display: inline-block;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .status-active {
    background: linear-gradient(135deg, var(--success) 0%, #16a34a 100%);
    color: #0a2e0a;
    box-shadow: 0 0 20px rgba(34, 197, 94, 0.3);
  }

  .status-inactive {
    background: linear-gradient(135deg, var(--error) 0%, #dc2626 100%);
    color: #450a0a;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
  }

  .status-pending {
    background: linear-gradient(135deg, var(--warning) 0%, #d97706 100%);
    color: #451a03;
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
  }

  /* Banner de segurança */
  .security-banner {
    background: linear-gradient(135deg, rgba(7, 16, 41, 0.9) 0%, rgba(26, 31, 58, 0.9) 100%);
    border-left: 4px solid var(--warning);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1.5rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  .security-banner strong {
    color: var(--warning);
  }

  /* Formulários e inputs */
  .stTextInput > div > div > input,
  .stPasswordInput > div > div > input,
  .stSelectbox > div > div > select,
  .stTextArea > div > div > textarea {
    background-color: rgba(26, 31, 58, 0.6) !important;
    border: 1px solid var(--border-color) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
    padding: 0.75rem !important;
  }

  .stTextInput > div > div > input:focus,
  .stPasswordInput > div > div > input:focus,
  .stSelectbox > div > div > select:focus,
  .stTextArea > div > div > textarea:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1) !important;
  }

  /* Botões */
  .stButton > button {
    background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.5rem;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 16px rgba(124, 58, 237, 0.3);
  }

  .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(124, 58, 237, 0.4);
  }

  /* Cards de informação */
  .info-card {
    background: linear-gradient(135deg, rgba(15, 20, 40, 0.7) 0%, rgba(26, 31, 58, 0.7) 100%);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    backdrop-filter: blur(10px);
  }

  /* Mensagens de alerta */
  .stAlert {
    border-radius: 8px;
    border: 1px solid rgba(124, 58, 237, 0.3);
    background-color: rgba(124, 58, 237, 0.1) !important;
  }

  /* Sidebar */
  .sidebar .sidebar-content {
    background: linear-gradient(180deg, rgba(15, 20, 40, 0.95) 0%, rgba(26, 31, 58, 0.95) 100%);
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 1px;
    background-color: transparent;
  }

  .stTabs [data-baseweb="tab"] {
    border: 1px solid var(--border-color);
    border-radius: 8px;
    color: var(--text-secondary);
  }

  .stTabs [aria-selected="true"] {
    border-bottom: 2px solid var(--accent-primary);
    color: var(--accent-primary);
  }

  /* Expander */
  .streamlit-expanderHeader {
    background-color: rgba(26, 31, 58, 0.5);
    border-radius: 8px;
    color: var(--text-primary);
  }

  .streamlit-expanderHeader:hover {
    background-color: rgba(26, 31, 58, 0.7);
  }

  /* Scrollbar customizada */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    background: rgba(26, 31, 58, 0.5);
  }

  ::-webkit-scrollbar-thumb {
    background: var(--accent-primary);
    border-radius: 4px;
  }

  ::-webkit-scrollbar-thumb:hover {
    background: var(--accent-secondary);
  }

  /* Supporter badge */
  .supporter-badge {
    position: relative;
    font-size: 0.9rem;
    color: #a3e635;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  /* Animações suaves */
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .main .block-container > * {
    animation: fadeIn 0.5s ease-out;
  }

  /* Tooltip */
  .tooltip {
    position: relative;
    display: inline-block;
    border-bottom: 1px dotted var(--accent-primary);
  }

  .tooltip .tooltiptext {
    visibility: hidden;
    width: 200px;
    background-color: rgba(26, 31, 58, 0.95);
    color: var(--text-primary);
    text-align: center;
    border-radius: 6px;
    padding: 5px;
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    margin-left: -100px;
    opacity: 0;
    transition: opacity 0.3s;
    border: 1px solid var(--accent-primary);
  }

  .tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
  }
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

    _, col2, _ = st.columns([1, 2, 1])

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
                if authenticate_user(username, password):
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
    # Avoid runtime/type annotation issues by assigning without inline annotation
    st.session_state.file_info = cast(FileInfoDict, {})
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
    pix_key: Optional[str] = None
    role = "user"
    current_username = get_current_username()
    if current_username:
        try:
            meta = get_user_metadata(current_username)
            pix_val = meta.get("pix_key")
            if isinstance(pix_val, str):
                pix_key = pix_val
            role_val = meta.get("role")
            if isinstance(role_val, str):
                role = role_val
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
user_role = st.session_state.get("user_role", "user")
has_binary_access = user_role in {"admin", "super_admin"}

file_format_options = [
    "CSV",
    "Excel (.xlsx/.xls)",
    "Parquet (.parquet)",
    "Texto (.txt)",
]
if has_binary_access:
    file_format_options.append("BIN (quantum .bin)")

file_format = st.sidebar.selectbox(
    "Formato do arquivo",
    file_format_options,
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

if has_binary_access:
    st.sidebar.markdown("---")
    st.sidebar.markdown("**🧬 Quantum Binary Mode (admins)**")
    st.sidebar.success(
        "Modo BIN habilitado: registros fixos `<IQIq32s>` com parser Quantum Binary. Envie arquivos .bin para convertê-los em DataFrame protegido innan do app."
    )

# ==================== SEÇÃO PRINCIPAL ====================
st.markdown("## 📁 Carregar Arquivo")

if has_binary_access:
    with st.expander("Modo BIN quantum", expanded=False):
        st.markdown(
            """
            - **Formato esperado:** registros fixos `<IQIq32s>` (id, timestamp, quantidade, valor em centavos, nome do produto).
            - **Pipeline:** parser `QuantumBinaryParser` converte blocos .BIN em DataFrame protegido antes de gerar CSV/Parquet.
            - **Recurso exclusivo:** disponível apenas para administradores/super admins autenticados.
            """
        )

# Mapa de tipos de arquivo
file_type_map = {
    "CSV": ["csv", "txt"],
    "Excel (.xlsx/.xls)": ["xlsx", "xls"],
    "Parquet (.parquet)": ["parquet"],
    "Texto (.txt)": ["txt"],
    "BIN (quantum .bin)": ["bin"],
}

allowed_types = file_type_map.get(file_format, ["csv"])

# Upload
uploaded_file = st.file_uploader(
    f'Selecione um arquivo ({", ".join(allowed_types)})',
    type=allowed_types,
    key="file_upload",
)

st.markdown("### 🛡️ Segurança Proativa")
tab_link, tab_zip, tab_ai = st.tabs(
    ["Verificar Link", "Processar ZIP", "Assistente IA"]
)

with tab_link:
    suspect_url = st.text_input(
        "Cole um link para inspeção",
        placeholder="https://exemplo.com/arquivo",
        key="security_link_input",
    )
    if st.button("Analisar link", key="btn_scan_link"):
        if not suspect_url.strip():
            st.warning("Informe um link antes de executar a análise.")
        else:
            report = analyze_url(suspect_url)
            verdict = "seguro" if report["safe"] else "suspeito"
            message = \
                f"Hash {report['hash']} — domínio `{report['hostname'] or 'desconhecido'}` classificado como {verdict}."
            if report["safe"]:
                st.success(message)
            else:
                st.error(message)
            for reason in report["reasons"]:
                st.write(f"- {reason}")
            st.session_state.security_events.append(
                f"URL {'OK' if report['safe'] else 'bloqueada'}: {report['input']}"
            )

with tab_zip:
    zip_file = st.file_uploader(
        "Envie um pacote ZIP para verificação",
        type=["zip"],
        key="zip_guard_upload",
        help="Arquivos são extraídos em sandbox e analisados antes de uso.",
    )
    if st.button("Validar ZIP", key="btn_zip_guard"):
        if zip_file is None:
            st.warning("Anexe um arquivo ZIP antes de validar.")
        else:
            try:
                zip_bytes = zip_file.getvalue()
                target_dir = SECURE_UPLOAD_ROOT / f"zip_{secrets.token_hex(4)}"
                entries = safe_extract_zip(zip_bytes, target_dir)
                st.success(
                    f"ZIP inspecionado com sucesso — {len(entries)} arquivo(s) extraído(s) para `{target_dir}`"
                )
                st.session_state.security_events.append(
                    f"ZIP seguro armazenado em {target_dir}"
                )
                st.session_state.zip_last_entries = len(entries)
                for entry in entries:
                    st.write(
                        f"📄 `{entry['name']}` — {entry['bytes']} bytes"
                        f" | {'texto' if entry['allowed'] else 'binário'}"
                    )
                    if entry.get("preview"):
                        st.code(entry["preview"], language="text")
            except Exception as zip_exc:
                st.error(f"Falha ao validar ZIP: {zip_exc}")
                st.session_state.security_events.append(
                    f"ZIP rejeitado ({zip_exc})"
                )

with tab_ai:
    st.caption("Assistente IA local — fornece apenas orientações de leitura.")
    if st.button("🤖 Consultar IA", key="btn_ai_assistant"):
        answer = build_virtual_assistant_answer(
            events=st.session_state.security_events,
            has_dataframe="current_df" in st.session_state,
            binary_enabled=has_binary_access,
            zip_entries=int(st.session_state.get("zip_last_entries", 0)),
        )
        st.info(answer)

st.markdown("### 🧪 Sandbox ANY.RUN")
st.info(
    "Envie URLs ou arquivos suspeitos para quarentena local e abra o painel oficial do ANY.RUN para análise profunda. "
    "Os dados permanecem na sua máquina; o upload para o serviço externo é opcional e manual."
)

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("#### URL suspeita")
    sandbox_url = st.text_input(
        "Cole o link a ser investigado",
        placeholder="https://exemplo.com/malware",
        key="sandbox_url_input",
    )
    if st.button("Pré-verificar URL", key="btn_sandbox_url"):
        if not sandbox_url.strip():
            st.warning("Informe uma URL antes de validar.")
        else:
            report = analyze_url(sandbox_url)
            verdict = "✅ Nenhum indicador crítico" if report["safe"] else "⚠️ Indicadores suspeitos"
            st.write(verdict)
            for reason in report["reasons"]:
                st.write(f"- {reason}")
            st.session_state.security_events.append(
                f"Sandbox URL {'limpa' if report['safe'] else 'suspeita'}: {report['input']}"
            )
    st.markdown(
        f"[Abrir trends oficiais]({ANYRUN_PUBLIC_URL}) · [Abrir console ANY.RUN]({ANYRUN_APP_URL})"
    )

with col_b:
    st.markdown("#### Arquivo suspeito")
    sandbox_file = st.file_uploader(
        "Envie ZIP ou documento para quarentena",
        type=["zip", "rar", "7z", "exe", "dll", "pdf", "docx", "xlsx"],
        key="sandbox_file_uploader",
        help="Os arquivos são salvos em secure_uploads/sandbox_queue para análise manual na sandbox.",
    )
    if st.button("Armazenar para sandbox", key="btn_save_sandbox"):
        if sandbox_file is None:
            st.warning("Selecione um arquivo antes de armazenar.")
        else:
            data = sandbox_file.getvalue()
            if len(data) > MAX_SANDBOX_BYTES:
                st.error("Arquivo maior que 15 MB — use a sandbox manualmente.")
            else:
                safe_name = Path(sandbox_file.name).name.replace(" ", "_")
                dest = SANDBOX_QUEUE_DIR / f"sample_{int(time.time())}_{safe_name}"
                dest.write_bytes(data)
                st.success(f"Arquivo guardado em {dest} — pronto para submissão ao ANY.RUN.")
                st.session_state.security_events.append(f"Arquivo enviado à sandbox: {dest.name}")
                st.session_state.sandbox_files += 1

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
    is_valid, result = validate_uploaded_file(uploaded_file, uploaded_file.name)

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

                # Detectar formato e carregar (fallbacks de encoding)
                if file_format == "CSV":
                    # Try common encodings safely. uploaded_file is a BytesIO-like object.
                    uploaded_file.seek(0)
                    data_bytes = uploaded_file.read()
                    encodings_to_try = ["utf-8", "latin-1"]
                    decoded = None
                    for enc in encodings_to_try:
                        try:
                            decoded = data_bytes.decode(enc)
                            used_encoding = enc
                            break
                        except Exception:
                            decoded = None
                    if decoded is None:
                        # Optional: try chardet if available
                        try:
                            import chardet

                            guess = chardet.detect(data_bytes)
                            if guess and guess.get("encoding"):
                                decoded = data_bytes.decode(guess["encoding"], errors="replace")
                                used_encoding = guess.get("encoding")
                        except Exception:
                            decoded = None
                    if decoded is None:
                        # Last resort: replace undecodable bytes
                        decoded = data_bytes.decode("utf-8", errors="replace")
                        used_encoding = "utf-8-replace"

                    # Create a text stream for pandas
                    from io import StringIO

                    text_stream = StringIO(decoded)
                    df = pd.read_csv(text_stream, sep=separator)

                elif file_format == "Excel (.xlsx/.xls)":
                    uploaded_file.seek(0)
                    df = pd.read_excel(uploaded_file)

                elif file_format == "Parquet (.parquet)":
                    uploaded_file.seek(0)
                    df = pd.read_parquet(uploaded_file)

                elif file_format == "BIN (quantum .bin)":
                    if QuantumBinaryParser is None:
                        raise ModuleNotFoundError("QuantumBinaryParser indisponível no ambiente atual")
                    uploaded_file.seek(0)
                    raw_bytes = uploaded_file.read()
                    parser = QuantumBinaryParser("<IQIq32s>")
                    record_size = parser.record_size
                    if len(raw_bytes) < record_size:
                        raise ValueError("BIN muito pequeno para conter registros válidos")
                    aligned_len = len(raw_bytes) - (len(raw_bytes) % record_size)
                    usable_bytes = raw_bytes[:aligned_len]
                    block_size = max(record_size * 1024, record_size)
                    records: List[Dict[str, Any]] = []
                    for start in range(0, len(usable_bytes), block_size):
                        block = usable_bytes[start : start + block_size]
                        records.extend(parser.parse_block(block))
                    if not records:
                        raise ValueError("Nenhum registro identificado no arquivo BIN fornecido")
                    df = pd.DataFrame(records)
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")

                else:  # Texto (treat as CSV fallback)
                    uploaded_file.seek(0)
                    data_bytes = uploaded_file.read()
                    try:
                        text = data_bytes.decode("utf-8")
                    except Exception:
                        try:
                            text = data_bytes.decode("latin-1")
                        except Exception:
                            text = data_bytes.decode("utf-8", errors="replace")
                    from io import StringIO

                    df = pd.read_csv(StringIO(text), sep=separator)

                st.session_state.current_df = df
                st.session_state.file_info = cast(
                    FileInfoDict,
                    {
                        "name": str(uploaded_file.name),
                        "size": int(len(df)),
                        "columns": int(len(df.columns)),
                        "format": str(file_format),
                    },
                )

                st.success("✅ Arquivo carregado com sucesso!")

            except Exception as e:
                st.error(f"❌ Erro ao carregar: {str(e)}")
                current_username = get_current_username()
                if current_username:
                    try:
                        meta = get_user_metadata(current_username)
                    except Exception:
                        meta = {}
                    if meta.get("role") == "super_admin":
                        st.info("Tentando processamento OCR/PDF para super admin...")
                        try:
                            upload_dir = os.path.join("secure_uploads", current_username)
                            os.makedirs(upload_dir, exist_ok=True)
                            csvs = []
                            try:
                                uploaded_file.seek(0)
                                csvs = pdf_to_tables_csv(
                                    uploaded_file,
                                    upload_dir,
                                    prefix=current_username,
                                )
                            except Exception:
                                # tentar OCR de imagem para texto simples
                                try:
                                    uploaded_file.seek(0)
                                    txt = image_to_text(uploaded_file)
                                    path = save_text_as_csv_for_user(
                                        current_username,
                                        txt,
                                        out_dir="secure_uploads",
                                    )
                                    csvs = [path]
                                except Exception as e2:
                                    st.error(f"❌ OCR falhou: {e2}")
                            if csvs:
                                st.success(
                                    f"✅ Conversão concluída: {len(csvs)} arquivos gerados em secure_uploads/{current_username}"
                                )
                        except Exception as e3:
                            st.error(f"❌ Erro no processamento OCR: {e3}")

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
    file_lines = file_info_int("size")
    file_columns = file_info_int("columns")
    file_format_label = file_info_str("format")
    file_name_display = file_info_str("name")
    with col1:
        st.metric("Linhas", file_lines)
    with col2:
        st.metric("Colunas", file_columns)
    with col3:
        st.metric("Formato", file_format_label)
    with col4:
        st.metric("Arquivo", (file_name_display[:20] + "...") if file_name_display else "N/A")

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
        download_name = file_info_str("name", "export")

        with col_csv:
            csv_buffer = st.session_state.current_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 CSV",
                data=csv_buffer,
                file_name=f"dados_{download_name}.csv",
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
                file_name=f"dados_{download_name}.xlsx",
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
                file_name=f"dados_{download_name}.parquet",
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
