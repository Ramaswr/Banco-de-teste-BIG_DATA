# Documentação Completa — Plataforma BIG DATA

## 1. Visão Geral
A solução integra ingestão de dados de vendas (CSV e BIN), processamento ETL e visualização interativa com Streamlit. O objetivo é permitir que equipes comerciais façam upload diário dos arquivos, executem limpezas padronizadas, gerem agregações (produtos, categorias e série temporal) e baixem os resultados já validados.

## 2. Arquitetura Lógica
1. **Interface (Streamlit / `app.py`)**: autenticação, upload dos arquivos, escolha de separadores, disparo do ETL e download dos relatórios.
2. **Camada de Segurança (`security.py`, `users.py`, `setup_security.sh`)**: provisiona usuários, criptografa senhas, registra atividades e cria o ambiente seguro antes de cada sessão.
3. **Motor ETL (`etl.py`, `etl_batch/etl_core.py`, `etl_batch/etl_integration_ui.py`)**: contém o `QuantumBinaryParser`, limpeza, validação e agregação, gravando saídas em `streamlit_output/`.
4. **Utilidades (`utils/`)**: envio de alertas (email/SMS), validação de senha, notificações para incidentes.
5. **Infra & Deploy (`deploy/`, `Dockerfile`, `run.sh`)**: scripts para executar em hosts Linux, contêineres e serviços de borda (Caddy/Nginx, DuckDNS, systemd).

## 3. Tecnologias Utilizadas
| Camada | Tecnologias |
| --- | --- |
| Front-end | Streamlit, CSS customizado (tema Matrix) |
| Back-end | Python 3.10+, pandas, numpy, python-pptx (documentação), utilitários próprios |
| Segurança | `bcrypt`, logging estruturado, scripts shell de hardening |
| DevOps | Docker, systemd, Caddy/Nginx, scripts Bash |

## 4. Fluxo ETL Resumido
1. Upload dos CSVs (produto, data) ou BIN (admin).
2. Funções `read_sales_csv`, `clean_product_df` e `clean_date_df` padronizam os dados.
3. `aggregate_and_save` gera DataFrames agregados (`produto_agg`, `categoria_agg`, `daily`).
4. Arquivos resultantes são salvos em `streamlit_output/` e oferecidos para download.

## 5. Métodos Principais
- **`read_sales_csv`**: leitura com separador configurável, validação de schema mínimo.
- **`clean_product_df` / `clean_date_df`**: normaliza colunas, remove duplicidades e converte tipos numéricos.
- **`QuantumBinaryParser.parse_records`**: decodifica lotes BIN enviados por administradores.
- **`aggregate_and_save`**: aplica `groupby`, calcula métricas e retorna um dicionário de DataFrames com paths exportados.
- **`security.bootstrap_secure_environment`** (referência): garante variáveis de ambiente e logging antes da UI subir.

## 6. Estrutura de Pastas (trechos relevantes)
```
app.py                         # Front-end Streamlit principal
security.py / users.py         # Autenticação e auditoria
etl.py                         # Orquestrador ETL rápido
etl_batch/etl_core.py          # Parser BIN + pipeline batch
utils/alerts.py|mailer.py      # Integrações externas
streamlit_output/              # Artefatos gerados
Documentacao_completa/         # (Pasta atual) documentação oficial
```

## 7. Operação no Dia a Dia
1. Ative a venv e instale dependências: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
2. Execute o front-end: `./.venv/bin/streamlit run app.py`.
3. Faça login (usuário cadastrado via `users.py`).
4. Carregue arquivos, revise prévias e baixe relatórios.
5. Para automações, utilize `deploy/run-caddy-on-host.sh` ou `systemd/streamlit-jerr.service`.

## 8. Boas Práticas e Monitoramento
- Gere logs via `logging` (já configurado em `security.py`).
- Utilize `secure_uploads/` para armazenamento temporário de arquivos sensíveis.
- Reforce backups dos CSVs em `streamlit_output/` e sincronia com `drive_helper.py` quando necessário.

## 9. Próximos Passos Recomendados
1. Adicionar testes automatizados para `QuantumBinaryParser` e funções de limpeza.
2. Integrar autenticação multifator usando `utils/sms.py`.
3. Publicar imagem Docker automatizada usando `create_release.py`.

---
Documentação elaborada em 19/11/2025 para suportar apresentações e auditorias técnicas.
