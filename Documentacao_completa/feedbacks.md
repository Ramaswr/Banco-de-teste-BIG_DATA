
# Feedbacks Rápidos do Projeto

1. **Experiência do Usuário**
   - O tema Matrix diferencia visualmente o dashboard, mas avalie um "modo claro" alternativo para apresentações executivas.
   - Inserir tooltips explicando as métricas em `produto_agg`, `categoria_agg` e `daily` ajudaria novos analistas.

2. **Processo ETL**
   - Criar testes unitários para `clean_product_df` e `clean_date_df` garantiria estabilidade ao receber novos layouts de CSV.
   - O parser BIN poderia validar checksums antes de aceitar os registros para mitigar uploads corrompidos.

3. **Segurança**
   - Automatize a rotação de senhas e tokens utilizados em `users.py` (por exemplo, via hash salgado + expiração automática).
   - Considere habilitar MFA por SMS/e-mail usando os utilitários já presentes em `utils/`.

4. **Observabilidade**
   - Centralizar logs (Elastic/CloudWatch) permitiria rastrear auditorias e facilitar investigações de incidentes.
   - Um painel simples com status dos jobs ETL pode ser exposto no Streamlit para facilitar o suporte.

5. **Segurança Proativa / IA**
   - Integrar o botão "Assistente IA" ao manual de operação, reforçando que ele apenas guia e não executa ações.
   - Expandir o scanner de links/ZIP para registrar indicadores em `security_events` e exportar relatórios periódicos.
   - Automatizar a execução de `scripts/run_security_scans.sh` no pipeline (Bandit + Gitleaks) antes de cada release.

6. **Governança de Dados**
   - Documentar o dicionário de dados dos arquivos CSV/BIN em `ETL_INTEGRATION_FEEDBACK.md` reduz tempo de onboarding.
   - Versionar transformações críticas (por exemplo, via `great_expectations`) garantiria confiabilidade nas cargas históricas.
