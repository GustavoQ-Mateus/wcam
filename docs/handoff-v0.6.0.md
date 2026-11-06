# Handoff v0.6.0, sessões agent, web e vcam

De: orquestrador (`wcam-ae`)
Spec: `docs/specs/spec-v0.6.0.md` (Aprovada em 2026-11-06), com "Decisões registradas"
Contrato: `docs/contrato.md` (versão 0.6.0): DataChannel nos dois sentidos, "Opção de qualidade", campos novos em `GET /api/status`
Planejamento: §1 CA-2 com a emenda da v0.6.0; §5.4 (mudanças em menos de 300 ms); §5.7 (glossário)
Textos: chaves novas já em `locales/` na branch de integração (`terminal.scan_in_console`, `console.source_frozen`, `quality.*`)

As três sessões trabalham ao mesmo tempo. O ponto de encontro entre agent e web é o contrato; entre agent e vcam, nada muda na API C da DLL. Qualquer mudança de contrato, chave de idioma ou API passa por mim antes do código.

| Sessão | Worktree | Branch |
|---|---|---|
| agent | `.worktrees/agent-qualidade` | `feature/qualidade-agent` |
| web | `.worktrees/web-qualidade` | `feature/qualidade-web` |
| vcam | `.worktrees/vcam-qualidade` | `feature/qualidade-vcam` |

Os worktrees já existem, criados a partir de `feature/qualidade`. Antes do relatório, `git merge origin/feature/qualidade` para pegar o que mudar na integração.

## Sessão agent

1. **Faixa de cor** (spec §1). Ler a faixa e a matriz de cada quadro decodificado (`color_range`, `colorspace` e o formato `yuvj420p` do PyAV). Faixa cheia é normalizada por tabela de consulta com numpy (Y: `16 + Y × 219 / 255`; U e V: `128 + (C − 128) × 224 / 255`; arredondamento ao inteiro mais próximo), no mesmo worker da conversão para NV12, fora do event loop. Faixa limitada e não declarada passam sem mudança. `session.video.colorRange` e `colorMatrix` no status. Testes: 0 vira 16, 255 vira 235, croma 128 fica 128, faixa limitada sai byte a byte igual, o quadro `yuvj420p` decodificado é reconhecido como faixa cheia.
2. **Congelar** (spec §2). Sem quadro novo, repetir o último quadro bom por até 3 s; depois, o preto de hoje. `virtualCamera.source` `frozen` nesse intervalo. Teste com relógio controlado: 3 s com tolerância de 0,2 s e depois Y=16, UV=128.
3. **Recuperar.** Primeiro o teste de laboratório no pytest: cliente aiortc enviando vídeo ao agente, um pacote e o seu reenvio descartados, tempo sem quadro medido de ponta a ponta. Com o teste reproduzindo a trava, implemente a recuperação: pacotes RTP chegando sem quadro saindo do buffer de recepção por mais de 500 ms, o agente descarta o trecho travado e pede quadro-chave (PLI). Critério: o vídeo volta em até 1 s a 5 Mbit/s. O relatório descreve o mecanismo e os números antes e depois. Mexer em atributo interno do aiortc segue a regra da v0.4.0: isolado num módulo, com teste que quebra se a versão do aiortc mudar o comportamento.
4. **Registro de episódios.** Uma linha JSON por episódio de mais de 500 ms sem quadro novo com sessão `live`, em `<WCAM_DATA_DIR>/logs/episodes.log`, com `logging.handlers.RotatingFileHandler` (1 MB, um arquivo antigo). Campos: `startedAt`, `endedAt` (UTC ISO 8601), `durationMs`, `cause` (`silence`, `stalled`, `portrait`), `action` (`frozen`, `black`), `rtpBytes`, `pliSent`. Teste: nenhuma linha contém token, `#t=`, URL de pareamento ou IP do celular.
5. **Opção de qualidade.** `PUT /api/quality-preset`, `qualityPreset` no status, mensagens `quality_preset` e `set_quality_preset` no DataChannel, teto do REMB igual à taxa da opção (substitui o `PHONE_MAX_BITRATE_BPS` fixo; a estimativa inicial continua começando no teto). Padrão `balanced`. A escolha vale para a sessão atual e as próximas, só em memória.
6. **Mensagens do celular.** Primeira vez que o agente lê o DataChannel: `set_quality_preset` e `camera_capabilities` (guardada em `session.cameraCapabilities`). Qualquer outra coisa é ignorada com log, sem derrubar a sessão. Teste para cada formato inválido do contrato.
7. **QR fora de arquivo.** Em `cli.py`, o QR e a URL com token só vão para a saída quando ela é um terminal interativo (`isatty`). Senão, `terminal.scan_in_console` com a URL do console. Teste com a saída redirecionada: nenhum `#t=` escrito.
8. **Benchmark** (spec §5): `python -m wcam.tools.decode_benchmark`, decodificando H.264 sintético gerado pelo próprio PyAV em 1280x720, 1920x1080, 2560x1440 e 3840x2160, a 30 e 60 fps, com a CPU do processo por formato. Rode nesta máquina e registre a tabela no relatório. Sem teste além de um de fumaça com um formato pequeno.
9. Versão 0.6.0 em `agent/pyproject.toml`.

## Sessão web

Skills de design obrigatórias e registradas no relatório, decisão por decisão: `taste-skill`, `impeccable` (`shape` antes, `audit` e `polish` depois), `emil-design-eng` e `mobile-native` para o celular; `animate` e `review-animations` se houver movimento.

1. **Seletor de qualidade no celular** (`/cam`). Visor em tela cheia, operado com uma mão: o seletor entra junto dos controles que já existem (`capture-controls`), sem cobrir a imagem, com as três opções e a dica curta de cada uma (`quality.*_hint`). A taxa em Mbit/s não aparece no celular. Escolher envia `set_quality_preset`; a opção marcada é sempre a do último `quality_preset` recebido, nunca a escolha local, para celular e console nunca divergirem. Acessível: estado marcado não só por cor.
2. **Aplicar a taxa.** Ao receber `quality_preset`, `sender.setParameters` com o `maxBitrate` da opção, sem renegociar (`use-publisher.ts`; a tabela de taxas fica num módulo de dados, com teste Vitest). Antes do primeiro `quality_preset`, a oferta sai com a taxa de `balanced`.
3. **Capacidades.** Quando o canal abre e a cada troca de câmera, enviar `camera_capabilities` como no contrato (`getCapabilities()` da faixa em uso e `RTCRtpSender.getCapabilities("video")`, sem `video/rtx`, `video/red` e `video/ulpfec`). A montagem da mensagem é função pura, testada no Vitest. Chamadas de API do navegador ficam em `media/`.
4. **Seletor no console** (`/`). No painel da sessão: as três opções, a dica e a taxa em Mbit/s numa área de detalhes (`quality.bitrate_limit`). Escolher chama `PUT /api/quality-preset`; o valor mostrado vem do `qualityPreset` do status. Funciona também sem celular conectado, porque vale para a próxima sessão.
5. **Estado congelado no console.** `virtualCamera.source` `frozen` mostra `console.source_frozen`.
6. **e2e** (Playwright, câmera falsa do Chromium): mudar no celular aparece no console e vice-versa em menos de 300 ms; depois de mudar para `light`, a `bitrateKbps` do status fica abaixo de 5 500 em até 5 s. O SSIM do e2e continua acima de 0,98.
7. Versão 0.6.0 em `web/package.json`.

Verificado no navegador antes de declarar pronto; no iPhone do usuário, no teste final.

## Sessão vcam

1. **Atributos de cor do tipo de mídia.** Declarar em `MediaStream.cs` `MF_MT_VIDEO_NOMINAL_RANGE` (`MFNominalRange_16_235`), `MF_MT_YUV_MATRIX`, `MF_MT_VIDEO_PRIMARIES` e `MF_MT_TRANSFER_FUNCTION`, pelo CsWin32 (`NativeMethods.txt`).
2. **Medição da matriz.** No probe (`--pattern`), barras de cor com valores YUV conhecidos em faixa limitada. Para BT.709 e para BT.601 declarados, ler o RGB que chega ao Chrome (canvas sobre `getUserMedia`) e ao app Câmera (captura de tela), e comparar com o esperado de cada matriz. A matriz escolhida é a que o Chrome e o app Câmera decodificam corretamente; o relatório traz a tabela. Se os dois apps discordarem, me traga os números antes de escolher.
3. **Quadro real do iPhone.** Com o agente da sessão agent e o iPhone do usuário, comparar a WCam no app Câmera com a prévia do celular, na matriz escolhida. Combine o horário com o usuário por mim.
4. Testes xUnit para os atributos novos do tipo de mídia.
5. Versão 0.6.0 no projeto .NET.

A API C (`WcamCameraStart`, `WcamCameraStop`, `WcamFramePublish`) e o canal de quadros não mudam. A DLL nova precisa ser registrada de novo pelo usuário (`scripts/register-vcam.ps1`, como administrador); avise antes de pedir.

## Verificação

- agent, a partir de `agent`: `uv run ruff check`, `uv run ruff format --check`, `uv run pyright`, `uv run pytest`.
- web, a partir de `web`: `npm run build` sem avisos, `npm run lint`, `npm test`, `npm run test:e2e` no compose.
- vcam, a partir de `vcam`: `dotnet build` sem avisos, `dotnet test`, `dotnet publish -r win-x64 -c Release` sem avisos de trimming ou AOT.

## Teste final, com o usuário

Na ordem: comparação lado a lado em pouca luz (CA 3); 10 min na Máxima sem episódio no Wi-Fi dele (spec §3); reunião de pelo menos 30 min no novo Teams na Máxima, com o `episodes.log` guardado (CA 7). Capacidades e codecs do iPhone registrados (CA 10).

## Relatórios

`docs/relatorio-v0.6.0-agent.md`, `docs/relatorio-v0.6.0-web.md` e `docs/relatorio-v0.6.0-vcam.md`, no formato de sempre, com o CA da spec que cada item cumpre. Commits sem referência a Claude ou Anthropic; push da própria branch liberado; PR não. Me avisem (`wcam-ae`) ao fechar cada etapa e antes de qualquer pedido ao usuário.

## Adendo: calibração de cor (2026-11-06)

Spec §1.1, CA 3.1 e 3.2, decisões 5 a 7. Contrato: mensagem `color_sample` e `session.video.colorCalibration`. Textos: `console.color_matched` e `console.color_default`, já em `locales/`. Os spikes `spike/color-space` (agent) e `spike/color-sample` (web) são referência de medição e não entram como estão: o código novo sai na branch de cada sessão, sem `WCAM_SPIKE_DIR` nem gravação em disco.

Sessão agent:
1. Aceitar `color_sample` só em `live`; validar formato (contrato) e descartar o resto com log.
2. Anel de quadros reduzidos dos últimos 2 s, ativo só enquanto houver amostra a comparar; casamento por correlação de luminância (com e sem espelho), descarte abaixo de 0,8.
3. Ajuste com pelo menos 3 amostras válidas: curva de tom monotônica no Y e ganho de saturação no U e V, minimizando o ΔE2000 entre amostra e saída corrigida lida como BT.709 limitada no espaço de cor da amostra. Só aplica se reduzir o ΔE2000.
4. Correção composta com a tabela de faixa numa tabela só por plano, no mesmo worker; custo por quadro igual ao de hoje.
5. `colorCalibration` no status; recomeça em `measuring` a cada conexão e troca de câmera; nada em disco.
6. Testes do CA 3.1 (curva e ganho conhecidos recuperados, correlação baixa descartada, `default` byte a byte igual, nada guardado entre conexões, `color_sample` antes do `live` ignorado).
7. No relatório: ΔE2000 antes e depois no iPhone do usuário e o custo por quadro.

Sessão web:
1. Hook em `media/` que, em `live` e paisagem, envia 5 `color_sample` (uma por segundo), e de novo a cada troca de câmera; em retrato, espera o paisagem. Montagem da mensagem em `data/`, com Vitest.
2. Console: linha na área de detalhes com `console.color_matched` (`applied`) ou `console.color_default` (outros estados).
3. e2e: a cada conexão o status chega a `applied` ou `default` com `deltaE` preenchido, e a conexão seguinte recomeça em `measuring`; SSIM acima de 0,98.

Sessão vcam:
1. Verificação de ponta a ponta para o teste final: quadro lido pelo Chrome na câmera WCam (`getUserMedia`) contra a amostra do celular do mesmo instante, ΔE2000 médio. Ferramenta de desenvolvimento, fora do produto; o método vai no relatório. Combine comigo o que precisar do agente (por exemplo, gravar amostras com horário quando uma variável de desenvolvimento estiver definida).
