# Relatório v0.7.0, sessão web

Spec: `docs/specs/spec-v0.7.0.md`
Contrato: `docs/contrato.md` (0.7.0: "Formato de vídeo" no lugar de "Opção de qualidade", `videoFormat` no status, `video_format` e `set_video_format` no DataChannel, `modes` em `camera_capabilities`, `orientation` em `session.video`)
Handoff: `docs/handoff-v0.7.0.md`, sessão web
Design: `docs/design-v0.7.0.md` (direção aprovada pelo orquestrador em 2026-11-10; audit e polish na §7)
Branch: `feature/formato-web`, com `origin/feature/formato` integrada até 4ab616d (agent, vcam e web da v0.7.0) e `origin/main`

## 1. Itens do handoff

| Item | Estado |
|---|---|
| 1. Spike `h264-levels`, lado do celular | Feito na branch local `spike/h264-levels` (9a23b81), fora da integração; os números ficam no relatório do agent |
| 2. Seletor no celular e no console | Feito |
| 3. Aplicar o formato | Feito |
| 4. Retrato | Feito |
| 5. Modos da câmera | Feito |
| 6. e2e | Feito; SSIM só em 1080p30 (§5) |
| 7. Versão 0.7.0 | Feito |

## 2. O que foi feito

Spike `h264-levels` (só na branch do spike):
- Ao ficar `live`, o celular percorre os formatos da tabela: `applyConstraints` exato (com `ideal` se o exato falhar), `maxBitrate` com `setParameters` e amostras de `outbound-rtp` por segundo. Envia `spike_format_start`, `spike_format_report` e `spike_format_done`, com a janela de cada formato definida pelo agente em `spike_format_plan`.
- Formato que não entrega o pedido no `getSettings` encerra cedo, com `settings_mismatch`.
- O resultado definiu a tabela final: 720p30, 720p60, 1080p30 (padrão), 1440p30 e 2160p30.

Dados (`data/`, com Vitest):
- `video-format.ts`: tabela final, regra das duas escolhas e restrições exatas, com largura e altura trocadas em retrato.
  - Escolher uma resolução mantém a fluidez se ela existir ali; senão, usa a que existir.
  - Escolher uma fluidez mantém a resolução se ela a tiver; senão, usa a maior resolução que tenha.
- `format-view.ts`: opções de cada grupo, marcada sempre a confirmada, espera só na opção que difere, e grupo de uma opção escondido.
- `format-name.ts`: nome do formato (`format.name`).
- `control-message.ts`: lê `video_format` (formato fora da tabela ou campo faltando é ignorado) e escreve `set_video_format`.
- `api-client.ts`: `changeVideoFormat` (`PUT /api/video-format`).
- `camera-capabilities.ts`: `modes` com os três modos de `getSettings()`, `null` quando o navegador não informa.
- `cam-state.ts`: sai o estado `rotate`; `ready` e `preview_off` levam `portrait`; `capture_changed` atualiza o formato mostrado.
- `constraint-failure.ts`: texto do registro de falha de `applyConstraints`.
- Saem `quality-preset.ts` e `use-quality-choice.ts`; `use-format-choice.ts` guarda a espera da escolha, como na v0.6.0.

Mídia (`media/`):
- `use-publisher.ts`: ao receber `video_format`, aplica o `maxBitrate` com `setParameters`, sem renegociar, e expõe o formato à interface. A oferta sai com a taxa de 1080p30.
- `apply-video-format.ts` e `use-video-format.ts`: aplicam o formato à faixa e o reaplicam ao girar. Depois atualizam o formato mostrado com o `getSettings`.
- **`applyConstraints` em duas chamadas:** primeiro o tamanho e o fps sozinhos, depois os mesmos com os modos contínuos em `advanced`. O Chromium mantém o tamanho antigo quando os modos vêm na mesma chamada; o e2e mostrou a faixa presa em 1920x1080 depois da troca para 720p.
- `camera-modes.ts`: pede `exposureMode`, `whiteBalanceMode` e `focusMode` `continuous` quando o navegador os oferece.
- Falhas de `applyConstraints`, no formato e nos modos, vão para `console.warn` com o formato pedido e o nome do erro, sem reenvio de `camera_capabilities`, que não mudaria `available` (decisão do orquestrador).

Interface:
- `/cam`:
  - `cam/format-picker.tsx` é o terceiro botão do trilho, com o ícone de enquadramento;
  - o painel mostra o formato atual em destaque, as pílulas de resolução (`resolution-option.tsx`) e as linhas de fluidez com dica (`frame-rate-option.tsx`).
- Retrato (spec §2):
  - o `/cam` segue ao vivo em pé, com `cam.portrait_hint` numa pílula no topo;
  - o trilho vira fileira embaixo, e o painel abre acima dela;
  - o aviso de tela acesa e o botão do print sobem para cima da fileira;
  - saem `rotate-prompt`, `rotate-phone-icon` e as chaves `cam.rotate_*`.
- Console:
  - `console/format-panel.tsx`: o título é o formato escolhido, `console.format_pending` aparece com `pending`, e a grade de rótulo e controle segmentado traz a resolução e a fluidez com a dica;
  - só `format.bitrate_limit` no detalhe; o fps medido e o codec continuam na linha `console.video_format`.
- Sai o aviso `console.frames_scaled` do painel da sessão: pelo contrato 0.7.0, `framesScaled` conta só quadros de retrato, que são o comportamento normal. A chave saiu dos dois locales.
- Saem as chaves `quality.*` dos dois locales.

E2E:
- `video-format.spec.ts`:
  - a resolução escolhida no celular aparece no console, e a do console no celular, cada uma em menos de 300 ms;
  - o tamanho que chega ao agente acompanha o formato em até 3 s;
  - formato fora de `available` responde `422`.
- `light-quality.spec.ts`: a troca para 720p30 baixa a taxa medida para menos de 5 500 kbps em até 5 s.
- `cam.spec.ts`: o celular em pé fica ao vivo, com pareamento real e quadro de 1080x1920, mostra a dica e os controles e volta ao formato padrão no fim.
- `playwright.config.ts`: a câmera falsa do Chromium passa a 60 fps (`--use-fake-device-for-media-stream=fps=60`), para o agente oferecer 720p60.

Versão 0.7.0 em `web/package.json` e `package-lock.json`.

## 3. Critérios de aceitação sob a sessão web

| CA | Situação | Evidência |
|---|---|---|
| 1, spike registrado | Lado web feito | branch `spike/h264-levels`; números no relatório do agent |
| 3, sincronia em menos de 300 ms nos dois sentidos | Verificado no e2e; pendente no iPhone | `video-format.spec.ts` |
| 3, tamanho acompanha em até 3 s | Verificado no e2e | `video-format.spec.ts` |
| 3, fora das capacidades não aparece nem é aceito | Verificado | `format-view` (Vitest) e `422` no e2e |
| 5, retrato ao vivo sem reconectar | Verificado no e2e; pendente no iPhone | `cam.spec.ts` |
| 7, modos contínuos, sem controle manual | Implementado; os modos do Safari ficam para o teste com o usuário | `camera-modes.ts` e `modes` em `camera_capabilities` |
| 9, desenho registrado | Verificado; aprovação visual é do usuário | `docs/design-v0.7.0.md` |
| 10, SSIM e versão | SSIM verificado em 1080p30; versão 0.7.0 | §4 |

## 4. Verificação final

Contra 4ab616d, com `origin/main` incluída:

- `npm run build` sem avisos, `npm run lint` limpo, Vitest 88.
- `npm run test:e2e` no compose, sem portas publicadas: 18 passaram, cerca de 1,3 min.

| Medida | Valor |
|---|---|
| Troca para 720p30 | 5 925 kbps antes, 3 297 kbps depois, em menos de 5 s |
| SSIM médio | 0,9838 |
| SSIM mínimo | 0,9833 |
| `quality.frames` | 33 |
| `session.video` na leitura do SSIM | 1920x1080, 26,8 fps, VP8, `framesScaled` 0, `orientation` `landscape` |

## 5. Achados

1. **Pico do codificador acima do `maxBitrate` em janela de 1 s.** Numa rodada, o agente mediu 17 573 kbps em 1080p30, com `maxBitrate` de 10 Mbit/s. O diagnóstico no e2e mostrou que o lado web aplica o teto certo desde o primeiro `video_format`: `encodings[0].maxBitrate` fica em 10 000 000 em todos os segundos, com um encoding só. O envio medido no `outbound-rtp` oscilou de 2 763 a 11 786 kbps, com média de cerca de 7 300. Os picos acima de 10 000 vêm logo depois de quedas de fps por falta de CPU no container, quando o codificador (VP8, libvpx) recupera a qualidade. É comportamento do codificador numa janela curta de medida, não do web; ficou com o orquestrador e o agent (janela de medida mais longa ou REMB). Por isso o e2e não confere kbps <= `maxBitrate` em janela de 1 s.
2. **`available` da última câmera.** Depois que a sessão termina, o agente mantém o `available` da última `camera_capabilities`, e um `PUT` fora dele responde `422`. É o contrato (decisão do orquestrador). No e2e, uma câmera de 720x1280 deixava só os formatos de 720p e o agente passava ao 720p60, que seguia escolhido nos testes seguintes. O teste do retrato passou a usar um quadro de 1080x1920 e volta ao padrão no fim.
3. **SSIM por formato.** O e2e mede o SSIM só em 1080p30, o tamanho da referência y4m; os outros formatos dependem do gerador de referência em vários tamanhos, do lado do agent.

**Pendente com o usuário:** a validação visual das duas telas, deitado e em pé; a troca de formato e os modos informados pelo Safari no iPhone.

## 6. Skills de design

As decisões, uma por uma, estão em `docs/design-v0.7.0.md`, com a skill de cada uma. O audit e o polish foram feitos só pela leitura do código e pelo e2e, sem captura de tela (decisão do usuário), e estão na §7 do design. O detector não teve achados. O polish deu às linhas de fluidez a resposta ao toque das pílulas (`mobile-native`) e fez o formato mostrado acompanhar a troca.

## 7. Dependências novas

Nenhuma.
