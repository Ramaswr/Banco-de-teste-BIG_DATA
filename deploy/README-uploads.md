Uploads e limites

Resumo
- O aplicativo aceita uploads com limite estrito de 10 MB por arquivo.
- Para datasets maiores ("Quantums" de 1 TB), use upload multipart/presigned para object storage (S3/MinIO) e processamento em background.

Validação aplicada
- `app.py`: validação imediata do lado do cliente (após upload) para recusar arquivos >10MB com mensagem amigável.
- `security.py`: `FileValidator.MAX_FILE_SIZE` ajustado para 10 MB e verificação robusta de tamanho.
- Reverse-proxy: Recomendamos configurar `client_max_body_size 10M;` no Nginx para bloquear uploads na borda.

Fluxo recomendado para grandes volumes
1. Usuário cria job no app → recebe URL presigned para upload multipart (S3/MinIO).
2. Cliente/CLI faz upload multipart diretamente para o storage (evita passar pelo app).
3. Ao finalizar, storage notifica o backend (webhook) ou o cliente solicita processamento.
4. Worker (Dask/Ray/Spark) faz processamento em background, escreve resultados particionados em Parquet/CSV.
5. App apresenta preview e links de download menores.

Executando workers com limites de recurso
- Não recomendamos matar outros processos do sistema. Em vez disso, rode seus workers com limites de CPU/memória.
- Use `deploy/run_under_cgroup.sh` para iniciar um processo sob `systemd-run --scope -p CPUQuota=50%` (requer sudo).

Exemplo:
```bash
# rodar worker com quota de CPU
cd /home/jerr/Downloads/Projeto extencionista BIG_DATA
sudo ./deploy/run_under_cgroup.sh "python3 worker_daemon.py"
```

Opções alternadas sem sudo
- `systemd --user` units podem ser usadas para rodar timers/serviços no escopo do usuário.
- Cron do usuário também é uma alternativa simples para tasks periódicas.

Segurança do token
- Armazene o token do DuckDNS em `.secrets/duckdns.env` com `chmod 600`.
- Não comite este arquivo no repositório.

Notas finais
- Essas mudanças aplicam defesa em profundidade: validação no cliente, validação no backend e recomendação para limites no proxy.
- Para suportar consulta/analítica em tempo real sobre arquivos de grande volume, adote arquitetura de object storage + processamento distribuído.
