# Spec v0.3.0, Pareamento e WebRTC

Status: Aprovada (2026-11-01)
Branch de integração: `feature/pareamento`
Sessões: `agent` e `web`, em paralelo
Referências: `docs/planejamento.md` §1 (CA-2, CA-4), §4 (fluxo e segurança), §5.2 a §5.4; ADRs 0003, 0004, 0009 e 0010

## Objetivo

O celular passa a enviar vídeo ao PC. O QR carrega um token de uso único; o celular abre a sessão, a conexão WebRTC sobe só dentro da LAN, as duas telas mostram o mesmo código de confirmação, e os quadros só passam depois do "Confirmar" no PC. O agente mede o que recebe: resolução, fps e bitrate reais.

Os quadros ainda não vão para uma câmera virtual (v0.4.0): depois do portão, o agente só os conta e mede.

## Contrato

Esta seção substitui as partes correspondentes de `docs/contrato.md` na aprovação. O orquestrador atualiza o arquivo antes do handoff.

### Console (`127.0.0.1:8080`)

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
  }
}
```

- `pairing` é `null` com a janela fechada; `session` é `null` sem sessão.
- `state`: `connecting`, `awaiting_confirmation`, `live`. Sessão encerrada vira `null`, e o motivo do último encerramento fica em `lastEnded: {"reason", "at"}` (`rejected`, `disconnected_by_pc`, `disconnected_by_phone`, `connection_failed`, `confirmation_timeout`).
- `confirmationCode` aparece a partir de `awaiting_confirmation`.
- `video` é `null` até o primeiro quadro; `fps` e `bitrateKbps` são a média da última janela de 1 s, medidos pelo agente (quadros decodificados e bytes RTP recebidos), não o que o celular declara.
- `deviceName` vem do `User-Agent`: sistema e navegador (`Android · Chrome`, `iPhone · Safari`), nunca o texto bruto. Parte não reconhecida é omitida (`Android`, `Chrome`); sem nenhuma reconhecida, `null`, e o console mostra `console.device_unknown`.
- `video` só aparece depois do Confirmar: o agente mede depois do portão. Em `connecting` e `awaiting_confirmation` é `null`.
- `connecting` vira `awaiting_confirmation` quando o DataChannel `control` abre do lado do agente.

### Celular (`<ip-da-lan>:8443`)

`POST /api/sessions` com `{"token": "...", "sdp": "<oferta completa, sem trickle>"}`:

- `201 {"sessionId", "sdp": "<resposta>", "confirmationNonce": "<32 hex>"}`.
- Ordem das checagens: bloqueio (`429`), sessão ativa (`409`), SDP (`422`) e por fim o token. Uma SDP ruim não consome o token.
- Só `pairing_token_invalid`, `pairing_token_expired` e `pairing_window_closed` contam para o limite de tentativas.
- Erros: `401 pairing_token_invalid` (token desconhecido, já usado ou substituído), `401 pairing_token_expired`, `403 pairing_window_closed`, `403 not_same_network`, `429 too_many_attempts`, `409 session_already_active`, `422 invalid_request` (SDP sem vídeo, sem DataChannel ou ilegível).

### DataChannel `control` (criado pelo celular)

Do agente para o celular, JSON:

- `{"type": "session_state", "state": "awaiting_confirmation"}` quando a conexão sobe;
- `{"type": "session_state", "state": "live"}` depois do Confirmar;
- `{"type": "session_state", "state": "ended", "reason": "<motivo de lastEnded>"}` antes de fechar.

O celular não envia mensagens nesta versão.

### WebRTC

- Os dois lados sem STUN e sem TURN: `iceServers: []` no navegador e `RTCConfiguration(iceServers=[])` no aiortc (o aiortc usa um STUN público quando a configuração é omitida; omitir é proibido).
- O agente descarta, antes de `setRemoteDescription`, toda linha `a=candidate` da oferta cujo endereço não esteja na sub-rede da LAN (inclui nomes `.local`), e remove da resposta os candidatos das suas outras interfaces (WSL, Hyper-V, Docker).
- Celular: uma faixa de vídeo, `contentHint = "detail"`, `maxBitrate` de 10 000 000 e `degradationPreference` `maintain-resolution` quando o navegador aceitar (o que não for aceito é registrado no relatório, não é erro).
- Codecs: os que o navegador e o aiortc têm em comum (H.264 ou VP8); o relatório registra qual foi negociado no aparelho real.

### Código de confirmação

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

Isto refina a codificação da ADR 0010 (alfabeto de 30 símbolos em vez de Crockford base32), sem mudar a decisão.

## Escopo da sessão agent

- `pairing/tokens.py`: janela de pareamento com um token ativo de 128 bits (`secrets.token_urlsafe(16)`), guardado só como SHA-256, comparado com `hmac.compare_digest`, uso único, 120 s, substituição invalida o anterior. Lembra o hash do último token expirado ou substituído só para distinguir `pairing_token_expired` de `pairing_token_invalid`.
- `pairing/attempts.py`: 5 falhas de `POST /api/sessions` em 60 s por IP bloqueiam esse IP por 10 min (`429 too_many_attempts`, mesmo com token válido). Sucesso não conta.
- `pairing/confirmation_code.py`: o algoritmo acima, puro.
- `media/sdp_filter.py`: filtro de candidatos e extração de fingerprint, puros.
- `media/frame_gate.py`: portão fechado até a confirmação; conta quadros recebidos e quadros liberados.
- `media/metrics.py`: fps e bitrate por janela de 1 s, puros.
- `media/peer.py`: adaptador aiortc (única parte que importa aiortc): cria a conexão, aplica o filtro, abre o DataChannel, consome a faixa num loop com dono e cancelamento explícito.
- `sessions/manager.py`: uma sessão por vez, estados, timeout de 120 s em `awaiting_confirmation` (`confirmation_timeout`), encerramento por qualquer lado, `lastEnded`.
- Rotas do contrato nos dois servidores, com `deviceName` derivado do `User-Agent`.
- `cli.py`: ao iniciar, abre a janela de pareamento e imprime o QR com o token (a URL completa com token não aparece em texto no terminal, só no QR); o resto do banner continua.
- Token nunca em log: nem do uvicorn (o fragmento nunca chega ao servidor; o corpo do `POST` não é logado), nem do agente.
- `.github/dependabot.yml`: ignorar atualizações de versão maior das imagens `python` e `node`, de `@types/node` e de `typescript`.
- Dependência nova: `aiortc` (traz `av` e `aioice`). Justificativa: ADR 0002.

Testes do agente, além dos de sempre:
- `test_pairing_token_is_stored_only_as_hash`
- `test_pairing_token_can_be_used_once`
- `test_expired_pairing_token_is_rejected_as_expired`
- `test_replaced_pairing_token_is_rejected_as_invalid`
- `test_session_without_open_window_is_rejected_as_window_closed`
- `test_five_failures_block_the_ip_for_ten_minutes`
- `test_second_session_is_rejected_while_one_is_active`
- `test_confirmation_code_matches_contract_vectors`
- `test_offer_candidates_outside_subnet_are_removed`
- `test_answer_has_only_lan_candidates`
- `test_peer_connection_has_no_ice_servers`
- `test_frames_do_not_pass_gate_before_confirmation`
- `test_frames_pass_gate_after_confirmation`
- `test_awaiting_confirmation_times_out_after_two_minutes`
- `test_reject_ends_session_and_requires_new_pairing`
- `test_pairing_token_never_appears_in_logs`
- integração aiortc com aiortc: um cliente aiortc com faixa sintética de 1920x1080 cria a sessão por HTTP, o console confirma, e o agente mede 1920x1080.

## Escopo da sessão web

### Fase 1: forma dos estados novos da `/cam`

Mesma regra da v0.2.0: `taste-skill`, `impeccable shape`, `mobile-native` e `emil-design-eng`, com entrega em `docs/design-v0.3.0-cam.md` e aprovação do usuário antes do código de tela. Estados novos, depois de `ready`:

| Estado | Quando | O que a tela mostra |
|---|---|---|
| `connecting` | criando a sessão e subindo a conexão | espera, com o visor ao fundo |
| `awaiting_confirmation` | conexão de pé, sem Confirmar | o código em tamanho grande e "Confira se é igual no PC" |
| `live` | depois do Confirmar | visor do `ready` com a tally acesa em `--data` no topo do trilho |
| `pairing_failed` | `pairing_token_invalid`, `pairing_token_expired` ou `pairing_window_closed` | pedir para ler um QR novo no PC |
| `blocked` | `not_same_network` ou `too_many_attempts` | o motivo e o que fazer |
| `busy` | `session_already_active` | outro celular já está conectado |
| `ended` | `session_state` `ended` ou conexão perdida | o motivo e como voltar (ler um QR novo) |

A tally usa `--data` e também forma e texto, nunca só cor.

### Fase 2

- `media/use-publisher.ts`: cria a conexão (`iceServers: []`), adiciona a faixa com `contentHint`, aplica `maxBitrate` e `degradationPreference`, cria o DataChannel `control`, espera o ICE gathering terminar, faz o `POST /api/sessions` e aplica a resposta.
- A sessão só começa quando a câmera está em `ready`; o token lido do fragmento na v0.2.0 é enviado aqui e descartado da memória depois do `POST`.
- `data/confirmation-code.ts`: o algoritmo do contrato com Web Crypto e `BigInt`, testado com os três vetores.
- `data/cam-state.ts` ganha os estados novos, testados.
- Console provisório (sem passada de design; a direção definitiva é da v0.5.0, mas sem nada das regras anti AI slop): QR do `qrSvg` com contagem até `expiresAt` e botão "Novo QR", estado da sessão, aparelho e IP, código de confirmação com Confirmar e Recusar, Desconectar, e `video` (resolução, fps, bitrate). Atualiza por `GET /api/status` a cada 1 s (o SSE é da v0.5.0).
- e2e no compose com o agente real: a `/cam` com câmera falsa cria a sessão com um token obtido por `POST /api/pairing`, chega a `awaiting_confirmation` com o mesmo código que `GET /api/status` mostra, o teste chama `POST /api/sessions/current/confirm`, a `/cam` mostra `live`, e o status passa a ter `video`. Mais: token reutilizado mostra `pairing_failed`; recusa mostra `ended`.

## Textos

O orquestrador adiciona as chaves em `locales/` depois da fase 1 de design, com os textos revisados nela. Lista inicial:

| Chave | en | pt-BR |
|---|---|---|
| `cam.connecting` | Connecting to your computer | Conectando ao computador |
| `cam.confirm_title` | Check the code on your computer | Confira o código no computador |
| `cam.confirm_body` | It must be the same as on the computer. Confirm there. | Tem de ser igual ao do computador. Confirme lá. |
| `cam.live` | Live | Ao vivo |
| `cam.pairing_failed` | This QR code is no longer valid. Scan a new one on your computer. | Este QR code não vale mais. Leia um novo no computador. |
| `cam.blocked_network` | This phone is not on the same network as the computer. | Este celular não está na mesma rede que o computador. |
| `cam.blocked_attempts` | Too many attempts. Wait 10 minutes and scan a new QR code. | Muitas tentativas. Espere 10 minutos e leia um novo QR code. |
| `cam.busy` | Another phone is already connected. | Outro celular já está conectado. |
| `cam.ended_rejected` | The computer did not accept this phone. | O computador não aceitou este celular. |
| `cam.ended_disconnected` | The computer ended the connection. | O computador encerrou a conexão. |
| `cam.ended_lost` | The connection was lost. Scan a new QR code to connect again. | A conexão caiu. Leia um novo QR code para conectar de novo. |
| `cam.ended_timeout` | Not confirmed in time. Scan a new QR code. | Não foi confirmado a tempo. Leia um novo QR code. |
| `console.pairing_title` | Scan with your phone camera | Leia com a câmera do celular |
| `console.pairing_expires` | Expires in {seconds} s | Expira em {seconds} s |
| `console.pairing_new` | New QR code | Novo QR code |
| `console.confirm_title` | Is this the code on your phone? | Este é o código no celular? |
| `console.confirm` | Confirm | Confirmar |
| `console.reject` | Reject | Recusar |
| `console.disconnect` | Disconnect | Desconectar |
| `console.state_connecting` | Connecting | Conectando |
| `console.state_live` | Live | Ao vivo |
| `console.video_format` | {width} × {height} · {fps} fps · {bitrate} Mbit/s | {width} × {height} · {fps} fps · {bitrate} Mbit/s |
| `errors.pairing_token_invalid` | This QR code is no longer valid. | Este QR code não vale mais. |
| `errors.pairing_token_expired` | This QR code expired. | Este QR code expirou. |
| `errors.pairing_window_closed` | Pairing is closed on the computer. | O pareamento está fechado no computador. |
| `errors.too_many_attempts` | Too many attempts. Wait 10 minutes. | Muitas tentativas. Espere 10 minutos. |
| `errors.session_already_active` | Another phone is already connected. | Outro celular já está conectado. |
| `errors.no_session_awaiting_confirmation` | No phone is waiting for confirmation. | Nenhum celular aguardando confirmação. |
| `errors.no_active_session` | No phone is connected. | Nenhum celular conectado. |
| `terminal.scan_with_token` | Scan this QR code with your phone camera. It works once, for 2 minutes. To get a new one, open the console. | Leia este QR code com a câmera do celular. Ele vale uma vez, por 2 minutos. Para gerar outro, abra o console. |

## Fora do escopo

Câmera virtual (v0.4.0), reconexão após queda (v0.7.0), pausa e troca de câmera pelo PC (v0.5.0), SSE (v0.5.0), persistência (v0.6.0), design definitivo do console (v0.5.0).

## Critérios de aceitação

1. Todos os testes de pareamento e segurança listados passam, incluindo token só em hash, uso único, expiração, janela fechada, limite de tentativas, sessão única e token ausente dos logs.
2. Nenhum STUN ou TURN nos dois lados, e só candidatos da sub-rede da LAN na oferta aceita e na resposta (testes).
3. O código de confirmação bate com os três vetores do contrato no Python e no TypeScript.
4. Antes do Confirmar nenhum quadro passa o portão; depois passa (teste de integração aiortc com aiortc).
5. Celular real, mesma rede: ler o QR do terminal ou do console, ativar a câmera em paisagem, ver o mesmo código nas duas telas, Confirmar no console, ver `live` com a tally no celular. Com isso, `GET /api/status` mostra 1920x1080 e fps médio de pelo menos 29 em 60 s, medidos pelo agente. Registrar aparelho, navegador, codec negociado e bitrate médio.
6. Recusar no console encerra a sessão, o celular mostra `ended`, e o mesmo QR não funciona de novo.
7. Ler o mesmo QR depois de usado mostra `pairing_failed`; um segundo celular com sessão ativa mostra `busy`.
8. Desconectar no console encerra a sessão e o celular mostra `ended`.
9. e2e no compose com o fluxo completo (sessão, código igual, confirmação, `live`, `video` no status) verde, mais os e2e de token reutilizado e recusa.
10. `docs/contrato.md` igual ao que foi implementado; textos só em `locales/`, com paridade.
11. Verificação completa dos dois lados sem erros nem avisos; CI e CodeQL verdes; versão 0.3.0 no agente e no web.
12. Fase 1 de design aprovada pelo usuário antes do código de tela, com a skill de cada decisão; `impeccable audit` dos estados novos sem P0.
13. Dependabot configurado para não abrir PR de versão maior de `python`, `node`, `@types/node` e `typescript`.

## Riscos registrados

- O navegador pode descartar o fragmento `#t=` ao aceitar o aviso de certificado (planejamento §8). Testar no CA 5; se acontecer, a `/cam` mostra `missing_pairing` e o usuário lê o QR de novo, já com o certificado aceito.
- Candidatos `.local`: com a permissão de câmera concedida, Chrome e Safari mostram o IP real. Se o aparelho real só mandar `.local`, a conexão falha no filtro; registrar e decidir em correção.
- O estimador de banda do aiortc pode segurar o bitrate abaixo de 10 Mbit/s e o navegador reduzir a qualidade. O CA 5 mede; se ficar abaixo do esperado, vira item da v0.4.0, que é onde a qualidade da saída é medida (SSIM).
