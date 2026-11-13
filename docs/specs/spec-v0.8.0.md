# Spec v0.8.0, Console

Status: Aprovada (2026-11-12)
Branch de integração: `feature/console`
Sessões: `agent`, `web`
Referências: `docs/planejamento.md` §4 (segurança), §5.1 a §5.7 (interface), §6 (roteiro da 0.8.0); ADR 0010 (código de confirmação); spec v0.7.0 e changelog (achados); protótipo aprovado pelo usuário em 2026-11-12: https://claude.ai/artifact/4j5uK8opMCjxa2iy1p1F8b

## Objetivo

1. **Segurança: confirmação nos dois lados.** Hoje só o PC confirma o código, e o celular já envia vídeo e mensagens antes disso. Nesta versão, nada sai do celular antes de o código ser confirmado no celular e no PC.
2. **Console definitivo.** QR, estado e prévia em tempo real, controles, indicador de câmera frontal ou traseira, métricas só em Detalhes.
3. **Congelar imagem e Desligar câmera.** O antigo Pausar vira duas funções, decididas pelo usuário em 2026-11-12.
4. **Console do desenvolvedor (`/dev`).** Página só de gráficos em tempo real do sistema funcionando, pedida pelo usuário em 2026-11-11.
5. **Bandeja do Windows.** Ícone com o estado e menu rápido com os controles.
6. **Linguagem.** Revisão de todos os textos (§5.7 do planejamento), com teste que falha se um termo proibido aparecer.
7. **Medição de zoom e lentes** no iPhone do usuário, para a spec seguinte (zoom real e enquadramento no PC).

A câmera virtual (`vcam`) não muda nesta versão.

## 0. Spike antes do código

- **`spike/zoom` (web, iPhone do usuário, Safari):** página temporária, só na branch do spike, que registra para cada câmera de `enumerateDevices()` o rótulo, `getCapabilities()` e `getSettings()` completos (`zoom`, `torch`, `focusMode`, `focusDistance`, `pointsOfInterest`, `exposureCompensation`, `exposureMode`, `whiteBalanceMode`, largura, altura, fps). Para cada câmera com `zoom`, aplica com `applyConstraints` o mínimo, 1, 2 e o máximo e registra o `getSettings()` e o tamanho do quadro depois de cada um. Registra também se a ultra-angular e a teleobjetiva aparecem como dispositivos separados, se trocar de dispositivo com a conexão aberta funciona com `replaceTrack`, e se a câmera frontal expõe o enquadramento aberto (zoom abaixo de 1 ou outro dispositivo). O resultado vai para `docs/relatorio-v0.8.0-web.md` e alimenta a spec v0.9.0. Nenhum código do spike entra na branch da sessão.

## 1. Confirmação nos dois lados

Hoje: o celular adiciona a faixa de vídeo antes da oferta e envia `camera_capabilities` assim que o DataChannel abre; o agente descarta os quadros até o Confirmar do PC (`FrameGate`). Um QR lido por outra pessoa já faz o vídeo dela trafegar até o PC antes de qualquer confirmação.

Regra nova: **o celular não envia nenhum pacote de vídeo e nenhuma mensagem, salvo a própria confirmação ou recusa, antes de o código ser confirmado nos dois lados.**

### 1.1 Web (`/cam`)

- A oferta continua com uma faixa de vídeo para a SDP negociar codec e taxa, mas o transceiver nasce sem faixa (`addTransceiver("video", {direction: "sendonly"})`). A faixa da câmera entra com `replaceTrack` só quando chega `session_state` `live`, sem renegociar.
- A câmera pode ser aberta antes, para o visor mostrar a imagem enquanto o usuário confere o código, mas nada é enviado.
- Em `awaiting_confirmation`, o celular mostra o código grande, a pergunta "O código no computador é igual a este?" e dois botões: **É igual** (`confirm_code`) e **É diferente** (`reject_code`). Depois de É igual, mostra que espera a confirmação no computador.
- `camera_capabilities`, `set_video_format` e qualquer outra mensagem só saem depois de `live`.
- Se o usuário tocar em É diferente, o celular envia `reject_code`, a conexão termina com `rejected`, e a tela explica que outra pessoa pode ter lido o QR code e que é preciso gerar um novo no computador.

### 1.2 Agent

- `session.confirmations` com `pc` e `phone`. A sessão vai para `live` só com os dois `true`; aí o agente envia `session_state` `live`.
- Antes de `live`, toda mensagem do celular que não seja `confirm_code` ou `reject_code` é ignorada com log, e todo pacote RTP de vídeo recebido é contado em `rtpPacketsBeforeLive` (log e status de desenvolvimento). O `FrameGate` continua como segunda camada.
- `reject_code` encerra com `rejected`, igual ao Recusar do console. O tempo limite de confirmação (`confirmation_timeout`) vale para os dois lados.
- O terminal, ao abrir uma conexão, diz onde confirmar: "Confira o código no console deste computador e no celular." (`terminal.confirm_hint`).

### 1.3 Testes

- Agent, integração com um celular aiortc: nenhum pacote RTP de vídeo chega antes das duas confirmações (`rtpPacketsBeforeLive` 0), com cada ordem possível (PC primeiro, celular primeiro); mensagem de controle antes de `live` é ignorada; `reject_code` encerra com `rejected`.
- Web, Vitest: a lógica do publicador só chama `replaceTrack` com a câmera depois de `live`, e só envia `confirm_code` ou `reject_code` antes disso.
- e2e com um falso computador: o teste altera a impressão digital da resposta (o código do celular fica diferente do mostrado no console), o celular toca em É diferente, e o agente registra 0 pacote de vídeo e encerramento `rejected`. Um segundo caso confirma só no PC e espera o tempo limite: 0 pacote.

## 2. Console (`/`)

Direção visual: o protótipo aprovado (artboards "Console: aguardando celular", "Console: confirmar código" e "Console: ao vivo"), com os tokens de §5.6 e as regras do CLAUDE.md. A sessão web registra em `docs/design-v0.8.0.md` a direção de `impeccable shape`, a revisão de `emil-design-eng` e o `impeccable audit` final.

### 2.1 Estados

| Estado | O que domina |
|---|---|
| Aguardando celular | QR grande, contagem de 2 min, três passos (mesmo Wi-Fi, aviso do certificado, conferir o código), QR code novo |
| Confirmar | código grande, "O código no celular é igual a este?", estado de cada lado (este computador, celular: aguardando ou confirmado), É igual e É diferente, recusar |
| Ao vivo | prévia, tally, controles, painel do celular, caminho da imagem, Detalhes |
| Imagem congelada | prévia parada com aviso de desde quando, Descongelar em destaque |
| Câmera desligada | prévia preta com "Câmera desligada" e Ligar câmera |
| Sinal perdido, problema | como no planejamento §5.2 |

- Painel do celular: aparelho (`deviceName`), câmera em uso (frontal ou traseira, de `cameraCapabilities.facingMode`, com seletor visual das duas) e orientação.
- Caminho da imagem: Celular, Wi-Fi, WCam no computador, Apps, cada trecho com estado em texto e marca.
- Detalhes (recolhível): resolução, fps, taxa, codec, formato da câmera, CPU. É o único lugar com termo técnico.
- O seletor de formato da v0.7.0 continua, refeito no visual do console.
- Link "Desenvolvedor" para `/dev`.

### 2.2 Tempo real

O console troca a consulta periódica do status por SSE (`GET /api/events`). Qualquer mudança aparece em menos de 300 ms (planejamento §5.4).

### 2.3 Prévia

- A prévia mostra o que os apps recebem: com espelho, congelamento e o quadro de câmera desligada aplicados.
- Fonte: uma segunda conexão WebRTC entre o console e o agente, só em `127.0.0.1`, aberta quando a prévia está ligada e fechada quando desligada ou quando o console fecha. O agente envia o quadro entregue à câmera, reduzido para 960x540 (ou a altura do formato, se menor), a no máximo 30 fps. A redução vale só para a prévia; a câmera virtual não muda (CA-2).
- Desligar a prévia fecha a conexão e economiza CPU; a câmera virtual não é afetada.
- ADR 0015 registra a escolha (WebRTC local em vez de imagens JPEG periódicas) com o custo de CPU medido neste PC em 1080p30 e 2160p30. Se a prévia passar de 10 pontos de CPU do processo, ela cai para 15 fps, e o relatório registra.

## 3. Controles

Decisão do usuário (2026-11-12): o antigo Pausar vira duas funções. Todas existem no console, no celular e na bandeja, e a mudança aparece nos três em menos de 300 ms.

| Controle | Efeito | Nos apps | Celular |
|---|---|---|---|
| Congelar imagem / Descongelar | o agente repete o último quadro entregue | imagem parada | continua enviando vídeo; mostra "Imagem congelada no computador" |
| Desligar câmera / Ligar câmera | o celular para a faixa (`track.stop()`, o indicador de câmera do sistema apaga) e envia `replaceTrack(null)`; a conexão continua | quadro de câmera desligada (abaixo) | visor preto com Ligar câmera |
| Trocar câmera | o celular troca entre frontal e traseira | imagem da outra câmera | como hoje |
| Espelhar | o agente espelha horizontalmente o quadro antes da câmera | imagem espelhada | não muda o visor (planejamento §5.3) |
| Desconectar | encerra; voltar exige QR novo | como hoje | como hoje |

- Congelar não existe com a câmera desligada; Ligar câmera com a imagem congelada descongela.
- Quadro de câmera desligada: preto (Y=16, UV=128) com o ícone de câmera riscada no centro, desenhado pelo agente no formato anunciado, sem texto (vale para qualquer idioma). `virtualCamera.source` `camera_off`.
- Espelhar inverte as colunas dos planos Y, U e V, sem redimensionar nem mudar a cor (não fere o CA-2). Vale até o agente fechar.
- Congelar e Desligar câmera não sobrevivem ao fim da conexão: a próxima começa ao vivo.
- O antigo "Pausar" do planejamento §5.4 é substituído por estas duas linhas (§8).

## 4. Console do desenvolvedor (`/dev`)

Pedido do usuário (2026-11-11), desenho do artboard "Console do desenvolvedor". Só no console (`127.0.0.1`), sem variável de ambiente; a comparação lado a lado da v0.6.0 continua atrás de `WCAM_DEV_TOOLS`. Aqui termos técnicos são permitidos (é a área de detalhes do produto), mas os textos continuam em `locales/`.

### 4.1 Layout

- Cabeçalho: estado, tempo ao vivo, aparelho, navegador, câmera, formato e codec; janela de 30, 60 ou 120 s; **Pausar gráficos** (congela os gráficos, não a câmera); **Exportar CSV** (todas as amostras guardadas na página, até 10 min).
- Faixa de saúde: fps entregue, taxa, processamento p95, pacotes perdidos na janela, CPU do processo e ida e volta. Cada número com estado em texto (ok, atenção) além da cor e um minigráfico.
- Caminho do quadro: Celular, Wi-Fi, Decodificar, Cor, Entrega, Apps, com a mediana de cada trecho.
- Grade: à esquerda, ocupando duas linhas, a prévia (§2.3) com Congelar imagem, Desligar câmera e Trocar câmera; à direita, em cima, quadros por segundo (celular e câmera, linha de 30) e orçamento do quadro (decodificar, cor, entrega empilhados, linha do orçamento do fps); embaixo, taxa recebida (linha do teto do formato) e rede (ida e volta, jitter, marcas de perda).
- Linha de baixo: histograma do tempo por quadro, câmera do WCam (formato anunciado e pendente, apps usando, quadros entregues e descartados), celular (pedido e entregue, câmera, limitação de qualidade, intervalo de quadro-chave) e eventos.
- Eventos aparecem também como marcas verticais nos gráficos.
- Gráficos em SVG desenhado pelo próprio código, sem biblioteca nova: são no máximo seis séries de até 120 pontos a 1 Hz.

### 4.2 Dados

- `GET /api/dev/events` (SSE, só no console): evento `metrics` a cada 1 s e evento `event` a cada acontecimento. A coleta detalhada (tempos por etapa, estatísticas do celular) só roda com pelo menos um assinante; sem assinante, o custo é zero.
- O celular envia `stats` a cada 1 s só depois de o agente pedir (`stats_request` com `enabled`), a partir de `RTCPeerConnection.getStats()`: `outbound-rtp` (fps codificado, quadros enviados, bytes, `qualityLimitationReason`, quadros-chave, `nackCount`, `pliCount`, largura e altura) e `remote-inbound-rtp` (`roundTripTime`, `jitter`, `packetsLost`). Campo que o Safari não informa vai `null`.
- O agente mede por quadro: decodificação, tradução de cor (inclui retrato e espelho), entrega à câmera e total; descartes da fila; quadros entregues. Mediana e p95 por segundo, mais as amostras do total para o histograma.
- Atraso fim a fim fica fora desta versão.

## 5. Bandeja do Windows

Ícone na área de notificação do Windows, criado pelo agente com `pystray` (já previsto no planejamento, dependência nova justificada aqui), em thread própria com dono e encerramento explícito. Só no Windows; fora dele, ou sem `pystray`, o agente segue sem bandeja e registra no log.

- Ícone em cinco estados, cada um com cor **e** forma do selo (§5.4 do planejamento, protótipo "Bandeja: console rápido"): ao vivo (círculo cheio, `--data`), imagem congelada (quadrado, `--data-2`), câmera desligada (duas barras, `--warning`), aguardando (círculo vazado, `--muted`), problema (triângulo, `--negative`). Dica do ícone com o estado em texto.
- Menu nativo: estado e câmera em uso (só leitura); Congelar imagem ou Descongelar; Desligar câmera ou Ligar câmera; Trocar câmera; Espelhar (marcado quando ligado); Abrir console; Mostrar QR code (abre o console em Aguardando); Desconectar celular; Sair (encerra como o Ctrl+C).
- Os itens que exigem conexão ficam desabilitados sem celular.
- O painel rico do protótipo (miniatura e botões grandes) depende da janela WebView2 e fica para a v1.0.0. Iniciar com o Windows e Idioma ficam para a persistência.

## 6. Linguagem

- Revisão de todas as chaves de `locales/` contra o glossário (planejamento §5.7), incluindo as oito chaves do levantamento de 2026-11-01.
- Teste (agent, pytest, porque `locales/` é lido pelos dois lados) que falha se um termo proibido aparecer em `en.json` ou `pt-BR.json`: agente, servidor, sessão, token, pareamento, requisição, interface, e os equivalentes em inglês. Exceções só para chaves `dev.*` (console do desenvolvedor) e `terminal.fingerprint`, listadas no próprio teste.

## 7. Contrato (`docs/contrato.md` vai para 0.8.0)

Console:
- `GET /api/events`: `text/event-stream`, evento `status` com o mesmo JSON de `GET /api/status`, enviado ao conectar, a cada mudança e a cada 1 s. `GET /api/status` continua.
- `PATCH /api/controls` com qualquer subconjunto de `{"frozen": bool, "cameraOff": bool, "mirror": bool, "facing": "user" | "environment"}`: `204`; `409 no_live_session` para `frozen`, `cameraOff` e `facing` sem sessão `live`; `422 invalid_request`.
- `POST /api/preview` com `{"sdp": "<oferta>"}`: `201 {"sdp": "<resposta>"}`; `DELETE /api/preview`: `204`. Uma prévia por vez; uma nova substitui a anterior.
- `GET /api/dev/events`: `text/event-stream`, eventos `metrics` e `event` (formato no handoff e no contrato).
- `GET /api/status` ganha `"controls": {"frozen", "cameraOff", "mirror", "facing"}` no primeiro nível, sempre presente, e `session.confirmations: {"pc", "phone"}`. `virtualCamera.source` ganha `held` (congelada pelo usuário) e `camera_off`.
- `POST /api/sessions/current/confirm` passa a marcar só `confirmations.pc`.

DataChannel `control`:
- Celular para o agente, únicas aceitas antes de `live`: `{"type": "confirm_code"}` e `{"type": "reject_code"}`.
- Agente para o celular: `{"type": "confirmation", "pc": bool, "phone": bool}` a cada mudança em `awaiting_confirmation`.
- Agente para o celular: `{"type": "controls", "frozen", "cameraOff", "mirror", "facing"}` quando o canal abre e a cada mudança, venha de onde vier.
- Celular para o agente: `{"type": "set_controls", ...}` com o mesmo subconjunto do `PATCH`; só em `live`.
- Agente para o celular: `{"type": "stats_request", "enabled": bool}`; celular para o agente: `{"type": "stats", ...}` a cada 1 s enquanto ligado.
- `camera_capabilities` e `set_video_format` só depois de `live`.

Erros: `no_live_session` (409) entra na tabela geral (hoje só nas rotas de desenvolvimento).

## 8. Planejamento

Antes do código, o orquestrador emenda `docs/planejamento.md`:
- §4: o código de confirmação é conferido nos dois lados, e nada sai do celular antes das duas confirmações.
- §5.2 e §5.3: estados Imagem congelada e Câmera desligada no lugar de Pausado; botões É igual e É diferente no celular.
- §5.4: Pausar sai; entram Congelar imagem e Desligar câmera; ícone da bandeja com cinco estados.
- §6: a 0.9.0 passa a ser "Zoom e enquadramento" (zoom real no celular, controlado pelo console e pelo celular; enquadramento recortado no PC, com ADR que abre exceção ao CA-2), e as linhas seguintes andam uma versão.

## Textos

Chaves novas em `locales/en.json` e `locales/pt-BR.json` no mesmo commit, na branch de integração, antes do código: estados e textos do console, botões É igual e É diferente, confirmação de cada lado, controles novos, painel do celular, caminho da imagem, menu e dicas da bandeja, `terminal.confirm_hint` e as chaves `dev.*`. A lista exata vai no handoff.

## Fora do escopo

- Zoom real, enquadramento no PC e controles de foco, lanterna e exposição (v0.9.0, depois do spike).
- Atraso fim a fim no console do desenvolvedor.
- Janela WebView2, painel rico da bandeja, Iniciar com o Windows, Idioma, Parar WCam separado de Sair (v1.0.0 e persistência).
- Histórico de conexões (persistência).
- Mudança na câmera virtual nativa.

## Decisões registradas

- 2026-11-12, falso computador (§1.3): o e2e troca o `confirmationNonce` da resposta em vez da impressão digital. Trocar a impressão digital na SDP derruba o DTLS, e o celular nem chega a enviar `reject_code`. O efeito pedido é o mesmo: o código do celular diverge do console. O caso do tempo limite usa os 120 s reais.
- 2026-11-12, caminho da imagem (§2.1): `virtualCamera.streamingApps` entra em `GET /api/status` (contrato), para o trecho Apps mostrar quantos apps usam a câmera sem ligar a coleta de `/api/dev/events`.

- 2026-11-12, Espelhar no celular (§3, CA 4): o CA vale sobre o "não" do planejamento §5.4. Espelhar existe no `/cam`, mas não na coluna de botões, que comporta cinco no celular deitado: fica na folha do Formato como o interruptor "Espelhar nos apps". O visor do celular não muda.

- 2026-11-12, e2e da prévia: o serviço `e2e` do compose roda com `network_mode: "service:agent"`, porque a prévia só aceita candidatos de loopback (contrato) e, em containers separados, não conecta. Os endereços `E2E_*` não mudam.

## Critérios de aceitação

1. Spike `zoom` registrado no relatório web, com a tabela por câmera do iPhone do usuário.
2. Confirmação nos dois lados: os testes da §1.3 passam, incluindo o falso computador; no fluxo real, nenhum vídeo aparece no console nem nos apps antes de É igual no celular e no PC, em qualquer ordem.
3. CA-3 completo: QR no console, console e `/cam` com desenhos próprios, todos os estados da §2.1 vistos pelo usuário.
4. Controles: Congelar imagem, Desligar câmera, Trocar câmera e Espelhar funcionam no console, no celular e na bandeja, e a mudança aparece nos outros dois em menos de 300 ms (medido no e2e para console e celular). Desligar câmera apaga o indicador de câmera do iPhone. Trocar a câmera pelo console muda a imagem no Meet.
5. Prévia: mostra o que os apps recebem; desligada, a conexão de prévia fecha; CPU registrada na ADR 0015.
6. Console do desenvolvedor: todos os painéis da §4.1 com dados reais do iPhone do usuário; Pausar gráficos e Exportar CSV funcionam; sem assinante, a coleta detalhada não roda (teste).
7. Bandeja: cinco estados com cor e forma, menu funcionando, Sair encerra limpo.
8. Linguagem: teste da §6 passa; nenhum termo proibido fora de Detalhes e de `/dev`.
9. CA-2 mantido: SSIM de pelo menos 0,98 no e2e com prévia ligada e com Espelhar desligado.
10. Verificação completa do CLAUDE.md, `npm run test:e2e` e fluxo real no iPhone; `version` 0.8.0 em `agent/pyproject.toml` e `web/package.json`.
