# Banco de teste BIG_DATA

![Logo do Banco de teste BIG_DATA](assets/logo.svg)

**Pasta local do projeto:** `JERR_BIG-DATA`

[![CI](https://github.com/Ramaswr/Banco-de-teste-BIG_DATA/actions/workflows/python-package.yml/badge.svg)](https://github.com/Ramaswr/Banco-de-teste-BIG_DATA/actions/workflows/python-package.yml)
[![License](https://img.shields.io/github/license/Ramaswr/Banco-de-teste-BIG_DATA.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Ramaswr/Banco-de-teste-BIG_DATA.svg)](https://github.com/Ramaswr/Banco-de-teste-BIG_DATA/releases)

Pequeno projeto para rodar o ETL que você enviou, sem dependências do Google Colab. Inclui:

- `etl.py` — script CLI com funções de leitura, limpeza e agregação; gera CSVs de saída.
- `app.py` — app web em Streamlit para upload dos arquivos, execução do ETL e download dos CSVs gerados.
- `requirements.txt` — dependências mínimas.

## 🚀 Início Rápido (1 comando)

Se prefere uma forma rápida e automática, execute:

```bash
./run.sh
```

### Modo Público (execução pública, código em somente leitura)

Se desejar expor o app na rede (por exemplo em uma LAN ou servidor público) mantendo o código e a estrutura em modo somente leitura para outros usuários, siga os passos abaixo.

1. Torne o app público (bind em 0.0.0.0) e proteja com autenticação:

```bash
# Iniciar em modo público (o app ficará acessível em todas as interfaces)
PUBLIC_MODE=1 ./run.sh
```

1. Ajuste permissões para deixar arquivos do projeto legíveis (somente leitura para outros) e proteger diretórios sensíveis:

```bash
# Executar script que aplica permissões seguras
./make_public_readonly.sh
```

**Credenciais de produção**:

- Configure `.secrets/credentials.json` antes de expor o app em produção. Um exemplo está em `.secrets/credentials.example.json`.
- Para gerar um arquivo de credenciais seguro, rode:

```bash
python scripts/create_credentials.py --username admin --role super_admin
```

O comando pedirá a senha e gravará o arquivo `.secrets/credentials.json` com permissão `600`.

1. Recomendado (IMPORTANTE para produção):

- Coloque o app atrás de um reverse-proxy (nginx/caddy) e habilite HTTPS/TLS.
- Configure firewall para limitar IPs que podem acessar o serviço.
- Não compartilhe `.secrets/credentials.json`; ele permanece protegido (modo 600).

Com essa configuração:

- O app exige login (`Jerr` + sua senha) para executar funcionalidades.
- Usuários externos poderão acessar a interface e executar o app (se autenticados), mas não poderão alterar os arquivos do projeto (apenas leitura).
- Diretórios sensíveis (`.secrets`, `secure_uploads`, `logs`) têm permissões restritas (700).

----

Este script irá:

- ✓ Criar ambiente virtual (se necessário)
- ✓ Instalar todas as dependências
- ✓ Abrir o navegador automaticamente em [http://localhost:8501](http://localhost:8501)
- ✓ Iniciar o app Streamlit

**Pronto em 1 linha!**

## Como usar

### 1) Criar e ativar um ambiente virtual (recomendado)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Instalar dependências

```bash
pip install -r requirements.txt
```

### 3) Rodar o app web (Streamlit)

```bash
streamlit run app.py
```

### 4) Usar o CLI (opcional)

```bash
python etl.py --product caminho/produto.csv --date caminho/date.csv --output resultados
```

## Observações

- O app aceita upload de arquivos locais (ou arquivos arrastados) e processa no ambiente local — não envia dados a terceiros.
- Os CSVs gerados estão em UTF-8, separador `,` (compatível com pandas e Excel/LibreOffice). Se preferir `;` altere o código em `aggregate_and_save`.

## Próximos passos possíveis

- Adicionar testes unitários simples para as funções de limpeza.
- Estender o app com filtros interativos, exportes em Excel e gráficos mais avançados.

## 🐳 Rodando com Docker

Se preferir executar o app em um container (evita instalação local de dependências e garante ambiente reprodutível), use o Dockerfile incluído.

### 1) Construir a imagem

```bash
docker build -t etl-vendas:latest .
```

### 2) Rodar o container

```bash
docker run --rm -p 8501:8501 -v "$PWD/streamlit_output":/app/streamlit_output etl-vendas:latest
```

Observações:

- O comando acima monta a pasta local `streamlit_output` dentro do container para persistir os CSVs gerados.
- Use `--rm` para remover o container quando ele for parado.
- Se estiver em Windows PowerShell, ajuste a sintaxe do caminho do volume.

## 📦 Arquivos do Projeto

- `.gitignore` — para evitar subir outputs e dependências.
- `LICENSE` — licença MIT incluída.
- `scripts/init_github.sh` — script opcional para inicializar o repositório e empurrar para o remoto.
- `run.sh` — script para executar o app com uma linha (instala deps + abre navegador).
- `create_release.py` e `create_release.sh` — scripts para criar Release no GitHub.

## 🔒 Verificação de integridade (SHA256)

Para garantir que o arquivo `zip_Jerr.js` não foi corrompido durante o download:

**Linux/Mac:**

```bash
sha256sum -c zip_Jerr.js.sha256
```

**Windows (PowerShell):**

```powershell
certUtil -hashfile zip_Jerr.js SHA256
```

Se o checksum corresponder, o arquivo está íntegro e pronto para uso/análise.

## 📖 Licença

MIT License — veja [LICENSE](LICENSE) para detalhes.

## Executar no Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/)
