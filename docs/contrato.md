# Contrato entre web e agent

Versão: 0.4.0

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
| `pairing_token_invalid` | 401 | token desconhecido, já usado ou substituído |
| `pairing_token_expired` | 401 | token expirado |
| `pairing_window_closed` | 403 | nenhuma janela de pareamento aberta |
| `too_many_attempts` | 429 | IP bloqueado por 10 min depois de 5 falhas em 60 s |
| `session_already_active` | 409 | já existe uma sessão; também no `POST /api/pairing` |
| `no_session_awaiting_confirmation` | 409 | confirmar ou recusar sem sessão aguardando |
| `no_active_session` | 404 | desconectar sem sessão |

Qualquer outro status de erro do framework vira `invalid_request` (4xx) ou `internal_error` (5xx). Não existe código genérico fora desta tabela.

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

## Console (`127.0.0.1:8080`)

| Rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `POST /api/pairing` | nenhum | `201 {"url","qrSvg","expiresAt"}` | `409 session_already_active` |
| `DELETE /api/pairing` | nenhum | `204` | nenhum |
| `GET /api/status` | nenhum | `200` (abaixo) | nenhum |
| `POST /api/sessions/current/confirm` | nenhum | `204` | `409 no_session_awaiting_confirmation` |
| `POST /api/sessions/current/reject` | nenhum | `204` | `409 no_session_awaiting_confirmation` |
| `DELETE /api/sessions/current` | nenhum | `204` | `404 no_active_session` |

- `POST /api/pairing` abre a janela de pareamento por 120 s, gera um token novo e invalida o anterior. `url` é `https://<ip-da-lan>:8443/cam#t=<token>`; `qrSvg` é o QR dessa URL como documento SVG completo e independente (com `xmlns="http://www.w3.org/2000/svg"`, sem declaração XML), pronto para virar uma imagem `data:`; `expiresAt` em ISO 8601 UTC.
- A janela fecha quando expira, quando uma sessão é criada (o token é consumido) ou no `DELETE`.

`GET /api/status`:

```json
{
  "pairing": {"expiresAt": "2026-11-01T18:02:00Z"},
  "session": {
    "id": "b3f1...",
    "state": "awaiting_confirmation",
    "deviceName": "Android · Chrome",
    "remoteIp": "192.168.100.31",
    "startedAt": "2026-11-01T18:00:10Z",
    "confirmationCode": "92Q-M2H",
    "video": {"width": 1920, "height": 1080, "fps": 30.0, "bitrateKbps": 9800}
  },
  "lastEnded": {"reason": "rejected", "at": "2026-11-01T17:55:40Z"}
}
```

- `pairing` é `null` com a janela fechada; `session` é `null` sem sessão.
- `state`: `connecting`, `awaiting_confirmation`, `live`. Sessão encerrada vira `null`, e o motivo do último encerramento fica em `lastEnded: {"reason", "at"}`, campo sempre presente no primeiro nível (`null` se nenhuma sessão terminou desde que o agente subiu) (`rejected`, `disconnected_by_pc`, `disconnected_by_phone`, `connection_failed`, `confirmation_timeout`).
- `confirmationCode` aparece a partir de `awaiting_confirmation`.
- `video` é `null` até o primeiro quadro; `fps` e `bitrateKbps` são a média da última janela de 1 s, medidos pelo agente (quadros decodificados e bytes RTP recebidos), não o que o celular declara.
- `deviceName` vem do `User-Agent`: sistema e navegador (`Android · Chrome`, `iPhone · Safari`), nunca o texto bruto. Parte não reconhecida é omitida (`Android`, `Chrome`); sem nenhuma reconhecida, `null`, e o console mostra `console.device_unknown`.
- `video` só aparece depois do Confirmar: o agente mede depois do portão. Em `connecting` e `awaiting_confirmation` é `null`.
- `connecting` vira `awaiting_confirmation` quando o DataChannel `control` abre do lado do agente.

## Celular (`<ip-da-lan>:8443`)

`POST /api/sessions` com `{"token": "...", "sdp": "<oferta completa, sem trickle>"}`:

- `201 {"sessionId", "sdp": "<resposta>", "confirmationNonce": "<32 hex>"}`.
- Ordem das checagens: bloqueio (`429`), sessão ativa (`409`), SDP (`422`) e por fim o token. Uma SDP ruim não consome o token.
- Só `pairing_token_invalid`, `pairing_token_expired` e `pairing_window_closed` contam para o limite de tentativas.
- Erros: `401 pairing_token_invalid` (token desconhecido, já usado ou substituído), `401 pairing_token_expired`, `403 pairing_window_closed`, `403 not_same_network`, `429 too_many_attempts`, `409 session_already_active`, `422 invalid_request` (SDP sem vídeo, sem DataChannel ou ilegível).

## DataChannel `control` (criado pelo celular)

Do agente para o celular, JSON:

- `{"type": "session_state", "state": "awaiting_confirmation"}` quando a conexão sobe;
- `{"type": "session_state", "state": "live"}` depois do Confirmar;
- `{"type": "session_state", "state": "ended", "reason": "<motivo de lastEnded>"}` antes de fechar.

O celular não envia mensagens nesta versão.

## WebRTC

- Os dois lados sem STUN e sem TURN: `iceServers: []` no navegador e `RTCConfiguration(iceServers=[])` no aiortc (o aiortc usa um STUN público quando a configuração é omitida; omitir é proibido).
- O agente descarta, antes de `setRemoteDescription`, toda linha `a=candidate` da oferta cujo endereço não esteja na sub-rede da LAN (inclui nomes `.local`), e remove da resposta os candidatos das suas outras interfaces (WSL, Hyper-V, Docker).
- Celular: uma faixa de vídeo, `contentHint = "detail"`, `maxBitrate` de 10 000 000 e `degradationPreference` `maintain-resolution` quando o navegador aceitar (o que não for aceito é registrado no relatório, não é erro).
- Codecs: os que o navegador e o aiortc têm em comum (H.264 ou VP8); o relatório registra qual foi negociado no aparelho real.

## Código de confirmação

Os dois lados calculam o mesmo código, cada um sozinho:

1. `phoneFingerprint`: valor de `a=fingerprint:sha-256` da oferta enviada pelo celular; `agentFingerprint`: o mesmo da resposta. Hex em maiúsculas com `:`, exatamente como na SDP depois de passar para maiúsculas.
2. `digest = SHA-256(UTF-8("wcam-confirmation-v1|" + confirmationNonce + "|" + phoneFingerprint + "|" + agentFingerprint))`.
3. `n` = os 8 primeiros bytes de `digest` como inteiro sem sinal big-endian.
4. Seis vezes: `n, r = divmod(n, 30)`, acrescentando `ALPHABET[r]`, com `ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"` (sem `0`, `1`, `I`, `L`, `O` e `U`; cerca de 29 bits).
5. Mostrado como `XXX-XXX`.

Vetores de teste (os dois lados testam os três):

| nonce | phoneFingerprint | agentFingerprint | código |
|---|---|---|---|
| `00112233445566778899aabbccddeeff` | `AB:AB:...` (32 vezes `AB`) | `CD:CD:...` (32 vezes `CD`) | `92Q-M2H` |
| `00112233445566778899aabbccddeeff` | 32 vezes `CD` | 32 vezes `AB` | `9MX-3B9` |
| `ffeeddccbbaa99887766554433221100` | 32 vezes `AB` | 32 vezes `CD` | `8VG-KBV` |

Refina a codificação da ADR 0010 (alfabeto de 30 símbolos em vez de Crockford base32), sem mudar a decisão.

## Câmera virtual, CPU e qualidade em `GET /api/status`

```json
{
  "virtualCamera": {
    "state": "active",
    "backend": "obs",
    "reason": null,
    "output": {"width": 1920, "height": 1080, "fps": 30},
    "source": "phone"
  },
  "session": {
    "video": {"width": 1920, "height": 1080, "fps": 30.0, "bitrateKbps": 9800, "codec": "H264", "framesScaled": 0}
  },
  "process": {"cpuPercent": 12.5},
  "quality": null
}
```

- `virtualCamera.state`: `active` ou `unavailable`. `reason` (só com `unavailable`): `driver_missing`, `device_in_use` ou `error`.
- `backend`: `obs` ou `fake`.
- `source`: `phone` quando os quadros vêm do celular; `placeholder` em qualquer outro momento.
- `session.video.codec`: o codec negociado (`H264` ou `VP8`). `framesScaled`: quantos quadros precisaram ser redimensionados na sessão (o esperado é 0; ver "Formato de saída").
- `process.cpuPercent`: uso de CPU do processo do agente, média da última janela de 1 s, via psutil.
- `quality`: só existe com `WCAM_QUALITY_REFERENCE` definido (desenvolvimento e e2e); fora disso é sempre `null`. Ver "Qualidade".

Variáveis de ambiente (somam-se à tabela abaixo):

| Variável | Padrão | Uso |
|---|---|---|
| `WCAM_VIRTUAL_CAMERA` | `auto` | `auto` (Windows usa `obs`, o resto usa `fake`), `obs` ou `fake` |
| `WCAM_QUALITY_REFERENCE` | vazio | caminho de um arquivo `.y4m` de referência; liga a medição de SSIM |

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
