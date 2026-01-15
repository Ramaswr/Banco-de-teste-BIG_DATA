# 🛡️ Guia de Segurança

## Visão Geral de Proteção

Este projeto implementa múltiplas camadas de segurança para proteger contra acessos não autorizados, malware e ataques:

---

## 1️⃣ Autenticação

### Credenciais Padrão (DEMO)

```text
👤 Username: admin
🔑 Senha: admin123

👤 Username: usuario
🔑 Senha: senha123
```

⚠️ **IMPORTANTE:** Altere estas credenciais ANTES de colocar em produção!

### Alterar Credenciais

Edite `security.py` e modifique a função `_load_credentials()`:

```python
'users': {
    'admin': self._hash_password('SUA_SENHA_FORTE_AQUI'),
    'usuario': self._hash_password('OUTRA_SENHA_FORTE')
}
```

As senhas são hashadas com **PBKDF2-SHA256** com 100.000 iterações.

---

## 2️⃣ Validação de Arquivos

### Tipos Permitidos

- CSV, TXT, XLSX, XLS, Parquet, JSON, TSV

### Proteções

✅ Verificação de extensão de arquivo
✅ Limite de tamanho: 100 MB
✅ Validação de assinatura (magic bytes)
✅ Sanitização de nome de arquivo
✅ Prevenção de path traversal
✅ Isolamento em diretório seguro (`secure_uploads/`)

### Arquivos Rejeitados

- Extensões perigosas (.exe, .sh, .bat, .dll)
- Tamanho > 100 MB
- Magic bytes inválidos (arquivo falsificado)
- Nomes com `../` (path traversal)

---

## 3️⃣ Rate Limiting

### Proteção contra Brute Force

- **Limite:** 30 requisições por minuto (por usuário/IP)
- **Timeout:** 60 segundos
- **Ação:** Bloqueia requisições excedentes

### Exemplo

```text
Tentativa 1-30: ✅ Aceito
Tentativa 31: ❌ Bloqueado
(Aguarde 1 minuto)
```

---

## 4️⃣ Gerenciamento de Sessão

### Timeout

- **Duração:** 1 hora (3.600 segundos)
- **Ação:** Logout automático após expiração
- **ID de Sessão:** Token único de 32 caracteres (secrets.token_urlsafe)

### Segurança de Sessão

- Tokens criptograficamente aleatórios
- Sem reutilização de tokens
- Destruição ao logout

---

## 5️⃣ Logging e Auditoria

### Arquivo: `security.log`

Todos os eventos de segurança são registrados:

```text
2025-11-12 10:30:45 - Login bem-sucedido: admin
2025-11-12 10:31:15 - Arquivo validado: dados_1234567890.csv (5.2 MB)
2025-11-12 10:32:00 - Rate limit atingido para: 192.168.1.100
2025-11-12 10:45:00 - Sessão expirada: abc123def456...
```

### Como Revisar Logs

```bash
# Últimas 20 linhas
tail -20 security.log

# Procurar por eventos de login falhos
grep "falhou" security.log

# Ver tentativas bloqueadas
grep "Rate limit" security.log
```

---

## 6️⃣ Sanitização de Entrada

### Proteção contra Injeção

#### SQL Injection

Caracteres perigosos removidos:

- `'`, `"`, `;`, `--`, `/*`, `*/`
- `DROP`, `DELETE`, `INSERT`

#### Command Injection

Caracteres perigosos removidos:

- `;`, `|`, `&`, `$`, `` ` ``, `\n`

#### Path Traversal

Caracteres perigosos removidos:

- `..`, `//`

---

## 7️⃣ Estrutura de Diretórios Segura

```text
Projeto/
├── app.py                 # Aplicação principal
├── security.py            # Módulo de segurança
├── security.log           # Log de auditoria (gerado)
├── .secrets/              # Modo 700 (rwx------)
│   └── credentials.json   # Credenciais criptografadas
├── secure_uploads/        # Modo 700 (rwx------)
│   └── dados_1234567890.csv
└── logs/                  # Modo 700 (rwx------)
```

### Permissões

```bash
# Visualizar permissões
ls -lah .secrets/
ls -lah secure_uploads/

# Deve mostrar: drwx------
```

---

## 🚀 Checklist de Produção

Antes de colocar em produção, verifique:

- [ ] ✅ Alterou credenciais padrão em `security.py`
- [ ] ✅ Configurou `.secrets/credentials.json` com senhas fortes
- [ ] ✅ Habilitou HTTPS (não use HTTP em produção)
- [ ] ✅ Configurou firewall para bloquear acesso direto
- [ ] ✅ Revisou `security.log` para detectar atividades suspeitas
- [ ] ✅ Configurou backup de credenciais seguro
- [ ] ✅ Testou timeout de sessão
- [ ] ✅ Testou validação de arquivo (tente upload de .exe)
- [ ] ✅ Testou rate limiting (>30 requisições)
- [ ] ✅ Configurou CORS adequadamente (se usar API)

---

## 🔧 Configuração Avançada

### Aumentar Rate Limit

Em `app.py`, modifique:

```python
rate_limiter = RateLimiter(max_requests=100, time_window=60)
```

### Aumentar Timeout de Sessão

Em `app.py`:

```python
session_manager = SessionManager(timeout=7200)  # 2 horas
```

### Alterar Limite de Tamanho de Arquivo

Em `security.py`:

```python
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB
```

### Adicionar Tipo de Arquivo Permitido

Em `security.py`:

```python
ALLOWED_EXTENSIONS = {'csv', 'txt', 'xlsx', 'xls', 'parquet', 'json', 'tsv', 'pdf'}
```

---

## ⚠️ Avisos de Segurança

### NÃO FAÇA

❌ Não commita `.secrets/` no Git
❌ Não expõe `security.log` publicamente
❌ Não use HTTP em produção
❌ Não reutilize senhas de outros serviços
❌ Não compartilhe credenciais por email/chat
❌ Não deixe credenciais padrão em produção

### FAÇA

✅ Faça backup seguro de credenciais
✅ Revise logs regularmente
✅ Atualize dependências Python regularmente
✅ Use senhas fortes (>12 caracteres, mix de tipos)
✅ Configure 2FA se disponível
✅ Monitore atividades suspeitas
✅ Execute verificações de segurança periodicamente

---

## 🆘 Resposta a Incidentes

### 1. Suspeita de Acesso Não Autorizado

```bash
# Revise os últimos acessos
grep "Login" security.log | tail -20

# Procure por tentativas falhas
grep "falhou" security.log | wc -l

# Revise uploads suspeitos
ls -lah secure_uploads/
```

### 2. Ataque de Brute Force

O sistema bloqueia automaticamente:

```bash
# Verificar bloqueios
grep "Rate limit" security.log | tail -10
```

### 3. Upload de Arquivo Malicioso

O arquivo é rejeitado automaticamente:

```bash
# Verificar rejeições
grep "Arquivo rejeitado" security.log
```

---

## 📚 Recursos Adicionais

- **OWASP Top 10:** <https://owasp.org/www-project-top-ten/>
- **Python Security:** <https://python-security.readthedocs.io/>
- **Streamlit Security:** <https://docs.streamlit.io/knowledge-base/using-streamlit/deploy>

---

## 📞 Suporte

Para questões de segurança:

1. Revise este arquivo
2. Consulte os logs em `security.log`
3. Teste as proteções localmente

**Desenvolvido com ❤️ para segurança** 🔒
