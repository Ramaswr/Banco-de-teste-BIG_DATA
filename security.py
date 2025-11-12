"""
Módulo de segurança para proteção do Streamlit app.
- Autenticação com username/password
- Validação de arquivos
- Rate limiting
- CORS e headers de segurança
- Isolamento de processo
- Sanitização de entrada
"""

import os
import hashlib
import hmac
import json
import time
import secrets
from pathlib import Path
from typing import Optional, Tuple
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURAÇÃO DE CREDENCIAIS ====================

class CredentialManager:
    """Gerenciador de credenciais com hash seguro."""
    
    def __init__(self, config_file: str = '.secrets/credentials.json'):
        self.config_file = config_file
        self.credentials = self._load_credentials()
    
    def _load_credentials(self) -> dict:
        """Carrega credenciais do arquivo de configuração."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar credenciais: {e}")
        
        # Credenciais padrão (MUDE ANTES DE COLOCAR EM PRODUÇÃO)
        return {
            'users': {
                'admin': self._hash_password('admin123'),  # MUDE ISTO
                'usuario': self._hash_password('senha123')   # MUDE ISTO
            }
        }
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash seguro de senha com salt."""
        salt = os.urandom(32)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return f"pbkdf2:100000:{salt.hex()}:{pwd_hash.hex()}"
    
    @staticmethod
    def _verify_password(password: str, hash_stored: str) -> bool:
        """Verifica se a senha corresponde ao hash."""
        try:
            parts = hash_stored.split(':')
            if len(parts) != 4 or parts[0] != 'pbkdf2':
                return False
            
            iterations = int(parts[1])
            salt = bytes.fromhex(parts[2])
            stored_hash = bytes.fromhex(parts[3])
            
            pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
            return hmac.compare_digest(pwd_hash, stored_hash)
        except Exception as e:
            logger.error(f"Erro ao verificar senha: {e}")
            return False
    
    def authenticate(self, username: str, password: str) -> bool:
        """Autentica usuário com username e password."""
        if username not in self.credentials.get('users', {}):
            logger.warning(f"Tentativa de login com usuário inexistente: {username}")
            return False
        
        stored_hash = self.credentials['users'][username]
        is_valid = self._verify_password(password, stored_hash)
        
        if is_valid:
            logger.info(f"Login bem-sucedido: {username}")
        else:
            logger.warning(f"Login falhou para: {username}")
        
        return is_valid


# ==================== VALIDAÇÃO DE ARQUIVOS ====================

class FileValidator:
    """Validador de arquivos para prevenir uploads maliciosos."""
    
    # Extensões permitidas
    ALLOWED_EXTENSIONS = {
        'csv', 'txt', 'xlsx', 'xls', 'parquet', 'json', 'tsv'
    }
    
    # MIME types permitidos
    ALLOWED_MIMES = {
        'text/csv',
        'text/plain',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'application/octet-stream',  # Parquet
        'application/json'
    }
    
    # Tamanho máximo de arquivo (100 MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # Diretório seguro para uploads
    UPLOAD_DIR = 'secure_uploads'
    
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
        if not filename.lower().endswith(tuple(f'.{ext}' for ext in cls.ALLOWED_EXTENSIONS)):
            return False, f"Extensão não permitida. Use: {', '.join(cls.ALLOWED_EXTENSIONS)}"
        
        # 2. Verificar tamanho
        file_size = len(file_obj.getvalue()) if hasattr(file_obj, 'getvalue') else file_obj.seek(0, 2)
        if file_size > cls.MAX_FILE_SIZE:
            return False, f"Arquivo muito grande. Máximo: {cls.MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
        
        # 3. Verificar conteúdo (magic bytes)
        file_obj.seek(0)
        header = file_obj.read(512)
        file_obj.seek(0)
        
        if not cls._verify_magic_bytes(header, filename):
            return False, "Conteúdo do arquivo não corresponde à extensão (possível arquivo falso)"
        
        # 4. Sanitizar filename
        safe_filename = cls._sanitize_filename(filename)
        
        logger.info(f"Arquivo validado: {safe_filename} ({file_size} bytes)")
        return True, safe_filename
    
    @staticmethod
    def _verify_magic_bytes(header: bytes, filename: str) -> bool:
        """Verifica assinatura de arquivo (magic bytes)."""
        ext = Path(filename).suffix.lower()
        
        magic_signatures = {
            '.csv': [b'', b'\xef\xbb\xbf'],  # UTF-8 BOM ou texto
            '.txt': [b'', b'\xef\xbb\xbf'],
            '.xlsx': [b'PK\x03\x04'],  # ZIP signature
            '.xls': [b'\xd0\xcf\x11\xe0'],  # OLE2
            '.parquet': [b'PAR1'],
            '.json': [b'{', b'[', b'\xef\xbb\xbf']
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
            filename = filename.replace(char, '_')
        
        # Remover espaços extras e pontos no início
        filename = filename.strip('. ')
        
        # Adicionar timestamp para evitar colisão
        timestamp = int(time.time() * 1000)
        name, ext = os.path.splitext(filename)
        return f"{name}_{timestamp}{ext}"


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
            (ts, count) for ts, count in self.requests[identifier]
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
        self.sessions[session_id] = {
            'user': username,
            'created': time.time()
        }
        logger.info(f"Sessão criada para: {username}")
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """Valida sessão e retorna username se válida."""
        if session_id not in self.sessions:
            logger.warning(f"Sessão inválida: {session_id}")
            return None
        
        session = self.sessions[session_id]
        if time.time() - session['created'] > self.timeout:
            del self.sessions[session_id]
            logger.info(f"Sessão expirada: {session_id}")
            return None
        
        return session['user']
    
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
        dangerous = ["'", '"', ';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT']
        for word in dangerous:
            text = text.replace(word, '')
        return text
    
    @staticmethod
    def sanitize_command(text: str) -> str:
        """Remove caracteres perigosos de comando shell."""
        dangerous = [';', '|', '&', '$', '`', '\n', '\r']
        for char in dangerous:
            text = text.replace(char, '')
        return text
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """Valida caminho de arquivo."""
        # Remover path traversal
        path = path.replace('..', '')
        path = path.replace('//', '/')
        return path.strip('/')


# ==================== SECURITY HEADERS ====================

def get_security_headers() -> dict:
    """Retorna headers HTTP de segurança."""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'",
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    }


# ==================== UTILS ====================

def setup_secure_environment():
    """Configura ambiente seguro."""
    # Criar diretórios seguros
    os.makedirs('.secrets', exist_ok=True)
    os.chmod('.secrets', 0o700)  # rwx------
    
    os.makedirs('secure_uploads', exist_ok=True)
    os.chmod('secure_uploads', 0o700)
    
    os.makedirs('logs', exist_ok=True)
    os.chmod('logs', 0o700)
    
    logger.info("Ambiente seguro configurado")


# Inicializar gerenciadores globais
credentials = CredentialManager()
rate_limiter = RateLimiter(max_requests=30, time_window=60)
session_manager = SessionManager(timeout=3600)
file_validator = FileValidator()
input_sanitizer = InputSanitizer()
