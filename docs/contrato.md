# Contrato entre web e agent

Versão: 0.1.0

Fonte da verdade da comunicação entre `web` e `agent`. Mudou aqui, muda na spec da versão antes do código.

## Servidores

| Servidor | Endereço | Protocolo | Serve |
|---|---|---|---|
| Console | `127.0.0.1:8080` | HTTP | página `/`, `/assets/*`, `/api/*` |
| Celular | `<ip-da-lan>:8443` | HTTPS (certificado autoassinado) | página `/cam`, `/assets/*`, `/api/*` |

As duas páginas são o mesmo `index.html` do build do web; a superfície é escolhida pelo caminho no navegador.

## Formato de erro

Toda resposta de erro, nos dois servidores:

```json
{"error": {"code": "not_same_network", "message": "The request does not come from the local network."}}
```

O cliente decide pelo `code`, nunca pela `message`. O texto mostrado ao usuário vem de `locales/<idioma>.json`, chave `errors.<code>`, com `errors.unknown` para código desconhecido.

| Código | Status | Quando |
|---|---|---|
| `not_same_network` | 403 | servidor do celular: IP de origem fora da sub-rede da LAN |
| `invalid_host` | 400 | cabeçalho `Host` fora da lista permitida do servidor |
| `web_not_built` | 503 | página pedida sem build do web presente |
| `not_found` | 404 | rota inexistente |
| `method_not_allowed` | 405 | método não suportado na rota |
| `invalid_request` | 422 | corpo ou parâmetros inválidos |
| `internal_error` | 500 | erro inesperado; a mensagem nunca traz detalhe interno |

Erro de rede no cliente (agente fora do ar) usa o código local `network_error`, que não vem do servidor.

## Hosts permitidos

- Console: `127.0.0.1:8080`, `localhost:8080`.
- Celular: `<ip-da-lan>:8443`.
- Mais `WCAM_EXTRA_ALLOWED_HOSTS` (JSON, por exemplo `["agent:8080","agent:8443"]`), só no compose.

Em desenvolvimento, o proxy do Vite precisa reescrever o `Host` para o alvo (`changeOrigin: true`).

## Rotas

### `GET /api/health`

Nos dois servidores.

```json
{"status": "ok", "version": "0.1.0", "surface": "console"}
```

`surface` é `"console"` no servidor do console e `"phone"` no servidor do celular.

## Variáveis de ambiente do agente

| Variável | Padrão | Uso |
|---|---|---|
| `WCAM_CONSOLE_PORT` | `8080` | porta do console |
| `WCAM_PHONE_PORT` | `8443` | porta do celular |
| `WCAM_CONSOLE_BIND` | `127.0.0.1` | endereço do console; `0.0.0.0` só dentro do container |
| `WCAM_LAN_IP` | detectado | força a interface da LAN |
| `WCAM_DATA_DIR` | `%LOCALAPPDATA%\wcam` ou `~/.local/share/wcam` | certificado e, depois, banco |
| `WCAM_WEB_DIST` | `<repo>/web/dist` | build do web |
| `WCAM_LOCALES_DIR` | `<repo>/locales` | textos |
| `WCAM_EXTRA_ALLOWED_HOSTS` | `[]` | hosts extras, só no compose |

## Variáveis dos testes e2e

| Variável | Exemplo no compose |
|---|---|
| `E2E_CONSOLE_URL` | `http://agent:8080` |
| `E2E_PHONE_URL` | `https://agent:8443` |
