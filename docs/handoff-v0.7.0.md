# Handoff v0.7.0, sessões agent, web e vcam

De: orquestrador (`wcam-cb`)
Spec: `docs/specs/spec-v0.7.0.md` (Aprovada em 2026-11-10), com "Decisões registradas"
Contrato: `docs/contrato.md` (versão 0.7.0): "Formato de vídeo" no lugar de "Opção de qualidade", `videoFormat` no status, `video_format` e `set_video_format` no DataChannel, `modes` em `camera_capabilities`, `orientation` em `session.video`
ADR: `docs/adr/0013-formato-escolhido-no-canal.md` (Proposta, aceita com o resultado do spike `vcam-format`)
Planejamento: §1 CA-2 com a emenda da v0.7.0; §5.3 (retrato); §5.4 (mudanças em menos de 300 ms); §5.7 (glossário)
Textos: chaves novas já em `locales/` na branch de integração (`format.*`, `console.format_pending`, `cam.portrait_hint`). As chaves `quality.*`, `cam.rotate_title` e `cam.rotate_body` saem no mesmo commit da sessão web que tira o uso delas, nos dois arquivos.

| Sessão | Worktree | Branch |
|---|---|---|
| agent | `.worktrees/agent-formato` | `feature/formato-agent` |
| web | `.worktrees/web-formato` | `feature/formato-web` |
| vcam | `.worktrees/vcam-formato` | `feature/formato-vcam` |

Os worktrees já existem, criados a partir de `feature/formato`. Antes do relatório, `git merge origin/feature/formato` para pegar o que mudar na integração.

## Ordem

1. **Spikes primeiro** (spec §0), em `spike/h264-levels` (agent e web juntos) e `spike/vcam-format` (vcam). O teste com o iPhone é feito pelo usuário; marquem comigo antes de pedir, porque o WCam dele pode estar em uso numa reunião. Nada de subir o agente nas portas 8080 e 8443 ou abrir a câmera sem combinar.
2. Cada spike termina com uma nota curta para mim (SendMessage): números, formatos que ficam, comportamento da troca com app aberto. Eu atualizo a tabela do contrato e a ADR 0013 na integração antes do código que depende disso.
3. O que não depende dos spikes começa já: retrato (§2), encerramento (§5), modos de câmera (§4), gerador de referência em vários tamanhos, desenho do seletor.

## Sessão agent

1. **Spike `h264-levels`, lado do agente.** Hoje a resposta do aiortc declara `profile-level-id` de nível 3.1. Medir com o iPhone, em cada formato da tabela: o tamanho e o fps que chegam decodificados, se o celular respeita o nível da resposta e, se respeitar, o ajuste mínimo na resposta SDP que libera até o nível 5.2. Ajuste em comportamento do aiortc segue a regra da v0.4.0: isolado num módulo, com teste que quebra se a versão do aiortc mudar. Taxa real de cada formato em 2 min com movimento.
2. **Formato** (spec §1.2, contrato "Formato de vídeo"). `PUT /api/video-format`, `videoFormat` no status, `video_format` e `set_video_format`, `available` pelas capacidades, troca para o maior formato que caiba quando a câmera muda, teto do REMB pela taxa do formato, chamada a `WcamFormatSet` no sink da câmera nativa (o sink falso e o do OBS aceitam o formato; o OBS só se ele aceitar trocar, senão registrar). Sai tudo de `quality_preset`. Testes para cada regra do contrato.
3. **Pipeline em vários tamanhos.** Aceitar o tamanho do formato anunciado em vez do 1920x1080 fixo; quadro de paisagem de outro tamanho não vai para a câmera (repete o último bom). Medir o tempo do worker por quadro em 2160p60 neste PC; se passar de 16,7 ms, processar em mais de um worker mantendo a ordem dos quadros.
4. **Retrato** (spec §2). Redução por área no YUV, sem RGB, centralizado com faixas Y=16, UV=128, com as mesmas tabelas de cor; `framesScaled` e `orientation`. Teste com quadro sintético de retrato: posição, largura da imagem e valores das faixas. A causa `portrait` sai do `episodes.log`.
5. **Encerramento** (spec §5). Ctrl+C imprime só `terminal.stopped`, código de saída 0. Teste automatizado com o processo real recebendo o sinal.
6. **Modos da câmera.** Aceitar e guardar `modes` em `camera_capabilities` (contrato).
7. **Referência e SSIM.** `make_reference` com largura e altura; o e2e e o SSIM aceitam a referência do formato em uso.
8. **Medição de codec** (spec §3): CPU do agente em cada formato com o iPhone por 2 min; fps médio em 10 min no maior formato. Números no relatório para a ADR 0014, que eu escrevo.
9. Versão 0.7.0 em `agent/pyproject.toml`.

## Sessão web

Skills de design obrigatórias e registradas em `docs/design-v0.7.0.md`, decisão por decisão: `taste-skill`, `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng` e `mobile-native` para o celular; `animate` e `review-animations` se houver movimento. O usuário achou "feio" o painel de qualidade da v0.6.0: este seletor é refeito do zero, não ajustado.

1. **Spike `h264-levels`, lado do celular.** Página de spike (ou parâmetro só de desenvolvimento) que aplica cada formato com `applyConstraints` e registra `getSettings()` e as estatísticas de envio (`outbound-rtp`: largura, altura, fps, taxa, `qualityLimitationReason`). Junto com o agent.
2. **Seletor no celular e no console** (spec §1.4). Duas escolhas, resolução e fluidez, só com os formatos de `available`. O marcado é sempre o do último `video_format` recebido (celular) ou do `videoFormat.selected` do status (console), nunca a escolha local. No console, taxa, fps medido e codec só na área de detalhes (`format.bitrate_limit`); `console.format_pending` quando `videoFormat.pending`. Acessível: estado marcado não só por cor.
3. **Aplicar o formato.** Ao receber `video_format`: `applyConstraints` com largura, altura e fps exatos (trocados em retrato) e `setParameters` com `maxBitrate`, sem renegociar. Tabela de formatos e montagem das restrições em `data/`, com Vitest; chamadas do navegador em `media/`.
4. **Retrato** (spec §2). Tirar o bloqueio de "Ao vivo" e o pedido de girar; em retrato, a dica `cam.portrait_hint`, discreta, sem cobrir o visor. Ao girar, reaplicar o formato com largura e altura trocadas. Tirar `cam.rotate_title`, `cam.rotate_body` e `quality.*` dos dois arquivos de `locales/` no mesmo commit.
5. **Modos da câmera** (spec §4). Pedir `exposureMode`, `whiteBalanceMode` e `focusMode` `continuous` quando o navegador expõe; `modes` em `camera_capabilities`. Montagem da mensagem com Vitest.
6. **e2e** (Playwright, câmera falsa do Chromium): mudar o formato no celular aparece no console e vice-versa em menos de 300 ms; o tamanho medido pelo agente acompanha em até 3 s; formato fora de `available` responde `422`; SSIM acima de 0,98 em 1080p30 e em cada formato que a câmera falsa entregar.
7. Versão 0.7.0 em `web/package.json`.

## Sessão vcam

1. **Spike `vcam-format`** (spec §0): media source anunciando um formato decidido pelo processo do agente na abertura; 1280x720, 2560x1440 e 3840x2160 a 30 e 60 fps no Chrome e no app Câmera; mudança de formato com app aberto (`MEStreamFormatChanged` ou equivalente) no Chrome, no app Câmera, no Teams e no OBS; se o agente consegue saber, sem a media source escrever no canal, que um app está com a câmera aberta e em qual formato. Teams e OBS precisam do usuário; marquem comigo.
2. **Canal e API** (spec §1.3, ADR 0013): largura, altura e fps no cabeçalho, posições para 3840x2160, `WcamFormatSet`, `WcamFramePublish` só no formato atual. Testes xUnit para cada regra, inclusive quadro de tamanho errado recusado.
3. **Media source:** um tipo de mídia, o formato do canal na abertura; quadros de espera e preto nesse formato; o comportamento de troca escolhido pelo spike.
4. Verificação no Frame Server, em cada formato que ficar na tabela: tamanho e fps no Chrome e no app Câmera, fps de pelo menos 95% do nominal por 2 min.
5. `dotnet publish -r win-x64 -c Release` sem avisos. Versão 0.7.0 no projeto.

## Adendo, 2026-11-10: resultado do spike `h264-levels`

- Tabela final no contrato ("Formato de vídeo"): `720p30`, `720p60`, `1080p30` (padrão), `1440p30` e `2160p30`. Saem `1080p60`, `1440p60` e `2160p60`, porque o Safari entrega 30 fps acima de 720p nas duas câmeras. Taxas mantidas, inclusive 35 Mbit/s em `2160p30`: o teto só limita quando o codificador o alcança, e na v0.6.0 o 1080p30 encheu os 20 Mbit/s da Máxima.
- Agent: a resposta SDP declara nível 5.1 (`42e033` e `420033`), isolado num módulo, com teste que quebra se a lista de codecs do aiortc mudar.
- Web: com a tabela final, a fluidez só tem escolha em 720p. A regra de esconder o grupo de uma opção só (aprovada no desenho) cobre isso.
- Achado aberto, agent e vcam: na rodada B, 720p60 chegou ao agente a cerca de 60 fps, mas o pipeline entregou à câmera nativa de 6 a 10 quadros/s depois de cerca de 20 s, com a câmera anunciada a 30 fps (DLL do spike no formato padrão). A vcam confere na sua janela se `WcamFramePublish` bloqueia quando o consumidor lê a 30 fps. O agent mede de novo com o pipeline no tamanho do formato e a câmera anunciada a 60 fps. O CA 2 (fps de pelo menos 95% do nominal por 2 min) vale também para 720p60.

## Adendo, 2026-11-10: resultado do spike `vcam-format`

- ADR 0013 aceita: o formato novo vale na próxima abertura. O Frame Server fixa o formato quando a câmera virtual inicia; `WcamFormatSet` faz a DLL reiniciar a câmera virtual (cerca de 5 s) quando nenhum app está recebendo vídeo da WCam. Com algum app recebendo, a troca fica pendente até o último parar. `MEStreamFormatChanged` descartado.
- Agent: `videoFormat.pending` existe de verdade. Enquanto a troca estiver pendente, o celular continua no formato que a câmera anuncia (`videoFormat.camera`), e o agente só envia o `video_format` novo ao celular quando a câmera reiniciar. Formato do celular e formato da câmera são estados separados.
- Vcam: propõe ao orquestrador a API C de estado (formato anunciado, troca pendente, consulta ou retorno do `WcamFormatSet`) antes de implementar; o monitor de atividade de sensores roda dentro da DLL.
- Ainda a verificar: modo 0 no app Câmera, 2 min por formato e, com o usuário, Teams e OBS (inclusive app que segura a câmera sem receber vídeo durante o reinício).

API C aprovada (vcam implementa, agent consome):
- `int WcamFormatSet(uint32 width, uint32 height, uint32 fps)`: `E_INVALIDARG` fora da tabela (os 5 formatos do contrato); antes de `WcamCameraStart`, guarda e vale no início (`S_OK`); com a câmera rodando e nenhum app recebendo vídeo, reinicia a câmera virtual antes de retornar (`S_OK`, pode bloquear cerca de 5 s: o agente chama fora do event loop); com app recebendo, fica pendente (`S_FALSE`) e a DLL aplica sozinha quando o último parar; pedir de novo o formato anunciado cancela a pendência (`S_OK`); falha no reinício devolve o `HRESULT` e deixa a câmera parada.
- `int WcamFormatGet(WcamFormatState* state)`: `S_OK` ou `E_POINTER`. Nove `uint32` em sequência: `width`, `height`, `fps` (anunciado), `requestedWidth`, `requestedHeight`, `requestedFps`, `pending`, `streamingApps`, `running` (0 durante o reinício e depois de falha).
- O agente consulta `WcamFormatGet` a cada 100 a 200 ms. `videoFormat.camera` e `virtualCamera.output` vêm do anunciado; `videoFormat.pending` vem de `pending`. Quando o anunciado passa a ser o pedido, o agente envia o `video_format` novo ao celular.
- `WcamFramePublish` aceita só o formato anunciado; outro tamanho volta `E_INVALIDARG`. O canal continua aberto durante o reinício.
- Sem callback da DLL para o Python.

## Fechamento

Relatórios em `docs/relatorio-v0.7.0-agent.md`, `docs/relatorio-v0.7.0-web.md` e `docs/relatorio-v0.7.0-vcam.md`, com cada CA da spec que a sessão toca, os números dos spikes e o que não foi verificado. PR de cada branch de sessão para `feature/formato`.
