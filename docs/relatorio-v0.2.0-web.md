# Relatório v0.2.0, sessão web

Spec: `docs/specs/spec-v0.2.0.md`
Design: `docs/design-v0.2.0-cam.md` (fase 1, aprovado em 2026-11-01)
Handoff: `docs/handoff-v0.2.0-web.md`
Branch: `feature/captura-web` (com `origin/feature/captura` até d759262 e o texto de `cam.unavailable_in_use` integrados)

## 1. O que foi feito

Fase 1: `docs/design-v0.2.0-cam.md`, com taste-skill, impeccable shape, mobile-native e emil-design-eng (commit f0d0d01).

Fase 2:
- `data/cam-state.ts`: máquina de estado pura com os oito estados da spec, eventos `start`, `granted`, `failed`, `frame_changed` e `preview_toggled`, e o mapa de erro do `getUserMedia` para `denied` ou o motivo de `unavailable`. Paisagem é decidida pelo quadro do vídeo (`videoWidth > videoHeight`).
- `data/pairing.ts`: lê `#t=` do endereço, guarda o valor só em memória e apaga o fragmento com `history.replaceState`. É chamado quando o chunk da `/cam` carrega, antes da primeira renderização.
- `media/capture.ts`: restrições (`facingMode`, 1920x1080 ideal, 30 fps ideal, sem áudio), espelho só na frontal, formato a partir de `getSettings()` com fps inteiro.
- `media/use-camera-stream.ts`: abre a câmera, para as faixas atuais antes de abrir a nova (troca de câmera), ignora respostas atrasadas de pedidos antigos, mostra o vídeo só depois do primeiro quadro e reabre a mesma câmera quando a faixa termina e a página volta a ficar visível.
- `media/use-orientation.ts`: acompanha o evento `resize` do vídeo e manda `frame_changed`.
- `media/use-wake-lock.ts`: pede o Wake Lock em `ready` e `preview_off` e de novo ao voltar à página; sem suporte ou com o pedido recusado, informa a falta.
- `cam/`: `cam-page`, `use-cam` (compõe a máquina e os hooks), `message-layer`, `cam-message` e `cam-messages` (os cinco estados de antes da câmera), `viewfinder`, `live-layer`, `capture-controls`, `control-button`, `capture-readout`, `preview-cover`, `rotate-prompt`, `screen-notice`, `primary-button` e os três ícones em SVG.
- `styles/tokens.scss`: tokens do design (tipo 13/16/24, `--space-5`, margens com área segura, alvos, raios, ícones, easing, durações e opacidades); saem `--text-small` e `--text-lead`. O console não usava nenhum dos dois; o título dele passa de 32 para 24px porque `--text-title` mudou, e o e2e do console segue verde.
- `styles/base.scss`: `overscroll-behavior: none`, botão sem estilo do navegador com `touch-action: manipulation` e sem seleção, utilitário `visually-hidden`.
- Testes Vitest: os oito da spec mais quatro (prévia liga e desliga, sem pareamento ignora eventos, endereço sem fragmento fica intacto, fps arredondado). Total do web: 18.
- E2E: os cinco cenários da spec mais os dois que já existiam (HTTPS e chunk do console), com câmera falsa do Chromium (`--use-fake-device-for-media-stream`, `--use-fake-ui-for-media-stream`), viewport de celular e toque. Retrato usa um quadro em retrato vindo de um canvas por script de inicialização, porque a câmera falsa só entrega quadro deitado.
- `tsconfig.node.json`: lib DOM para os scripts de página dos e2e.

Commits: e97a598, 9c44cca, 6eb2edc.

## 2. Critérios de aceitação

| CA | Situação | Evidência |
|---|---|---|
| 1 | Verificado | Fase 1 aprovada pelo usuário antes do código; design registra a skill de cada decisão. |
| 2 | Não verificado | Precisa de celular real. Na câmera falsa do Chromium o `ready` mostra `1920 × 1080 · 20 fps` (a câmera falsa entrega 20 fps), o que prova que o formato vem de `getSettings()`. |
| 3 | Verificado em e2e; falta o celular real | e2e `cam with a portrait frame shows rotate`: aparece o `rotate` e nenhum controle do `ready`. |
| 4 | Não verificado | Precisa de celular real com duas câmeras. A lógica para a faixa atual antes de abrir a outra. |
| 5 | Verificado em e2e; falta o celular real | e2e `turning the preview off...`: texto de `preview_off` visível e `readyState` da faixa `live`. O indicador de câmera do sistema só no aparelho. |
| 6 | Não verificado | Precisa de celular real (2 minutos parado). O headless do Chromium recusa o pedido de Wake Lock, e o aviso de tela acesa aparece, como previsto. |
| 7 | Parcial | e2e `cam shows denied...` mostra `denied` com "Tentar de novo". Voltar a pedir depois de liberar só no aparelho. |
| 8 | Verificado | e2e de paisagem confere que o endereço fica sem `#` depois de abrir; teste Vitest `pairing fragment is read and removed from the address`. |
| 9 | Verificado | Todo texto vem de `t()`; as chaves novas estão nos dois idiomas (teste de paridade de chaves verde). |
| 10 | Verificado | e2e `cam page does not load the console chunk`; build com `cam-page-*.js` e `console-page-*.js` separados. |
| 11 | Verificado (local, compose e CI) | Em `web/`: `npm run build` sem avisos, `npm run lint` limpo, `npm test` 18 passando. Compose: `docker compose --profile e2e up --build --exit-code-from e2e`, 7 de 7 contra o agente real, saída 0. CI verde no push de 6eb2edc (§7). |
| 12 | Verificado | `impeccable audit`: 18/20, nenhum P0; o único P1 foi corrigido (ver §3.2). |

## 3. Skills na fase 2

### 3.1 taste-skill

| Passo | Resultado | O que corrigi |
|---|---|---|
| `lint.mjs --app web/src` | 0 FAIL, 0 WARN | nada |
| `inspect.mjs --app` no build de produção, 390, 360 e 844px, `missing_pairing` | 2 FAIL `[headline-lines]`: a instrução ocupava 3 linhas a 390 e 360px; 1 WARN `[no-poster]` | Estrutura: a marca virou o `h1`, e o título do estado virou `h2` quando tem corpo ou `<p>` quando é frase sozinha (9c44cca). O FAIL só saiu com texto mais curto: propus e o orquestrador aprovou `cam.missing_pairing` e `cam.unavailable_unsupported` (d759262). Depois: 0 FAIL. |
| `inspect.mjs --app`, `intro` | 0 FAIL, 1 WARN `[no-poster]` | nada |
| WARN `[no-poster]` | defendido | O vídeo é a câmera ao vivo, não um clipe; fica transparente até o primeiro quadro, então nunca aparece uma caixa cinza. |
| Rodada de olhar (screenshots de todos os estados em 844×390, 390×844 e 640×360, pt-BR) | `cam.unavailable_in_use` em 3 linhas a 390px com quebra "Feche-/o"; formato da captura em `--muted` sobre `--scrim` sem contraste em imagem clara | Texto novo proposto e aprovado; formato em `--ink` (6eb2edc). |

O `inspect` não tem câmera falsa: os estados com câmera foram vistos pelas screenshots do Playwright.

### 3.2 impeccable

`detect` no código (47 arquivos) e na página renderizada (390×844 e 844×390, `/cam` e `/cam#t=teste`): nenhum achado.

Audit:

| # | Dimensão | Antes | Depois | Achado principal |
|---|---|---|---|---|
| 1 | Acessibilidade | 2 | 3 | formato da captura sem contraste sobre imagem clara (P1, corrigido) |
| 2 | Desempenho | 4 | 4 | só `opacity` e `transform`, sem blur; chunk da `/cam` com 9,7 kB |
| 3 | Temas | 4 | 4 | tudo em token; ícones em `currentColor` |
| 4 | Responsivo | 3 | 3 | alvos de 52 a 56px; margens com área segura; disco do trilho encosta na borda da imagem em telas 20:9 (P3, aberto) |
| 5 | Integridade | 3 | 4 | recusa do `play()` virava "Câmera bloqueada" (P2, corrigido) |
| | Total | 16/20 | 18/20 | Excelente |

Achados e o que foi feito:

| Severidade | Achado | Feito |
|---|---|---|
| P1 | Formato da captura em `--muted` sobre `--scrim`: em imagem clara o contraste caía para cerca de 2,3:1 | `--ink` (6eb2edc) |
| P2 | `video.play()` recusado seria lido como permissão negada | o erro do `play()` é ignorado; o `autoplay` mudo segue tocando (6eb2edc) |
| P2 | `aria-live` na seção que remonta a cada estado não anuncia a troca | `aria-live` no contêiner fixo da camada de mensagens (6eb2edc) |
| P3 | `ready` e `preview_off` sem cabeçalho | `h1` visualmente oculto com `app.name` (6eb2edc) |
| P3 | Anel de foco branco some sobre imagem clara nos botões do visor | aberto: teclado num celular é raro; fica para a spec de front |
| P3 | Em telas 20:9 o disco do trilho encosta na borda da imagem | aberto: é o desenho aprovado (`--scrim` sobre a faixa preta); avaliar no aparelho |
| P3 | `rotate` montado depois de `requesting` pode não ser anunciado por leitor de tela | aberto |

Polish: feito no mesmo passo, na ordem da skill (estado enganoso, depois acessibilidade, depois cosmético), sem mudar o desenho aprovado.

### 3.3 emil-design-eng

Revisão de toque, transições e estados contra a §6 do design:

| Antes | Depois | Por quê |
|---|---|---|
| vídeo aparecia no `loadedmetadata` | aparece no `loadeddata` (primeiro quadro) | a §6 pede o vídeo só depois do primeiro quadro, sem flash de vídeo vazio |
| `play()` com erro interrompia a abertura | `play()` sem bloquear | a abertura não pode falhar por um detalhe de reprodução |

Conferidos e conformes: toque com `scale(0.97)` em 120ms `--ease-out` em todos os botões; troca entre estados só por `opacity` em 200ms (`@starting-style`); troca de câmera apaga em 120ms, o espelho muda com o vídeo invisível e a nova câmera entra em 200ms; prévia entra em 160ms e sai em 200ms; `rotate` com o `--scrim` em 200ms e o giro do ícone de 600ms `--ease-in-out` depois de 300ms, uma vez; pulso do anel em `requesting`; formato sem animação; nenhum `transition: all`, nenhum `ease-in`, nenhum hover; movimento reduzido para o giro e o pulso e mantém as trocas de opacidade. Só no aparelho: o `:active` no iOS e a sensação do toque.

## 4. Divergências

1. Formato da captura em uma linha sobre `--scrim`, no canto superior esquerdo, sempre. O design previa três linhas dentro da faixa preta em telas 20:9; a largura dessa faixa (cerca de 75px menos a margem e a área segura) não comporta o texto com folga, e a frase vem inteira de `cam.capture_format`.
2. A marca `WCam` é o `h1` dos estados antes da câmera, e os títulos dos estados são `h2` ou `<p>`; no design os títulos eram o cabeçalho principal. Mudou por causa do `inspect` (§3.1).
3. O Wake Lock fica pedido também em `preview_off`: com a tela apagando, a página iria para segundo plano e a câmera pararia.
4. Tokens além da lista do design: `--radius-box`, `--illustration-size`, `--duration-cover`, `--duration-explain`, `--delay-explain`, `--duration-pulse`, `--scale-press` e `--opacity-dimmed`, para não deixar número solto no SCSS.
5. `SecurityError` e `NotSupportedError` levam a `unavailable` com motivo `unsupported`; erro desconhecido leva a `in_use`, que oferece "Tentar de novo".
6. O título do console provisório passou de 32 para 24px porque `--text-title` mudou para a escala da `/cam`.

## 5. Dependências novas

Nenhuma.

## 6. Perguntas para o orquestrador

1. Teste no celular real (CA 2, 3, 4, 5, 6 e 7): abrir `https://<ip-do-pc>:8443/cam#t=teste`. Pontos a observar além dos CA: se `getSettings()` no iPhone devolve largura e altura na orientação do quadro (o formato mostrado vem de lá); se o `:active` dá resposta ao toque no iOS; como fica o disco do trilho encostado na borda da imagem.
2. O anel de foco sobre imagem clara (P3 aberto) entra na spec de front ou numa correção desta versão?

## 7. CI

Push de 6eb2edc em `feature/captura-web`: `ci` verde em `agent` (Windows e Linux), `web` e `e2e` (run 41333262471); `codeql` verde (run 41333262465).
