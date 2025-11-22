# Deploy seguro com HTTPS — Jerr_BIG-DATE

Este documento descreve passos recomendados para colocar o app `Jerr_BIG-DATE` em produção protegendo a rede com HTTPS.

Opções recomendadas (escolha uma):

A) Usar Caddy (recomendado, configura TLS automaticamente)
B) Usar Nginx + Certbot (Let's Encrypt)

Pré-requisitos:

- Servidor com IP público e um domínio (ex.: `yourdomain.example`)
- Entrada DNS `A` apontando para o IP do servidor
- Acesso root (sudo) ao servidor para instalar serviços e colocar configs

---

1) Configurar o serviço do Streamlit

- Copie o unit systemd para `/etc/systemd/system/streamlit-jerr.service` (ajuste caminhos se diferente):

```bash
sudo cp deploy/systemd/streamlit-jerr.service /etc/systemd/system/streamlit-jerr.service
sudo systemctl daemon-reload
sudo systemctl enable --now streamlit-jerr.service
sudo systemctl status streamlit-jerr.service
```

Isto executa o Streamlit ligado somente a `127.0.0.1:8501`, o que é seguro para ser colocado atrás de um reverse-proxy.

2) Opção A — Caddy (auto TLS — mais simples)

- Instalar Caddy (https://caddyserver.com/docs/install)
- Criar `/etc/caddy/Caddyfile` com o conteúdo em `deploy/Caddyfile` substituindo `YOUR_DOMAIN` e `you@example.com`.
- Reiniciar Caddy:

```bash
sudo systemctl reload caddy
sudo journalctl -u caddy -f
```

Caddy automaticamente obtém certificados e serve HTTPS, com proxy reverso para `localhost:8501`.

3) Opção B — Nginx + Certbot

- Copie `deploy/nginx/jerr_big_date.conf` para `/etc/nginx/sites-available/jerr_big_date` e ajuste `YOUR_DOMAIN`.

```bash
sudo cp deploy/nginx/jerr_big_date.conf /etc/nginx/sites-available/jerr_big_date
sudo ln -s /etc/nginx/sites-available/jerr_big_date /etc/nginx/sites-enabled/jerr_big_date
sudo nginx -t
sudo systemctl reload nginx
```

- Obtenha certificados com certbot:

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN -d www.YOUR_DOMAIN
```

- Verifique renovação automática:

```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

4) Firewall (UFW exemplo)

```bash
# permitir SSH
sudo ufw allow OpenSSH
# permitir HTTPS e HTTP (apenas se for servidor público)
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp
# (opcional) bloquear acesso ao porto do streamlit diretamente (8501)
sudo ufw deny 8501/tcp

sudo ufw enable
sudo ufw status
```

5) Boas práticas finais

- Nunca exponha a pasta do projeto diretamente como webroot do Nginx — use o proxy para encaminhar para localhost.
- Proteja `.secrets/` com permissão 700 e não commite no Git.
- Monitore `security.log` e os logs do systemd (`journalctl -u streamlit-jerr -f`).
- Considere usar fail2ban para proteger contra tentativas repetidas de login.

6) Testes

- Acesse `https://YOUR_DOMAIN` após apontar DNS e configurar proxy/TLS.
- Teste login com usuário `Jerr` e sua senha.
- Verifique que o código não é editável por usuários externos (permissionamento aplicado).

---

Se quiser, eu posso gerar os comandos prontos para você copiar/colar no servidor (ex.: passo a passo para Caddy ou Nginx + certbot). Diga qual opção prefere (Caddy ou Nginx+Certbot).