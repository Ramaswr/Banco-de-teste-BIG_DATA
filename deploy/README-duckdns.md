Uso do DuckDNS (atualizador automático)

Passos rápidos:

1. Crie o arquivo de segredo local em `.secrets/duckdns.env` com conteúdo:

```
DOMAIN=rama01rodriguez.duckdns.org
TOKEN=fa809ba8-e26a-4e88-885d-892f20a6f258
EMAIL=rama01rodriguez@gmail.com
ACCOUNT=Ramaswr@github
```

2. Proteja o arquivo:

```
chmod 600 .secrets/duckdns.env
```

3. Ative o atualizador (systemd):

```
sudo cp deploy/duckdns/duckdns-updater.service /etc/systemd/system/
sudo cp deploy/duckdns/duckdns-updater.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now duckdns-updater.timer
```

4. Verifique o log:

```
tail -n 50 deploy/duckdns/duckdns-update.log
```

Segurança:
- Não commit o arquivo `.secrets/duckdns.env` no Git. Ele já está listado no `.gitignore` do projeto.
- O token deve ser mantido com permissão `600`.

Observação: Antes de rodar o `setup_caddy_noninteractive.sh`, confirme que o domínio aponta para o IP público do servidor onde os scripts serão executados.
