## HEAD
# Banco-de-teste-BIG_DATA
## "Repositório de testes para ETL e análises — Banco de teste BIG_DATA"
=======
# Banco de teste BIG_DATA

![Logo do Banco de teste BIG_DATA](assets/logo.svg)

Pequeno projeto para rodar o ETL que você enviou, sem dependências do Google Colab. Inclui:

- `etl.py` — script CLI com funções de leitura, limpeza e agregação; gera CSVs de saída.
- `app.py` — app web em Streamlit para upload dos arquivos, execução do ETL e download dos CSVs gerados.
- `requirements.txt` — dependências mínimas.

```bash
python etl.py --product caminho/produto.csv --date caminho/date.csv --output resultados
# Banco de teste BIG_DATA

![Logo do Banco de teste BIG_DATA](assets/logo.svg)

Pequeno projeto para rodar o ETL que você enviou, sem dependências do Google Colab. Inclui:

- `etl.py` — script CLI com funções de leitura, limpeza e agregação; gera CSVs de saída.
- `app.py` — app web em Streamlit para upload dos arquivos, execução do ETL e download dos CSVs gerados.
- `requirements.txt` — dependências mínimas.

Como usar

1) Criar e ativar um ambiente virtual (recomendado):

```bash
python -m venv .venv
source .venv/bin/activate
```

2) Instalar dependências:

```bash
pip install -r requirements.txt
```

3) Rodar o app web (Streamlit):

```bash
streamlit run app.py
```

4) Usar o CLI (opcional):

```bash
python etl.py --product caminho/produto.csv --date caminho/date.csv --output resultados
```

Observações

- O app aceita upload de arquivos locais (ou arquivos arrastados) e processa no ambiente local — não envia dados a terceiros.
- Os CSVs gerados estão em UTF-8, separador `,` (compatível com pandas e Excel/LibreOffice). Se preferir `;` altere o código em `aggregate_and_save`.

Próximos passos possíveis

- Adicionar testes unitários simples para as funções de limpeza.
- Estender o app com filtros interativos, exportes em Excel e gráficos mais avançados.

Rodando com Docker (recomendado para segurança e reprodutibilidade)

Se preferir executar o app em um container (evita instalação local de dependências e garante ambiente reprodutível), use o Dockerfile incluído.

1) Construir a imagem:

```bash
docker build -t etl-vendas:latest .
```

2) Rodar o container (mapear porta 8501 para acessar o Streamlit no navegador):

```bash
docker run --rm -p 8501:8501 -v "$PWD/streamlit_output":/app/streamlit_output etl-vendas:latest
```

Observações:

- O comando acima monta a pasta local `streamlit_output` dentro do container para persistir os CSVs gerados.
- Use `--rm` para remover o container quando ele for parado. Remova `--rm` se quiser manter o container.
- Se estiver em Windows PowerShell, ajuste a sintaxe do caminho do volume.

Se preferir usar Docker Compose, posso adicionar um `docker-compose.yml` simples.

Título sugerido do repositório: **Banco de teste BIG_DATA**

Arquivos úteis para GitHub

- `.gitignore` — para evitar subir outputs e dependências.
- `LICENSE` — licença MIT incluída.
- `scripts/init_github.sh` — script opcional para inicializar o repositório e empurrar para o remoto (forneça a URL do repositório GitHub).

Onde está a(s) imagem(ns)?

Eu procurei por arquivos de imagem (`png`, `jpg`, `jpeg`, `gif`, `svg`) dentro do workspace atual e não encontrei nenhuma imagem presente no diretório do projeto. Se você tem uma imagem específica que quer incluir (por exemplo, um diagrama, logo ou captura de tela), adicione o arquivo ao projeto, por exemplo em `assets/` ou `docs/images/`. Depois disso eu atualizo o `README.md` para referenciar a imagem no topo do repositório.
