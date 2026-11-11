# Contrato entre web e agent

Versão: 0.7.0

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
| `PUT /api/video-format` | `{"format"}` | `204` | `422 invalid_request` |
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

### Comparação lado a lado (desenvolvimento, spec v0.6.0 §6)

Só com `WCAM_DEV_TOOLS=1`; sem a variável, todas as rotas abaixo respondem `404 not_found` e `GET /api/status` traz `devTools: false`. Com ela, `devTools: true` no primeiro nível do status.

| Rota | Corpo | Resposta | Erros |
|---|---|---|---|
| `POST /api/dev/comparisons` | nenhum | `201 {"id"}` | `409 no_live_session` |
| `PUT /api/dev/comparisons/{id}/pc?capturedAt=<ms>` | PNG (`image/png`), até 20 MB; `capturedAt` é o instante da captura no relógio do PC, em ms desde a época | `204` | `404 comparison_not_found`, `422 invalid_request` |
| `GET /api/dev/comparisons/{id}` | nenhum | `200` (abaixo) | `404 comparison_not_found` |
| `GET /api/dev/comparisons/{id}/phone.png` | nenhum | `200 image/png` | `404 comparison_not_found` |
| `PUT /api/dev/comparisons/{id}/screen` | PNG (`image/png`) do print da tela do celular, até 20 MB | `204` | `404 comparison_not_found`, `409 comparison_not_ready`, `422 invalid_request` (não é PNG) |
| `GET /api/dev/comparisons/{id}/screen.png` | nenhum | `200 image/png` | `404 comparison_not_found` |

`GET /api/dev/comparisons/{id}`:

```json
{
  "id": "c1",
  "state": "ready",
  "reason": null,
  "requestedAt": "2026-11-07T21:50:00.120Z",
  "phone": {"capturedAt": "2026-11-07T21:50:00.240Z", "colorSpace": "display-p3", "width": 1920, "height": 1080},
  "pc": {"receivedAt": "2026-11-07T21:50:00.180Z", "capturedAt": "2026-11-07T21:50:00.110Z", "width": 1920, "height": 1080},
  "correction": {"state": "applied", "transfer": "bt709", "display": "apple", "tables": {"y": [0], "u": [0], "v": [0]}},
  "difference": {
    "captureGapMs": 60, "correlation": 0.97, "mirrored": false,
    "deltaE2000": {"mean": 3.2, "median": 2.9, "p90": 6.1},
    "deltaL": -4.1, "chromaRatio": 0.92, "hueShiftDegrees": 2.3,
    "grid": {"columns": 8, "rows": 4, "deltaE2000": [3.1]}
  }
}
```

- `state`: `pending` (esperando uma das imagens), `ready` ou `failed`. `reason` (só em `failed`): `phone_timeout` (celular sem resposta em 10 s), `phone_invalid` (pedaços faltando ou tamanho errado), `pc_missing` (imagem do PC não chegou em 10 s), `session_ended`.
- `phone` e `pc` são `null` até cada imagem chegar; `difference` é `null` até as duas. `correction.tables` são as tabelas Y, U e V em uso (256 inteiros cada); `grid.deltaE2000` tem `columns × rows` valores, linha a linha.
- Em `screenDifference`, `mirrored` e `correlation` são os do alinhamento do print (o print da câmera frontal vem espelhado, como o visor). `screen` é `null` até o print chegar; com ele, `{"receivedAt", "width", "height", "colorSpace"}` (do perfil ICC; sem perfil, `srgb`), e `screenDifference` traz `{"phone": <mesmo formato de difference>, "pc": <mesmo formato>}`: print contra o canvas do celular e print contra a imagem do PC. O print só é aceito com a comparação `ready`.
- O agente guarda só as últimas 5 comparações, em memória.

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
- `{"type": "video_format", "format": "1080p30", "width": 1920, "height": 1080, "fps": 30, "maxBitrate": 10000000, "available": ["720p30", "720p60", "1080p30"]}` quando o canal abre, a cada mudança de formato, venha ela do console ou do próprio celular, e a cada `camera_capabilities` (ver "Formato de vídeo").

Do celular para o agente, JSON:

- `{"type": "set_video_format", "format": "<chave>"}` quando o usuário escolhe um formato no celular. O agente aplica e responde com `video_format` (inclusive ao próprio celular), que é a fonte da verdade do que está em uso. Só vale com a sessão em `live`: antes do Confirmar o aparelho ainda não foi aceito, e a mensagem é ignorada com registro no log, sem resposta. Chave fora de `available` também é ignorada com log, e o agente reenvia o `video_format` atual. O seletor do celular só aparece depois de `session_state` `live`;
- `{"type": "camera_capabilities", "width": 3840, "height": 2160, "frameRate": 60, "facingMode": "environment", "codecs": ["video/H264", "video/VP8"], "colorSpace": {"primaries": "bt709", "transfer": "bt709", "matrix": "bt709", "fullRange": true}}` quando o canal abre e a cada troca de câmera. `width`, `height` e `frameRate` são os máximos de `getCapabilities()` da faixa em uso (`null` quando o navegador não informa); `facingMode` é `user`, `environment` ou `null`; `codecs` são os `mimeType` de vídeo de `RTCRtpSender.getCapabilities("video")`, sem repetição e sem `video/rtx`, `video/red` e `video/ulpfec`; `colorSpace` é o `VideoFrame.colorSpace` de um quadro da câmera em uso (`primaries`, `transfer`, `matrix` com os nomes do WebCodecs, `fullRange` booleano; campo `null` quando o navegador não informa) ou `null` quando o navegador não expõe `VideoFrame` (spec v0.6.0 §1.1). `modes` é `{"exposureMode", "whiteBalanceMode", "focusMode"}` com os valores de `getSettings()` da faixa em uso, cada um `null` quando o navegador não informa (spec v0.7.0 §4).


Comparação lado a lado (só com `WCAM_DEV_TOOLS=1`; sem a variável, o agente não envia `snapshot_request` e ignora as respostas com log):

- agente para o celular: `{"type": "snapshot_request", "id": "c1"}`, só em `live`;
- celular para o agente: `{"type": "snapshot_begin", "id": "c1", "capturedAt": <ms>, "captureDelayMs": <ms entre receber o snapshot_request e capturar, no relógio do celular>, "colorSpace": "display-p3" | "srgb", "width": 1920, "height": 1080, "size": <bytes do PNG>, "chunks": <n>}` e depois `n` mensagens `{"type": "snapshot_chunk", "id": "c1", "index": <0 a n−1>, "data": "<base64 de até 45 000 bytes do PNG>"}`. O quadro é o do visor, sem espelho, no tamanho nativo do vídeo. Cada mensagem cabe no `max-message-size` de 65 536. `capturedAt` do celular é só informativo, porque o relógio do celular pode estar defasado do PC; `captureGapMs` no relatório é |(envio do `snapshot_request` + `captureDelayMs`) − `capturedAt` do PC|, tudo no relógio do PC.
- celular para o agente, print da tela escolhido pelo usuário: `{"type": "screenshot_begin", "id": "c1", "size": <bytes do PNG>, "chunks": <n>}` e `n` mensagens `{"type": "screenshot_chunk", "id": "c1", "index": <0 a n−1>, "data": "<base64 de até 45 000 bytes>"}`. `id` é o do último `snapshot_request`. Tem o mesmo efeito de `PUT /api/dev/comparisons/{id}/screen` (só com a comparação `ready`, só PNG); se a comparação ainda não estiver `ready`, o agente guarda o print e o aplica quando ela ficar. O botão do celular só aparece depois de um `snapshot_request`, que só existe com `WCAM_DEV_TOOLS=1`.

Mensagem com `type` desconhecido, JSON inválido ou campo fora do formato é ignorada pelo agente e registrada no log, sem encerrar a sessão.

## Formato de vídeo

Substitui a "Opção de qualidade" da 0.6.0 (`PUT /api/quality-preset`, `qualityPreset`, `quality_preset` e `set_quality_preset` saem). Spec v0.7.0 §1.

| Chave | Largura | Altura | fps | Taxa máxima (bit/s) |
|---|---|---|---|---|
| `720p30` | 1280 | 720 | 30 | 5 000 000 |
| `720p60` | 1280 | 720 | 60 | 8 000 000 |
| `1080p30` (padrão) | 1920 | 1080 | 30 | 10 000 000 |
| `1440p30` | 2560 | 1440 | 30 | 18 000 000 |
| `2160p30` | 3840 | 2160 | 30 | 35 000 000 |

Tabela confirmada pelo spike `h264-levels` (2026-11-10, iPhone do usuário, câmeras frontal e traseira, Safari): taxas recebidas de 3,6 a 4,9 Mbit/s em 720p30, 5,8 a 7,9 em 720p60, 7,5 a 9,6 em 1080p30, 16,6 em 1440p30 e 17,4 a 19,1 em 2160p30. Saíram `1080p60`, `1440p60` e `2160p60`: o Safari aceita o pedido de 60 fps acima de 720p e entrega 30 nas duas câmeras.

A resposta SDP do agente declara H.264 nível 5.1 (`profile-level-id` `42e033` e `420033`), o do maior formato da tabela. O Safari envia o nível do formato que codifica, independentemente do nível da resposta (spike: 3.1, 4.0, 5.0 e 5.1 com resposta 3.1); a resposta só fica coerente com o que o agente aceita.

- `available`: os formatos da tabela cuja largura, altura e fps cabem nos máximos da última `camera_capabilities` (largura e altura comparadas na orientação paisagem). Até a primeira, só `1080p30`.
- `PUT /api/video-format` com `{"format": "<chave>"}` muda o formato; vale para a sessão atual e as próximas, até o agente fechar. Chave desconhecida ou fora de `available`: `422 invalid_request`. Com sessão aberta, o agente envia `video_format` ao celular.
- Se uma `camera_capabilities` nova deixar o formato escolhido fora de `available`, o agente passa ao maior formato de `available` (mais pixels, depois mais fps) e envia `video_format`.
- O celular aplica largura, altura e fps com `applyConstraints` na faixa em uso (largura e altura trocadas em retrato) e a taxa em `maxBitrate` com `setParameters`, sem renegociar; o agente ajusta o teto da estimativa de banda (REMB) ao mesmo valor.
- `GET /api/status` traz no primeiro nível, sempre presente, `"videoFormat": {"selected": "1080p30", "available": ["1080p30"], "camera": "1080p30", "pending": false}`. `camera` é o formato que a câmera WCam anuncia agora; `pending` é `true` enquanto `selected` espera um app reabrir a câmera (spec v0.7.0 §1.3; sempre `false` se o spike mostrar troca imediata).

## WebRTC

- Os dois lados sem STUN e sem TURN: `iceServers: []` no navegador e `RTCConfiguration(iceServers=[])` no aiortc (o aiortc usa um STUN público quando a configuração é omitida; omitir é proibido).
- O agente descarta, antes de `setRemoteDescription`, toda linha `a=candidate` da oferta cujo endereço não esteja na sub-rede da LAN (inclui nomes `.local`), e remove da resposta os candidatos das suas outras interfaces (WSL, Hyper-V, Docker).
- Celular: uma faixa de vídeo, `contentHint = "detail"`, `maxBitrate` do formato em uso (ver "Formato de vídeo"; padrão 10 000 000) e `degradationPreference` `maintain-resolution` quando o navegador aceitar (o que não for aceito é registrado no relatório, não é erro).
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
  "videoFormat": {"selected": "1080p30", "available": ["720p30", "720p60", "1080p30", "1440p30", "2160p30"], "camera": "1080p30", "pending": false},
  "session": {
    "video": {"width": 1920, "height": 1080, "fps": 30.0, "bitrateKbps": 9800, "codec": "H264", "framesScaled": 0, "orientation": "landscape", "colorRange": "full", "colorMatrix": "unspecified", "colorCorrection": {"state": "applied", "transfer": "bt709", "display": "apple"}},
    "cameraCapabilities": {"width": 3840, "height": 2160, "frameRate": 60, "facingMode": "environment", "codecs": ["video/H264", "video/VP8"], "colorSpace": null, "modes": {"exposureMode": "continuous", "whiteBalanceMode": "continuous", "focusMode": "continuous"}}
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
- `session.video.colorCorrection`: correção de cor da conexão atual, derivada do `colorSpace` declarado pela câmera em `camera_capabilities` (spec v0.6.0 §1.1). `state`: `applied` (curva de exibição aplicada ao Y) ou `default` (só a faixa: sem `colorSpace`, transferência `srgb`, HDR ou convenção `standard`). `transfer`: o declarado, ou `null`. `display`: convenção de exibição do celular pela plataforma do `User-Agent`, `apple` (iPhone, iPad, Safari no macOS) ou `standard`. Recalculada a cada `camera_capabilities`; nada é guardado entre conexões.
- `session.cameraCapabilities`: a última mensagem `camera_capabilities` do celular, sem o `type`; `null` até chegar a primeira.
- `session.video.codec`: o codec negociado (`H264` ou `VP8`). `framesScaled`: quantos quadros foram reduzidos na sessão; só quadros de retrato (faixas laterais, spec v0.7.0 §2), 0 em paisagem. `orientation`: `landscape` ou `portrait`, do quadro mais recente. `width` e `height` são os do quadro recebido (em retrato, altura maior que largura). `virtualCamera.output` é o formato anunciado pela câmera (`videoFormat.camera`).
- `process.cpuPercent`: uso de CPU do processo do agente, média da última janela de 1 s, via psutil.
- `quality`: só existe com `WCAM_QUALITY_REFERENCE` definido (desenvolvimento e e2e); fora disso é sempre `null`. Ver "Qualidade".

Variáveis de ambiente (somam-se à tabela abaixo):

| Variável | Padrão | Uso |
|---|---|---|
| `WCAM_VIRTUAL_CAMERA` | `auto` | `auto` (Windows 22000 ou maior com a DLL registrada usa `media_foundation`; senão `obs`; fora do Windows, `fake`), `media_foundation`, `obs` ou `fake` |
| `WCAM_VCAM_DLL` | `%ProgramFiles%\WCam\Wcam.VirtualCamera.dll` | caminho da DLL da câmera nativa |
| `WCAM_QUALITY_REFERENCE` | vazio | caminho de um arquivo `.y4m` de referência; liga a medição de SSIM |
| `WCAM_DEV_TOOLS` | vazio | `1` liga a comparação lado a lado no console (spec v0.6.0 §6); qualquer outro valor deixa desligada |

## Qualidade (`quality`)

Medição automática:
- Com `WCAM_QUALITY_REFERENCE` definido, o agente lê o arquivo `.y4m` de referência (1920x1080, um quadro estático de alto detalhe) e compara cada quadro entregue ao sink com ele: SSIM no plano Y, janela de 8x8, implementado com numpy. Os quadros dos primeiros 3 s da sessão `live` são ignorados, enquanto o codificador estabiliza. A referência tem o tamanho de um formato da tabela (o gerador aceita largura e altura, spec v0.7.0 §3); quadro de outro tamanho não é medido.
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
