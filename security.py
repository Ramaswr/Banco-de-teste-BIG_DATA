"""
Módulo de segurança para proteção do Streamlit app.
- Autenticação com username/password
- Validação de arquivos
- Rate limiting
- CORS e headers de segurança
- Isolamento de processo
- Sanitização de entrada
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Optional, Tuple
from logging.handlers import RotatingFileHandler

# Configurar logging
LOG_PATH = os.path.join("logs", "security.log")
os.makedirs("logs", exist_ok=True)
try:
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=5)
except Exception:
    file_handler = logging.FileHandler(LOG_PATH)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURAÇÃO DE CREDENCIAIS ====================


class CredentialManager:
    """Gerenciador de credenciais com hash seguro."""

    def __init__(self, config_file: str = ".secrets/credentials.json"):
        self.config_file = config_file
        self.credentials = self._load_credentials()
        # user metadata cache: {username: {'role': ..., 'pix_key': ...}}
        self.user_meta = self._load_user_metadata()

    def _load_credentials(self) -> dict:
        """Carrega credenciais do arquivo de configuração."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar credenciais: {e}")
        # Não criar credenciais padrão automaticamente em produção.
        # Retorne um dicionário vazio para forçar configuração explícita.
        logger.warning("Nenhuma credencial encontrada; é necessário configurar .secrets/credentials.json")
        return {"users": {}}

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash seguro de senha com salt."""
        salt = os.urandom(32)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return f"pbkdf2:100000:{salt.hex()}:{pwd_hash.hex()}"

    @staticmethod
    def _verify_password(password: str, hash_stored: str) -> bool:
        """Verifica se a senha corresponde ao hash."""
        try:
            parts = hash_stored.split(":")
            if len(parts) != 4 or parts[0] != "pbkdf2":
                return False

            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            stored_hash = bytes.fromhex(parts[3])

            pwd_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt, iterations
            )
            return hmac.compare_digest(pwd_hash, stored_hash)
        except Exception as e:
            logger.error(f"Erro ao verificar senha: {e}")
            return False

    def authenticate(self, username: str, password: str) -> bool:
        """Autentica usuário com username e password."""
        user_entry = self.credentials.get("users", {}).get(username)
        if not user_entry:
            logger.warning(f"Tentativa de login com usuário inexistente: {username}")
            return False

        stored_hash = (
            user_entry.get("password") if isinstance(user_entry, dict) else user_entry
        )
        is_valid = self._verify_password(password, stored_hash)

        if is_valid:
            logger.info(f"Login bem-sucedido: {username}")
        else:
            logger.warning(f"Login falhou para: {username}")

        return is_valid

    def _load_user_metadata(self) -> dict:
        meta = {}
        for u, v in self.credentials.get("users", {}).items():
            if isinstance(v, dict):
                meta[u] = {"role": v.get("role", "user"), "pix_key": v.get("pix_key")}
            else:
                meta[u] = {"role": "user", "pix_key": None}
        # garantir metadados consistente
        return meta

    def get_user_metadata(self, username: str) -> dict:
        return self.user_meta.get(username, {"role": "user", "pix_key": None})


# ==================== VALIDAÇÃO DE ARQUIVOS ====================


class FileValidator:
    """Validador de arquivos para prevenir uploads maliciosos."""

    # Extensões permitidas
    ALLOWED_EXTENSIONS = {"csv", "txt", "xlsx", "xls", "parquet", "json", "tsv"}

    # MIME types permitidos
    ALLOWED_MIMES = {
        "text/csv",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/json",
    }

    # Tamanho máximo de arquivo (10 MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Diretório seguro para uploads
    UPLOAD_DIR = "secure_uploads"

    @staticmethod
    def _ensure_upload_dir():
        """Cria diretório seguro se não existir."""
        os.makedirs(FileValidator.UPLOAD_DIR, exist_ok=True)
        os.chmod(FileValidator.UPLOAD_DIR, 0o700)  # rwx------

    @classmethod
    def validate_file(cls, file_obj, filename: str) -> Tuple[bool, str]:
        """Valida arquivo antes de processar."""
        cls._ensure_upload_dir()

        # 1. Verificar extensão
        if not filename.lower().endswith(
            tuple(f".{ext}" for ext in cls.ALLOWED_EXTENSIONS)
        ):
            return (
                False,
                f"Extensão não permitida. Use: {', '.join(cls.ALLOWED_EXTENSIONS)}",
            )

        # 2. Verificar tamanho (maneira robusta para file-like objects)
        try:
            # Alguns objetos (BytesIO) suportam getbuffer()/getvalue()
            if hasattr(file_obj, "getbuffer"):
                file_size = len(file_obj.getbuffer())
            elif hasattr(file_obj, "getvalue"):
                # getvalue pode carregar muita memória, mas é comum em testes
                file_size = len(file_obj.getvalue())
            else:
                # fallback: leia em chunks até o limite (não carrega inteiro na memória)
                current = None
                try:
                    current = file_obj.tell()
                except Exception:
                    current = None
                file_size = 0
                try:
                    file_obj.seek(0)
                except Exception:
                    pass
                chunk = file_obj.read(8192)
                while chunk:
                    file_size += len(chunk)
                    if file_size > cls.MAX_FILE_SIZE:
                        break
                    chunk = file_obj.read(8192)
                # reset pointer caso seja seekable
                try:
                    if current is not None:
                        file_obj.seek(current)
                    else:
                        file_obj.seek(0)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Não foi possível determinar tamanho do arquivo: {e}")
            return False, "Não foi possível determinar tamanho do arquivo"

        if file_size > cls.MAX_FILE_SIZE:
            return (
                False,
                f"Arquivo muito grande. Máximo: {cls.MAX_FILE_SIZE / 1024 / 1024:.0f} MB",
            )

        # 3. Verificar conteúdo (magic bytes)
        file_obj.seek(0)
        header = file_obj.read(512)
        file_obj.seek(0)

        if not cls._verify_magic_bytes(header, filename):
            return (
                False,
                "Conteúdo do arquivo não corresponde à extensão (possível arquivo falso)",
            )

        # 4. Sanitizar filename
        safe_filename = cls._sanitize_filename(filename)

        logger.info(f"Arquivo validado: {safe_filename} ({file_size} bytes)")
        return True, safe_filename

    @staticmethod
    def _verify_magic_bytes(header: bytes, filename: str) -> bool:
        """Verifica assinatura de arquivo (magic bytes)."""
        ext = Path(filename).suffix.lower()

        magic_signatures = {
            # Require at least printable characters for CSV/TXT (avoid empty binary)
            ".csv": [b"\n", b"\r", b"\xef\xbb\xbf"],
            ".txt": [b"\n", b"\r", b"\xef\xbb\xbf"],
            ".xlsx": [b"PK\x03\x04"],  # ZIP signature
            ".xls": [b"\xd0\xcf\x11\xe0"],  # OLE2
            ".parquet": [b"PAR1"],
            ".json": [b"{", b"[", b"\xef\xbb\xbf"],
        }

        if ext not in magic_signatures:
            return True  # Permitir extensões não mapeadas

        valid_sigs = magic_signatures[ext]
        return any(header.startswith(sig) for sig in valid_sigs)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Remove caracteres perigosos do nome do arquivo."""
        # Remover path traversal
        filename = os.path.basename(filename)

        # Remover caracteres especiais perigosos
        dangerous_chars = '<>:"/\\|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, "_")

        # Remover espaços extras e pontos no início
        filename = filename.strip(". ")

        # Adicionar timestamp para evitar colisão
        timestamp = int(time.time() * 1000)
        name, ext = os.path.splitext(filename)
        return f"{name}_{timestamp}{ext}"


# ==================== BLACKLIST (APLICAÇÃO) ====================
BLACKLIST_FILE = ".secrets/blacklist.json"
LOCKS_FILE = ".secrets/locks.json"


def _ensure_locks():
    try:
        os.makedirs(".secrets", exist_ok=True)
        if not os.path.exists(LOCKS_FILE):
            with open(LOCKS_FILE, "w") as f:
                json.dump({"failed": {}, "locked": {}}, f)
            try:
                os.chmod(LOCKS_FILE, 0o600)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Erro ao garantir locks file: {e}")


def _read_locks():
    _ensure_locks()
    try:
        with open(LOCKS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"failed": {}, "locked": {}}


def _write_locks(data: dict):
    tmp = LOCKS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    try:
        os.replace(tmp, LOCKS_FILE)
    except Exception:
        with open(LOCKS_FILE, "w") as f:
            json.dump(data, f)
    try:
        os.chmod(LOCKS_FILE, 0o600)
    except Exception:
        pass


def register_failed_attempt(identifier: str, max_attempts: int = 5, window: int = 300, lock_time: int = 600):
    """Registra tentativa falha e bloqueia se exceder `max_attempts` dentro de `window` segundos.
    identifier pode ser username ou ip ou session id.
    """
    now = int(time.time())
    data = _read_locks()
    failed = data.get("failed", {})
    lst = failed.get(identifier, [])
    # manter só dentro da janela
    lst = [ts for ts in lst if now - ts < window]
    lst.append(now)
    failed[identifier] = lst
    data["failed"] = failed
    # bloquear se necessário
    if len(lst) >= max_attempts:
        locked = data.get("locked", {})
        locked[identifier] = now + lock_time
        data["locked"] = locked
        # limpar falhas
        data["failed"][identifier] = []
    _write_locks(data)


def is_locked(identifier: str) -> bool:
    data = _read_locks()
    locked = data.get("locked", {})
    now = int(time.time())
    until = locked.get(identifier)
    if until and now < until:
        return True
    # limpar bloqueio expirado
    if until and now >= until:
        locked.pop(identifier, None)
        data["locked"] = locked
        _write_locks(data)
        return False
    return False


def reset_attempts(identifier: str):
    data = _read_locks()
    failed = data.get("failed", {})
    if identifier in failed:
        failed[identifier] = []
    data["failed"] = failed
    # também remover lock se existir
    locked = data.get("locked", {})
    if identifier in locked:
        locked.pop(identifier, None)
    data["locked"] = locked
    _write_locks(data)


def _ensure_blacklist():
    try:
        os.makedirs(".secrets", exist_ok=True)
        try:
            os.chmod(".secrets", 0o700)
        except Exception:
            pass
        if not os.path.exists(BLACKLIST_FILE):
            with open(BLACKLIST_FILE, "w") as f:
                json.dump({"ips": {}}, f)
    except Exception as e:
        logger.warning(f"Erro ao garantir blacklist: {e}")


def is_blacklisted(ip: str) -> bool:
    _ensure_blacklist()
    try:
        with open(BLACKLIST_FILE, "r") as f:
            data = json.load(f)
        return ip in data.get("ips", {})
    except Exception:
        return False


def add_to_blacklist(ip: str, reason: str = ""):
    _ensure_blacklist()
    try:
        with open(BLACKLIST_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        data = {"ips": {}}
    data["ips"][ip] = {"reason": reason, "time": int(time.time())}
    # Escrita atômica simples: gravar em arquivo temporário e renomear
    tmp = BLACKLIST_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    try:
        os.replace(tmp, BLACKLIST_FILE)
    except Exception:
        # fallback
        with open(BLACKLIST_FILE, "w") as f:
            json.dump(data, f)
    try:
        os.chmod(BLACKLIST_FILE, 0o600)
    except Exception:
        pass
    logger.info(f"IP adicionado à blacklist (aplicação): {ip} - {reason}")


# ==================== RATE LIMITING ====================


class RateLimiter:
    """Limitador de taxa para prevenir brute force."""

    def __init__(self, max_requests: int = 30, time_window: int = 60):
        """
        max_requests: número máximo de requisições
        time_window: janela de tempo em segundos
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}  # {ip: [(timestamp, count), ...]}

    def is_allowed(self, identifier: str) -> bool:
        """Verifica se requisição é permitida para o identificador (IP/usuário)."""
        current_time = time.time()

        if identifier not in self.requests:
            self.requests[identifier] = []

        # Remove requisições fora da janela de tempo
        self.requests[identifier] = [
            (ts, count)
            for ts, count in self.requests[identifier]
            if current_time - ts < self.time_window
        ]

        # Contar requisições na janela
        total_requests = sum(count for _, count in self.requests[identifier])

        if total_requests >= self.max_requests:
            logger.warning(f"Rate limit atingido para: {identifier}")
            return False

        # Adicionar nova requisição
        if self.requests[identifier]:
            ts, count = self.requests[identifier][-1]
            if current_time - ts < 1:  # Mesma segunda
                self.requests[identifier][-1] = (ts, count + 1)
            else:
                self.requests[identifier].append((current_time, 1))
        else:
            self.requests[identifier].append((current_time, 1))

        return True


# ==================== SESSION MANAGEMENT ====================


class SessionManager:
    """Gerenciador de sessões seguras."""

    def __init__(self, timeout: int = 3600):  # 1 hora
        self.timeout = timeout
        self.sessions = {}  # {session_id: {'user': username, 'created': timestamp}}

    def create_session(self, username: str) -> str:
        """Cria nova sessão para usuário autenticado."""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {"user": username, "created": time.time()}
        logger.info(f"Sessão criada para: {username}")
        return session_id

    def validate_session(self, session_id: str) -> Optional[str]:
        """Valida sessão e retorna username se válida."""
        if session_id not in self.sessions:
            logger.warning(f"Sessão inválida: {session_id}")
            return None

        session = self.sessions[session_id]
        if time.time() - session["created"] > self.timeout:
            del self.sessions[session_id]
            logger.info(f"Sessão expirada: {session_id}")
            return None

        return session["user"]

    def destroy_session(self, session_id: str):
        """Destroi sessão."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Sessão destruída: {session_id}")


# ==================== SANITIZAÇÃO DE ENTRADA ====================


class InputSanitizer:
    """Sanitiza entrada de usuário para prevenir injeção."""

    @staticmethod
    def sanitize_sql(text: str) -> str:
        """Remove caracteres perigosos de SQL."""
        dangerous = ["'", '"', ";", "--", "/*", "*/", "DROP", "DELETE", "INSERT"]
        for word in dangerous:
            text = text.replace(word, "")
        return text

    @staticmethod
    def sanitize_command(text: str) -> str:
        """Remove caracteres perigosos de comando shell."""
        dangerous = [";", "|", "&", "$", "`", "\n", "\r"]
        for char in dangerous:
            text = text.replace(char, "")
        return text

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Valida caminho de arquivo."""
        # Remover path traversal
        path = path.replace("..", "")
        path = path.replace("//", "/")
        return path.strip("/")


# ==================== SECURITY HEADERS ====================


def get_security_headers() -> dict:
    """Retorna headers HTTP de segurança."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }


# ==================== UTILS ====================


def setup_secure_environment():
    """Configura ambiente seguro."""
    # Criar diretórios seguros
    os.makedirs(".secrets", exist_ok=True)
    os.chmod(".secrets", 0o700)  # rwx------

    os.makedirs("secure_uploads", exist_ok=True)
    os.chmod("secure_uploads", 0o700)

    os.makedirs("logs", exist_ok=True)
    os.chmod("logs", 0o700)

    logger.info("Ambiente seguro configurado")


# Inicializar gerenciadores globais
credentials = CredentialManager()
rate_limiter = RateLimiter(max_requests=30, time_window=60)
session_manager = SessionManager(timeout=3600)
file_validator = FileValidator()
input_sanitizer = InputSanitizer()
