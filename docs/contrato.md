# Contrato entre web e agent

Versão: 0.6.0

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
| `PUT /api/quality-preset` | `{"preset"}` | `204` | `422 invalid_request` |
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
- `{"type": "session_state", "state": "ended", "reason": "<motivo de lastEnded>"}` antes de fechar;
- `{"type": "quality_preset", "preset": "<chave>"}` quando o canal abre e a cada mudança de opção, venha ela do console ou do próprio celular.

Do celular para o agente, JSON:

- `{"type": "set_quality_preset", "preset": "<chave>"}` quando o usuário escolhe uma opção no celular. O agente aplica e responde com `quality_preset` (inclusive ao próprio celular), que é a fonte da verdade do que está em uso. Só vale com a sessão em `live`: antes do Confirmar o aparelho ainda não foi aceito, e a mensagem é ignorada com registro no log, sem resposta. O seletor do celular só aparece depois de `session_state` `live`;
- `{"type": "camera_capabilities", "width": 3840, "height": 2160, "frameRate": 60, "facingMode": "environment", "codecs": ["video/H264", "video/VP8"]}` quando o canal abre e a cada troca de câmera. `width`, `height` e `frameRate` são os máximos de `getCapabilities()` da faixa em uso (`null` quando o navegador não informa); `facingMode` é `user`, `environment` ou `null`; `codecs` são os `mimeType` de vídeo de `RTCRtpSender.getCapabilities("video")`, sem repetição e sem `video/rtx`, `video/red` e `video/ulpfec`.

- `{"type": "color_sample", "colorSpace": "display-p3", "width": 160, "height": 90, "rgb": "<base64>", "capturedAt": 1793991387130}` para a calibração de cor: o quadro que o visor do celular está exibindo, desenhado num canvas sem espelho e lido com `getImageData` no mesmo `colorSpace` (`display-p3` ou `srgb`). `rgb` é o base64 dos bytes R, G e B de cada pixel, sem alfa, linha a linha (`width × height × 3` bytes); `capturedAt` é `performance.timeOrigin + performance.now()` em ms. Enviada com a sessão em `live` e o celular em paisagem, uma por segundo, 5 vezes, e de novo a cada troca de câmera. Antes do `live` é ignorada com registro no log. Cabe no `max-message-size` de 65 536 bytes anunciado pelo agente.

Mensagem com `type` desconhecido, JSON inválido ou campo fora do formato é ignorada pelo agente e registrada no log, sem encerrar a sessão.

## Opção de qualidade

| Chave | Nome | Taxa máxima |
|---|---|---|
| `maximum` | Máxima | 20 000 000 bit/s |
| `balanced` | Equilibrada (padrão) | 10 000 000 bit/s |
| `light` | Leve | 5 000 000 bit/s |

- `PUT /api/quality-preset` com `{"preset": "<chave>"}` muda a opção; vale para a sessão atual e as próximas, até o agente fechar. Chave desconhecida: `422 invalid_request`. Com sessão aberta, o agente envia `quality_preset` ao celular.
- O celular aplica a taxa em `maxBitrate` do envio com `setParameters`, sem renegociar; o agente ajusta o teto da estimativa de banda (REMB) ao mesmo valor.
- `qualityPreset` no primeiro nível de `GET /api/status`, sempre presente.

## WebRTC

- Os dois lados sem STUN e sem TURN: `iceServers: []` no navegador e `RTCConfiguration(iceServers=[])` no aiortc (o aiortc usa um STUN público quando a configuração é omitida; omitir é proibido).
- O agente descarta, antes de `setRemoteDescription`, toda linha `a=candidate` da oferta cujo endereço não esteja na sub-rede da LAN (inclui nomes `.local`), e remove da resposta os candidatos das suas outras interfaces (WSL, Hyper-V, Docker).
- Celular: uma faixa de vídeo, `contentHint = "detail"`, `maxBitrate` da opção de qualidade em uso (ver "Opção de qualidade"; padrão 10 000 000) e `degradationPreference` `maintain-resolution` quando o navegador aceitar (o que não for aceito é registrado no relatório, não é erro).
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
    "backend": "media_foundation",
    "reason": null,
    "fallbackReason": null,
    "output": {"width": 1920, "height": 1080, "fps": 30},
    "source": "phone"
  },
  "qualityPreset": "balanced",
  "session": {
    "video": {"width": 1920, "height": 1080, "fps": 30.0, "bitrateKbps": 9800, "codec": "H264", "framesScaled": 0, "colorRange": "full", "colorMatrix": "unspecified", "colorCalibration": {"state": "applied", "deltaE": 1.2}},
    "cameraCapabilities": {"width": 3840, "height": 2160, "frameRate": 60, "facingMode": "environment", "codecs": ["video/H264", "video/VP8"]}
  },
  "process": {"cpuPercent": 12.5},
  "quality": null
}
```

- `virtualCamera.state`: `active` ou `unavailable`. `reason` (só com `unavailable`): `driver_missing`, `device_in_use` ou `error`.
- `backend`: `media_foundation` (câmera nativa "WCam", ADR 0011), `obs` (fallback) ou `fake`.
- `fallbackReason`: por que a câmera nativa não está em uso; `null` quando `backend` é `media_foundation`. Valores: `native_not_registered` (DLL não registrada), `windows_too_old` (build anterior a 22000), `native_error` (a DLL falhou ao iniciar) e `not_windows`. Só é preenchido quando `WCAM_VIRTUAL_CAMERA` é `auto` e a escolha caiu da câmera nativa para outro backend; com backend explícito é sempre `null`. Com `WCAM_VIRTUAL_CAMERA=media_foundation` explícito e falha, não há fallback: `state` `unavailable` com `reason` `driver_missing` (DLL ausente) ou `error` (`WcamCameraStart` falhou).
- `source`: `phone` quando os quadros vêm do celular; `frozen` quando a câmera repete o último quadro do celular porque nenhum quadro novo chegou há mais de 0,5 s (até completar 3 s sem quadro; antes de 0,5 s continua `phone`, que é o intervalo normal entre quadros); `placeholder` em qualquer outro momento.
- `session.video.colorRange`: faixa declarada pelo celular no quadro mais recente, `full`, `limited` ou `unspecified`. `colorMatrix`: matriz declarada, `bt709`, `bt601`, outro nome do FFmpeg ou `unspecified`. A câmera sempre entrega faixa limitada; quadro em faixa cheia é ajustado pelo agente (CA-2, emenda da v0.6.0).
- `session.video.colorCalibration`: calibração de cor da conexão atual (spec v0.6.0 §1.1). `state`: `measuring` (esperando amostras `color_sample`), `applied` (curva de tom e saturação aplicadas) ou `default` (amostras insuficientes ou correção sem ganho; só a faixa é ajustada). `deltaE`: ΔE2000 médio entre as amostras do celular e a saída corrigida; `null` até medir. Recomeça em `measuring` a cada conexão e a cada troca de câmera; nada é guardado entre conexões.
- `session.cameraCapabilities`: a última mensagem `camera_capabilities` do celular, sem o `type`; `null` até chegar a primeira.
- `session.video.codec`: o codec negociado (`H264` ou `VP8`). `framesScaled`: quantos quadros precisaram ser redimensionados na sessão (o esperado é 0; ver "Formato de saída").
- `process.cpuPercent`: uso de CPU do processo do agente, média da última janela de 1 s, via psutil.
- `quality`: só existe com `WCAM_QUALITY_REFERENCE` definido (desenvolvimento e e2e); fora disso é sempre `null`. Ver "Qualidade".

Variáveis de ambiente (somam-se à tabela abaixo):

| Variável | Padrão | Uso |
|---|---|---|
| `WCAM_VIRTUAL_CAMERA` | `auto` | `auto` (Windows 22000 ou maior com a DLL registrada usa `media_foundation`; senão `obs`; fora do Windows, `fake`), `media_foundation`, `obs` ou `fake` |
| `WCAM_VCAM_DLL` | `%ProgramFiles%\WCam\Wcam.VirtualCamera.dll` | caminho da DLL da câmera nativa |
| `WCAM_QUALITY_REFERENCE` | vazio | caminho de um arquivo `.y4m` de referência; liga a medição de SSIM |

## Qualidade (`quality`)

Medição automática:
- Com `WCAM_QUALITY_REFERENCE` definido, o agente lê o arquivo `.y4m` de referência (1920x1080, um quadro estático de alto detalhe) e compara cada quadro entregue ao sink com ele: SSIM no plano Y, janela de 8x8, implementado com numpy. Os quadros dos primeiros 3 s da sessão `live` são ignorados, enquanto o codificador estabiliza.
- `quality` no status: `{"ssim": <média>, "minimum": <menor>, "frames": <quantos>}`. Com a referência definida e nenhum quadro medido ainda, vem `{"ssim": null, "minimum": null, "frames": 0}`; o cliente espera `frames >= 30` antes de ler `ssim`.
- O arquivo de referência é gerado por um script do agente (`python -m wcam.tools.make_reference <saida.y4m>`), deterministicamente, com padrão de alto detalhe representativo de imagem de câmera: texto fino, linhas de 1 px, gradientes e uma textura fina estruturada, estática, com detalhe de 2 a 4 px (trama, como tecido). Sem ruído aleatório pixel a pixel, que nenhuma câmera entrega (o celular remove o ruído do sensor) e que o codificador de câmera do Chromium descarta por definição. Ele não é commitado.
- No e2e, o Chromium recebe a referência como câmera falsa (`--use-file-for-fake-video-capture`), faz o fluxo completo até `live`, e o teste confere `quality.ssim >= 0.98` depois de pelo menos 30 quadros medidos.

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
| `E2E_QUALITY_REFERENCE` | `/reference/reference.y4m` (volume `reference`, o mesmo arquivo de `WCAM_QUALITY_REFERENCE` no `agent`) |
