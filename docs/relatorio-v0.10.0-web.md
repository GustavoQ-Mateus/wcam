# Relatório v0.10.0, sessão web

Spec: `docs/specs/spec-v0.10.0.md` · Handoff: `docs/handoff-v0.10.0.md` · Contrato: `docs/contrato.md` 0.10.0 · Branch: `feature/performance-web` (worktree `.worktrees/web-performance`) · Design: `docs/design-v0.10.0.md`

## 1. Detalhes do console (spec §2)

- Linha "Decodificação" com "Placa de vídeo" ou "Processador", logo depois do codec, só na área de detalhes (`console/details-panel.tsx`). Vem de `session.video.decoder`, ou de `videoSource.decoder` com o vídeo ativo (`currentDecoder` e `decoderKey` em `data/console-format.ts`). Sem linha quando `null`.
- `Decoder` (`hardware` | `software`) entrou em `Video` e `VideoSource` em `data/contract.ts`.
- Com a ADR 0019 o celular ao vivo decodifica no processador com `WCAM_HW_DECODE=auto`, então os detalhes mostram "Processador" com o celular; nada mudou na web por isso.

## 2. `/dev` (spec §2)

- Etapa `transfer` ("Transferência": passagem de NV12 para I420 e cópia entre processos, contrato 0.10.0) no gráfico de tempos por etapa, logo acima de "Decodificar", em `--data` com hachura a 45 graus (pattern SVG), a mesma hachura na legenda; sem token novo, decisão do orquestrador. Com `transfer` 0 (processador) a faixa não tem altura e a legenda some.
- Caminho do quadro: a etapa aparece entre "Decodificar" e "Cor" só com mediana acima de 0.
- Lista de eventos: rótulos para `decoder`, `video_source` e `timeline`. O `data` de cada evento continua como JSON cru, então qualquer `reason` (incluindo `live_phone` da ADR 0019) aparece sem chave nova.
- CSV: `transfer_median_ms` e `transfer_p95_ms` logo depois das colunas de decodificação.
- Indicador "Processamento p95" (CA 7): limite revisto pelo agent e aprovado pelo orquestrador. Fica em atenção só acima de `budgetMs`, o tempo de um quadro no formato atual (33,3 ms em 30 fps, 16,7 ms em 60 fps). Antes era metade disso, e ficava em atenção em 83 a 98% dos segundos em 4K sem perda de quadro (medição do agent).
- O `delivered_fps` que oscilava de 0 a 430 no CSV do usuário (2160p30, 2026-11-23 00:39 a 00:49Z) não era da web: o CSV grava o `delivered.fps` do evento como vem, e a diferença de `delivered.frames` entre linhas ficava entre 29 e 31. Era a janela do agent dividida entre assinantes de `/api/dev/events`, corrigida no agent (e8098a8).

## 3. Zoom da linha do tempo por Ctrl com a roda (spec §2)

- Ctrl com a roda sobre a régua e os clipes aproxima e afasta pelos mesmos níveis dos botões (`console/editor-timeline.tsx`, `console/video-editor.tsx`). O ouvinte não passivo fica em `media/use-ctrl-wheel.ts`, para impedir o zoom da página só sobre a faixa.
- Um entalhe da roda é um nível; os deltas pequenos do trackpad se somam até 50 px (`wheelZoom` em `data/timeline.ts`). O ponto sob o cursor fica parado; no limite do zoom o scroll não muda. Sem animação.

## 4. Testes

- Vitest: 217 testes. Novos: decodificador vindo do celular ou do vídeo ativo e `null` sem quadro, rótulos "Placa de vídeo" e "Processador" (`console-format.test.ts`); limite do p95 com 25, 33,3 e 33,4 ms em 30 fps (`dev-metrics.test.ts`); colunas `transfer` no CSV; etapa no caminho do quadro só com a placa; faixa `transfer` pelo p95 (`dev-view.test.ts`); um entalhe e a soma dos deltas do trackpad (`timeline.test.ts`).
- e2e: `quality.spec.ts` agora exige `session.video.decoder` igual a `software` junto do SSIM; `dev.spec.ts` exige a coluna `transfer_median_ms` no CSV.
- e2e completo no estado final (feature/performance-web c0fe1c1 com feature/performance-agent e8098a8, worktree temporário, compose sem portas no host): **33 de 33 passaram**. SSIM do CA-2: 0,9842 (mínimo 0,9837, 34 quadros, 1920 × 1080, VP8, `decoder` `software`). A primeira rodada achou `decoder` `null` com VP8, que o agent corrigiu (3f5c8ad).

## 5. Critérios de aceitação que a sessão web toca

| CA | Situação |
| --- | --- |
| 4 (SSIM no e2e) | SSIM 0,9842 no e2e, acima de 0,98, com `decoder` `software`. A igualdade byte a byte é do agent. |
| 7 | Detalhes e `/dev` mostram o decodificador e a etapa `transfer`; indicador com o limite revisto. |
| 8 | `npm run build` sem avisos, `npm run lint` e `npm test` verdes; `npm run test:e2e` 33 de 33; `version` 0.10.0 em `web/package.json`. |

## 6. Não verificado

- Visual no navegador e no `/dev` com a placa de vídeo: não abri as telas (sem subir o WCam nas portas 8080 e 8443). Fica com o usuário: linha "Decodificação", faixa hachurada e o zoom com Ctrl e a roda.
- Fluxo real com o celular (`uv run wcam` e QR): não rodei nesta sessão; as medições com o celular são do agent.
- O zoom com trackpad (pinça) só foi testado pela função pura, não num trackpad real.
