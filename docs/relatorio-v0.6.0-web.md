# Relatório v0.6.0, sessão web

Spec: `docs/specs/spec-v0.6.0.md`
Contrato: `docs/contrato.md` (0.6.0: DataChannel nos dois sentidos, "Opção de qualidade", campos novos do status, `set_quality_preset` só em `live`, `frozen` depois de 0,5 s sem quadro)
Handoff: `docs/handoff-v0.6.0.md`, sessão web
Design: `docs/design-v0.6.0.md` (aprovado pelo orquestrador em 2026-11-06)
Branch: `feature/qualidade-web`, com `origin/feature/qualidade` integrada até 8ab7edb (agent e vcam da v0.6.0)

## 1. O que foi feito

Dados e mídia:
- `data/quality-preset.ts`: tabela das opções (`maximum` 20, `balanced` 10, `light` 5 Mbit/s), padrão `balanced`, validação da chave, nome, dica e nível do ícone de cada opção. Testes Vitest.
- `data/camera-capabilities.ts`: função pura que monta `camera_capabilities` com os máximos de `getCapabilities()`, o `facingMode` de `getSettings()` (`null` fora de `user` e `environment`) e os codecs sem `video/rtx`, `video/red` e `video/ulpfec` e sem repetição. Testes Vitest. A leitura no navegador fica em `media/camera-capabilities.ts`.
- `data/control-message.ts`: lê `quality_preset` (chave desconhecida ou ausente é ignorada) e escreve `set_quality_preset`. Testes Vitest.
- `media/use-publisher.ts`:
  - a oferta sai com o `maxBitrate` de `balanced`;
  - ao receber `quality_preset`, aplica o `maxBitrate` da opção com `setParameters`, sem renegociar; todas as chamadas de `setParameters` (inclusive o `degradationPreference`) passam por uma fila única, para duas não se cruzarem;
  - envia `camera_capabilities` quando o canal abre e a cada troca de faixa;
  - expõe a opção recebida e a escolha para a interface.
- `data/api-client.ts`: `changeQualityPreset` (`PUT /api/quality-preset`). Teste Vitest.
- `data/contract.ts`: `qualityPreset`, `virtualCamera.source` `frozen`, `session.cameraCapabilities`, `video.colorRange` e `colorMatrix`, e o `backend` `media_foundation`, que faltava no tipo desde a v0.5.0.
- `data/use-quality-choice.ts`: estado de espera da escolha, compartilhado pelas duas telas. A opção marcada é sempre a confirmada pelo agente; a escolhida fica "em espera" até a confirmação chegar, ou por no máximo 2 s.

Interface:
- `/cam`: `cam/quality-picker.tsx` (terceiro botão do trilho e painel), `cam/quality-option.tsx`, `cam/quality-icon.tsx` e `cam/use-dismiss.ts` (fechar tocando fora ou com Esc). O seletor só aparece em `live`, depois do primeiro `quality_preset`.
- `/`: `console/quality-panel.tsx`, sempre presente quando há status, abaixo do painel da sessão ou do QR. `console/virtual-camera-panel.tsx` mostra `console.source_frozen`.
- `data/use-console.ts`: o status passa a ser lido a cada 250 ms (antes 1 s). Motivo: uma troca feita no celular só chega ao console pelo status, e com 1 s o CA 8 (menos de 300 ms) não passava. O status é local (`127.0.0.1`) e barato. O SSE da v0.8.0 substitui esta leitura.

E2E:
- `e2e/quality-preset.spec.ts`, projeto `chromium`: troca no celular aparece no console, e no console aparece no celular, cada uma em menos de 300 ms.
- `e2e/light-quality.spec.ts`, projeto `quality`: depois de trocar para `light`, a taxa medida pelo agente fica abaixo de 5 500 kbps em até 5 s.
- `playwright.config.ts`: `workers: 1`. O agente aceita uma sessão só. Com dois arquivos de spec pareando um celular, o Playwright os rodou em paralelo, e o segundo caiu em `busy`. Aprovado pelo orquestrador.

Versão 0.6.0 em `web/package.json` e `package-lock.json`.

Commits: 507dd00, 5f32f35, 28057b6, 93b5455, 592a18d, 9c2276d, 327d3f9, ba6fe07, 1458433, 6c07c21.

## 2. Critérios de aceitação sob a sessão web

| CA | Situação | Evidência |
|---|---|---|
| 8, celular para console em menos de 300 ms | Verificado no e2e; pendente no iPhone | `quality-preset.spec.ts` (§5) |
| 8, console para celular em menos de 300 ms | Verificado no e2e; pendente no iPhone | `quality-preset.spec.ts` (§5) |
| 8, taxa acompanha a opção em até 5 s | Verificado no e2e | 6 930 kbps em `balanced`, 4 676 kbps depois de `light` (§5) |
| 10, capacidades e codecs do iPhone | Implementado; pendente do teste final | a mensagem sai quando o canal abre e a cada troca de câmera; os valores reais do iPhone ficam para o teste com o usuário |
| 11, SSIM do e2e de pelo menos 0,98 | Verificado | 0,9845, mínimo 0,9835, 52 quadros (§5) |
| 11, versão 0.6.0 no web | Verificado | `web/package.json` |
| Estado congelado no console | Implementado; não visto na tela | `frozen` mostra `console.source_frozen`; o e2e não provoca falta de quadro |
| Textos só em `locales/` | Verificado | nenhuma chave nova; o nome acessível do botão usa `quality.label` e a opção atual vai em `aria-describedby` |
| Verificação do web | Verificado | `npm run build` sem avisos, `npm run lint` limpo, `npm test` 50 passando |

**Pendente do teste final:** o visual das duas telas e o fluxo no iPhone. A extensão do Chrome não conectou nesta sessão, então nenhuma das duas telas foi vista por mim no navegador. O usuário vai validar o visual. O seletor no iPhone, as capacidades e os codecs reais entram no teste final com ele.

## 3. Skills de design

As decisões, uma por uma, estão em `docs/design-v0.6.0.md`, com a skill de cada uma. Resumo:

| Skill | Onde guiou |
|---|---|
| `impeccable shape` | brief, lugar do seletor nas duas telas, marca da escolha por forma, anel de espera com limite de 2 s, opção marcada vinda sempre do agente |
| `taste-skill` | ícone como medidor de quantidade (segmentos iguais, parte usada cheia) em vez de barras de sinal; tratado como componente dentro de um mundo visual já existente, sem sorteio de direção |
| `emil-design-eng` | painel aparecendo a partir do botão (`scale(0.96)` com opacidade, nunca de `scale(0)`), saída mais rápida que a entrada, `ease-out` forte, disco sem animação ao trocar de linha, `scale(0.97)` no toque |
| `mobile-native` | resposta no toque (`:active`), `overscroll-behavior: contain` na rolagem do painel, hover só com `(hover: hover) and (pointer: fine)`; o painel centrado no trilho para caber em telas de 360px a 390px de altura em paisagem |

O `impeccable audit` e o `polish`, que o handoff pede depois da implementação, não rodaram: dependem de ver a tela, e o navegador não conectou. Ficam para depois da validação visual do usuário.

## 4. Divergências e decisões do orquestrador

1. Seletor do console num painel próprio, sempre presente, em vez de dentro do painel da sessão: o painel da sessão só existe com celular conectado, e o handoff pede que o seletor funcione sem ele.
2. Leitura do status a cada 250 ms (§1).
3. Taxa em Mbit/s numa linha de detalhe em `--faint`, sem chave nova; o `<details>` fica para a v0.8.0.
4. Ícone: três segmentos iguais na horizontal, no lugar de barras de altura crescente, que leriam como força do Wi-Fi.
5. O teste de taxa roda no projeto `quality`. Na primeira versão, no projeto `chromium`, ele passava lendo 0 kbps antes e depois, porque a primeira janela de 1 s ainda não tinha fechado. Além disso, a câmera falsa padrão não garante passar de 5 500 kbps. Agora ele espera a taxa passar de 5 500 em `balanced` antes de trocar.

## 5. E2E no compose

`docker compose --profile e2e up --build --exit-code-from e2e` contra `feature/qualidade` (8ab7edb): 13 passaram, saída 0, cerca de 26 s.

| Medida | Valor |
|---|---|
| Celular para console | abaixo de 300 ms |
| Console para celular | abaixo de 300 ms |
| Taxa em `balanced` antes da troca | 6 930 kbps |
| Taxa depois de `light` | 4 676 kbps, em menos de 5 s |
| SSIM médio | 0,9845 |
| SSIM mínimo | 0,9835 |
| `quality.frames` | 52 |
| `session.video` na leitura do SSIM | 1920x1080, 29,9 fps, 6 526 kbps, VP8, `framesScaled` 0, `colorRange` `limited`, `colorMatrix` `unspecified` |

A câmera falsa do Chromium declara faixa limitada, então a normalização do agente não atuou, e o SSIM continua no nível da v0.4.0 (0,9851).

## 6. Notas técnicas

1. **Rádio controlado do React não dispara `change` nativo.** Num `<input type="radio">` controlado, o React restaura o `checked` durante o próprio `click`, então o navegador não vê mudança e não dispara `change`. É isso que mantém a opção marcada igual à do agente até a confirmação. Por isso o e2e mede o tempo a partir do `click`, que é a medida mais rigorosa, porque inclui o processamento.
2. **Medição de tempo no e2e.** O instante do toque e o da troca de `data-checked` na outra tela são lidos dentro do navegador, com `Date.now()`, que é o mesmo relógio nas duas páginas do mesmo navegador. O tempo dos comandos do Playwright fica fora da medida.

## 7. Dependências novas

Nenhuma.

## 8. Perguntas

Nenhuma.

## 9. Adendo: calibração de cor (spec §1.1, CA 3.1)

**Substituída pela correção pela câmera (decisão 10, §11).** O código desta seção saiu do produto; o texto fica como registro.

Integração: `origin/feature/qualidade` em 8e40b78, com o agent da calibração.

O que foi feito:
- `data/color-sample.ts`: monta o `color_sample` do contrato (RGB sem alfa em base64, `capturedAt` em ms). Testes Vitest.
- `media/use-color-sample.ts`:
  - desenha o quadro do `<video>` do visor num canvas 160x90 sem espelho, em `display-p3` quando o contexto aceita, senão `srgb`, e lê com `getImageData` no mesmo espaço;
  - envia 5 amostras, uma por segundo, com a sessão em `live`, em paisagem e fora da troca de câmera;
  - a contagem recomeça a cada nova faixa da câmera; em retrato, pausa e continua ao voltar para paisagem.
- `media/use-publisher.ts` expõe `sendControl`, e `cam/use-cam.ts` liga o hook. Sem texto nem elemento novo na tela.
- Console: `colorCalibration` em `data/contract.ts`; `colorCalibrationKey` em `data/console-format.ts` (Vitest) escolhe `console.color_matched` em `applied` e `console.color_default` nos outros estados; a linha fica em `--muted` no painel da sessão, abaixo da linha do formato de vídeo.
- O console não tolera agente sem `colorCalibration`: os dois lados saem juntos na v0.6.0 e o contrato garante o campo (decisão do orquestrador).
- `e2e/color-calibration.spec.ts`: em duas conexões seguidas, o status chega a `applied` ou `default` com `deltaE` numérico, e a segunda começa em `measuring`.

E2E no compose contra 8e40b78: 14 passaram, cerca de 45 s.

| Medida | Valor |
|---|---|
| Calibração, primeira conexão | `applied`, ΔE2000 0,11 |
| Calibração, segunda conexão | começou em `measuring`; `applied`, ΔE2000 0,16 |
| Amostras por conexão | 5, a 1 000 ms uma da outra, `display-p3` (e2e temporário, não commitado) |
| Taxa em `balanced` antes da troca | 6 505 kbps |
| Taxa depois de `light` | 4 218 kbps, em menos de 5 s |
| SSIM médio | 0,9854 |
| SSIM mínimo | 0,9836 |
| `quality.frames` | 31 |
| `session.video` na leitura do SSIM | 1920x1080, 28,6 fps, 9 730 kbps, VP8, `framesScaled` 0, `colorRange` `limited`, `colorCalibration` `measuring` |

**Ressalva do SSIM:** na leitura, a calibração ainda estava em `measuring`. O `QualityMeter` do agente acumula desde o início da sessão, então o SSIM acima é o da saída sem a curva aplicada. Medir o SSIM só com a calibração aplicada pede mudança no agente; levado ao orquestrador.

**Verificação manual pendente:** as 5 amostras novas a cada troca de câmera. A câmera falsa do Chromium não troca de faixa, então isso fica para o teste no iPhone do usuário.

### 9.1 Rodadas seguintes da calibração

O `quality.spec` passou a esperar `colorCalibration` `applied` ou `default` antes de exigir os 30 quadros (e80035a). O `color-calibration` exige ΔE abaixo de 2 com a câmera falsa padrão do Chromium (8b26564), e o canvas da amostra reduz com `imageSmoothingQuality` `high` (a568f52).

Rodada contra 8e40b78, com o agente antes de 9d5a3a6: no projeto `quality`, com a referência y4m, o vídeo caiu para 5,8 a 6,1 fps e de 2 673 a 3 846 kbps, e o `light-quality` falhou na pré-condição (sem passar de 5 500 kbps em `balanced`). Com o celular sem mandar `color_sample`, a mesma imagem do agente passou. A queda vinha do processamento da calibração no agente, corrigido em 9d5a3a6 (tabela sem dependência de conteúdo e máscara de detalhe).

Rodada contra 71016d0, só esta sessão no compose, com a série do `/api/status` a cada segundo, `docker stats` e `WCAM_COLOR_TRACE_DIR`: 13 de 14 passaram.

| Medida | Valor |
|---|---|
| Calibração, câmera falsa padrão, conexões 1 e 2 | `applied`, ΔE2000 0,16 e 0,22 |
| Taxa em `balanced` antes da troca | 6 112 kbps |
| Taxa depois de `light` | 4 654 kbps, em menos de 5 s |
| Referência y4m depois do `applied` | 29,5 a 31 fps, 8 747 a 9 479 kbps |
| Calibração com a referência y4m | `applied`, ΔE2000 4,36 |
| SSIM médio depois do `applied` | 0,9730 (mínimo 0,9726, 35 quadros): falha |
| Correlação das 20 amostras do trace | 0,897 a 0,990, todas aceitas |
| Tabela aplicada contra a de faixa | Y de −32 a +18 códigos; U e V de −15 a +16 |
| Carga do agente (`docker stats`) | média 64,9%, máximo 96,3% |
| `liquida-producer` e `liquida-consumer` (outro projeto) | médias 0,1% e 0,9%, pico 36,7%; o consumer reiniciava em loop |

O fps voltou ao normal. O SSIM caiu porque a calibração aproxima a saída da amostra do celular e a afasta da referência y4m (BT.601); antes do `applied`, a mesma referência dava 0,985. Decisão 8 da spec (opção b): o `QualityMeter` passa a comparar contra a referência passada pela mesma tabela de Y aplicada. A mudança do agente entrou em 3e581ab.

Rodada final contra f5de19d (merge local b0ef7f1), só esta sessão no compose, com a série do `/api/status`, `docker stats` e `WCAM_COLOR_TRACE_DIR`: 14 passaram, cerca de 44 s.

| Medida | Valor |
|---|---|
| Calibração, câmera falsa padrão, conexões 1 e 2 | `applied`, ΔE2000 0,16 e 0,22 |
| Taxa em `balanced` antes da troca | 6 858 kbps |
| Taxa depois de `light` | 5 411 kbps, em menos de 5 s |
| Referência y4m depois do `applied` | 22,6 a 32,1 fps (29,2 na leitura do SSIM), 7 467 a 10 400 kbps |
| Calibração com a referência y4m | `applied`, ΔE2000 4,56 a 4,57 (de matriz, fora do escopo, decisão 8) |
| SSIM médio depois do `applied` | 0,9865 (mínimo 0,9856, 51 quadros), contra a referência passada pela tabela de Y aplicada |
| Carga do agente (`docker stats`) | média 63,9% |
| `liquida-producer` e `liquida-consumer` | médias 0,1% e 4,4%, pico 23,9% |

CA 3.1 do lado web verificado no e2e. Fica pendente a verificação manual no iPhone: ΔE abaixo de 2 e as 5 amostras novas a cada troca de câmera.

## 10. Adendo: comparação lado a lado (spec §6, CA 3.3)

Integração: `origin/feature/qualidade` em e688f0e, com o agent da comparação.

O que foi feito:
- Celular:
  - responde `snapshot_request` em `live` com o PNG do visor no tamanho nativo, sem espelho, `display-p3` quando aceito, em `snapshot_begin` e pedaços de 45 000 bytes (`data/snapshot.ts`, Vitest);
  - o envio respeita `bufferedAmount`: fila em `media/use-publisher.ts`, que acima de 1 MB espera `bufferedamountlow`;
  - depois de um `snapshot_request`, mostra `cam.dev_send_screenshot` no canto inferior direito. O botão escolhe um PNG da galeria, confere a assinatura (`isPng`, Vitest) e envia `screenshot_begin` e os pedaços; o resultado aparece por 3 s.
- Console:
  - `console.dev_compare` no painel da sessão, só com `devTools` e `live` (`comparisonAvailable`, Vitest);
  - no mesmo clique, `POST /api/dev/comparisons` e a captura da câmera WCam (`media/wcam-camera.ts`: label "WCam" depois de um `getUserMedia`, canvas srgb no tamanho do vídeo, PNG), enviada por `PUT .../pc`;
  - imagens lado a lado com horário em milissegundos e a grade 8x4 sobre a imagem do PC: número em cada célula, contorno e número em `--warning` acima de 2;
  - dados em grupos (celular e PC; com o print, tela e celular, tela e PC), formatados em `data/comparison-format.ts` (Vitest);
  - downloads do celular, do PC, do print e do JSON;
  - print pelo console ou pelo celular, que aparece como terceira imagem.
- Decisões de design em `docs/design-v0.6.0.md` §6.

Para o e2e:
- O console no compose (`http://agent:8080`) não é contexto seguro, e sem isso `navigator.mediaDevices` não existe.
- O `playwright.config` ganhou `--unsafely-treat-insecure-origin-as-secure` para a URL do console, e o projeto `chromium` passou a usar `channel: "chromium"` (headless completo): o headless shell padrão ignora esse flag (testado: `isSecureContext` false no shell e true no canal `chromium`).
- A câmera WCam é simulada: a câmera falsa do Chromium com o label trocado para "WCam" por init script (o Chromium do compose não enxerga a WCam real).

E2E no compose contra e688f0e, sem portas publicadas: 18 passaram, cerca de 1,2 min.

| Medida | Valor |
|---|---|
| Comparação | imagens e dados em menos de 10 s depois do clique; os três downloads baixam; o print enviado pelo celular aparece como terceira imagem |
| Calibração, câmera falsa padrão | `applied`, ΔE2000 0,25 e 0,22 |
| Taxa em `balanced` e depois de `light` | 6 089 e 4 934 kbps |
| SSIM depois do `applied` | 0,9865 (mínimo 0,9856, 48 quadros), 31,3 fps |

Borda de baixo do `/cam`, com o aviso de tela acesa forçado e o botão do print, em paisagem (teste temporário, não commitado):

| Tela | Aviso (x) | Botão do print (x) | Folga | Último botão do trilho (fundo) e topo do botão do print |
|---|---|---|---|---|
| 667x375 | 20 a 396 | 519 a 647 | 123 px | 288 e 311 |
| 844x390 | 20 a 396 | 696 a 824 | 300 px | 295 e 326 |
| 932x430 | 20 a 396 | 784 a 912 | 388 px | 315 e 366 |

Sem sobreposição. Nas telas mais largas que 16:9, o vídeo fica com faixas pretas, e as pílulas em `--scrim` dos controles, inclusive o botão do print, ficam quase sem contorno sobre o preto, como já acontecia com o trilho. Fica para a validação visual.

**Pendente:** uso pelo usuário no iPhone, com a WCam real no PC, antes de aprovar o CA 3.

## 11. Adendo: correção de cor pela câmera e falhas da comparação (spec §1.1, §6, CA 3.1 e 3.3, decisão 10)

Integração: `origin/feature/qualidade` em 455db77, com o agent da correção pela câmera.

Correção pela câmera:
- Sai o envio de `color_sample`: o hook, a montagem da mensagem e os testes. O `toBase64` foi para `data/base64.ts`, com Vitest, e o tipo do canvas para `data/snapshot.ts`. A `sendControl` pública do publisher saiu.
- `camera_capabilities` leva `colorSpace` (`data/camera-capabilities.ts`, com Vitest; campos ausentes viram `null`).
- A leitura fica em `media/camera-capabilities.ts`:
  - espera o `<video>` do visor mostrar a faixa atual, até 2 s;
  - faz `new VideoFrame(video)`, com `MediaStreamTrackProcessor` num clone da faixa como alternativa;
  - devolve `null` sem `VideoFrame` e sempre chama `frame.close()`.
- A mensagem sai quando o canal abre e a cada troca de câmera, e só se a faixa ainda for a mesma quando a leitura termina.
- Console: `colorCorrection` com `console.color_matched` em `applied` e `console.color_default` nos outros casos; `correction` no tipo da comparação.
- e2e: `color-correction.spec.ts` substitui o `color-calibration.spec.ts`. O `quality.spec` espera a correção existir (`cameraCapabilities` recebido) antes de contar os quadros.

Falhas da comparação (bug do teste de 2026-11-07, "missing" na tela):
- A câmera WCam abre ANTES do `POST` (`openWcamCamera`): permissão resolvida, label "WCam" achado depois do primeiro `getUserMedia`, primeiro quadro recebido. Só então o `POST` e a captura do quadro saem juntos, seguidos do `PUT .../pc`. A câmera fecha no fim.
- Se a câmera não abre, a comparação não é criada:
  - NotAllowedError, SecurityError ou página sem `mediaDevices` dão `camera_denied`;
  - NotFoundError, OverconstrainedError ou label ausente dão `camera_missing`;
  - NotReadableError ou AbortError dão `camera_busy`;
  - qualquer outro erro dá `camera_failed`.
- Cada motivo vira um texto próprio (`comparisonFailureKey`, com Vitest): os `reason` do contrato, `no_live_session` e os problemas da câmera. Qualquer outro código cai em `errors.<code>` ou `errors.unknown`. `console.dev_compare_failed` saiu.
- e2e novo: com `getUserMedia` rejeitando com NotAllowedError, o alerta mostra `console.dev_compare_camera_denied`, e o celular não recebe `snapshot_request` (o botão do print não aparece).

E2E no compose contra 455db77, sem portas publicadas: 16 passaram, cerca de 1,0 min. Vitest 73.

| Medida | Valor |
|---|---|
| Câmera falsa padrão, `colorSpace` declarado | primaries, transfer e matrix `smpte170m`, `fullRange` false |
| Correção com a câmera falsa padrão | `default`, transfer `smpte170m`, display `standard` |
| Comparação | as duas imagens, os três downloads e o print do celular em 8,1 s de teste |
| Comparação com permissão negada | texto `console.dev_compare_camera_denied`, nenhuma comparação criada |
| Opção de qualidade, celular para console e console para celular | abaixo de 300 ms |
| Taxa em `balanced` e depois de `light` | 7 633 e 4 927 kbps |
| SSIM (referência y4m) | 0,9837, mínimo 0,9831, 34 quadros, 30,1 fps |
| Correção com a referência y4m | `default`, transfer `null`: o Chromium não declara transferência para y4m, o que é esperado (orquestrador) |

**Pendente:** o teste manual do usuário no iPhone: a correção em `applied` com `bt709` e `apple`, e a comparação com a câmera WCam real.

