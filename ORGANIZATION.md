# Organização de Pastas do Projeto

Este documento descreve a estrutura profissional do projeto Jerr_BIG-DATA.

## 📁 Estrutura Principal

```
Banco-de-teste-BIG_DATA/
├── assets/                    # Recursos visuais e estáticos
│   ├── logo.svg              # Logotipo do projeto
│   └── background-pattern.svg # Padrão de fundo otimizado (SVG leve)
│
├── deploy/                    # Configurações de deployment
│   ├── nginx/                # Configurações Nginx
│   ├── systemd/              # Scripts systemd
│   ├── duckdns/              # Atualizador DuckDNS para DNS dinâmico
│   ├── Caddyfile             # Configuração Caddy reverse proxy
│   └── *.sh                  # Scripts de setup e deployment
│
├── scripts/                   # Scripts utilitários
│   ├── init_github.sh        # Inicializar repositório GitHub
│   └── user_create.py        # Criar usuários do sistema
│
├── utils/                     # Módulos utilitários
│   └── alerts.py             # Sistema de alertas e notificações
│
├── z_ip/                      # Arquivos zipados/backup (legado)
│
├── .github/                   # Configurações GitHub
│   └── workflows/            # GitHub Actions CI/CD
│       └── python-package.yml # Pipeline de testes e linting
│
├── app.py                     # 🚀 Aplicação principal Streamlit
├── etl.py                     # Módulo ETL (Extract, Transform, Load)
├── ocr.py                     # Módulo OCR e processamento de PDF
├── security.py                # Sistema de segurança e autenticação
├── users.py                   # Gerenciamento de usuários
├── drive_helper.py            # Helpers para Google Drive
│
├── requirements.txt           # Dependências Python
├── run.sh                     # Script de execução rápida
├── setup_security.sh          # Configurar ambiente seguro
├── make_public_readonly.sh    # Tornar arquivos read-only
│
├── README.md                  # Documentação principal
├── SECURITY.md                # Política de segurança
├── SECURITY_IMPLEMENTATION.md # Detalhes de implementação de segurança
└── LICENSE                    # Licença MIT

```

## 📂 Descrição dos Diretórios

### `/assets/` - Recursos Visuais
Contém recursos estáticos como logos, ícones e imagens de fundo.
- **Otimizado**: Usa SVG para gráficos vetoriais leves
- **Performance**: Background pattern tem apenas ~400 bytes

### `/deploy/` - Configurações de Deployment
Tudo relacionado a implantar o aplicativo em produção.
- **Nginx/Caddy**: Configurações de reverse proxy
- **Systemd**: Scripts para executar como serviço
- **DuckDNS**: Atualizador de DNS dinâmico

### `/scripts/` - Scripts Auxiliares
Scripts para automação e tarefas administrativas.
- Inicialização de repositório
- Gerenciamento de usuários
- Tarefas de manutenção

### `/utils/` - Utilitários
Módulos Python reutilizáveis.
- Sistema de alertas
- Funções auxiliares
- Helpers comuns

### `/z_ip/` - Arquivos Legados
Contém backups e versões antigas zipadas.

## 🔐 Diretórios Dinâmicos (Criados em Runtime)

Estes diretórios são criados automaticamente quando o aplicativo é executado:

- **`secure_uploads/`** - Uploads de usuários (criado automaticamente, 700 permissões)
- **`.secrets/`** - Credenciais e dados sensíveis (700 permissões)
- **`logs/`** - Arquivos de log (700 permissões)
- **`streamlit_output/`** - Saídas de processamento ETL

## 📄 Arquivos Principais

### Aplicação Core
- **`app.py`** - Aplicação Streamlit principal com dashboard interativo
- **`etl.py`** - Pipeline ETL para processamento de dados
- **`ocr.py`** - OCR para imagens e extração de tabelas PDF

### Segurança
- **`security.py`** - Sistema completo de segurança (auth, validação, rate limiting)
- **`users.py`** - Gerenciamento de usuários e permissões

### Configuração
- **`requirements.txt`** - Todas as dependências Python
- **`.env.security`** - Variáveis de ambiente de segurança

## 🎯 Características da Organização

### ✅ Profissional
- Separação clara de responsabilidades
- Código core separado de configurações
- Scripts de deployment isolados

### ✅ Segura
- Diretórios sensíveis com permissões restritas
- Credenciais fora do controle de versão
- Validação de arquivos upload

### ✅ Manutenível
- Documentação clara
- Estrutura intuitiva
- Fácil localização de componentes

## 🚀 Fluxo de Trabalho

1. **Desenvolvimento**: Editar arquivos em `/` raiz
2. **Testes**: Executar `./run.sh` localmente
3. **Deploy**: Usar scripts em `/deploy/`
4. **Manutenção**: Usar scripts em `/scripts/`

## 📋 Boas Práticas

- ✅ Sempre adicionar novos recursos estáticos em `/assets/`
- ✅ Scripts de automação vão em `/scripts/`
- ✅ Configurações de deploy em `/deploy/`
- ✅ Utilitários reutilizáveis em `/utils/`
- ✅ Manter `.gitignore` atualizado para excluir dados sensíveis

## 🔍 Localização Rápida

| Preciso de... | Vá para... |
|---------------|-----------|
| Interface principal | `app.py` |
| Processar dados CSV | `etl.py` |
| OCR ou PDF | `ocr.py` |
| Segurança/Auth | `security.py` |
| Usuários | `users.py` |
| Logo/Imagens | `assets/` |
| Deploy configs | `deploy/` |
| Scripts úteis | `scripts/` |

---

**Última atualização**: 2025-11-19
**Versão**: 1.0
