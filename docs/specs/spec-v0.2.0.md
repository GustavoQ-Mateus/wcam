# Spec v0.2.0, Captura no celular

Status: Entregue (2026-11-01)
Branch de integração: `feature/captura`
Sessões: `web` (implementa). A sessão `agent` não tem trabalho nesta versão.
Referências: `docs/planejamento.md` §1 (CA-2, CA-3), §5.1, §5.3 e §5.6; ADR 0007

## Objetivo

A página `/cam` passa a ser o visor da câmera: pede permissão, mostra a imagem da câmera do próprio celular em tela cheia, garante paisagem a 1920x1080 e mantém a tela acesa. Ainda não envia vídeo ao PC; isso é a v0.3.0.

É também a primeira versão com direção visual definitiva, só para a superfície do celular. O console continua provisório até a v0.5.0.

## Como a `/cam` é aberta nesta versão

O pareamento por token é da v0.3.0. Nesta versão:
- `/cam` sem fragmento `#t=` mostra o estado "sem pareamento".
- `/cam#t=<qualquer valor>` entra no fluxo de captura. O valor não é validado; a página lê o fragmento, guarda o valor só em memória e apaga o fragmento da barra de endereço (`history.replaceState`) antes da primeira renderização.
- Para o teste manual, o usuário abre `https://<ip-do-pc>:8443/cam#t=teste` no celular.

## Fase 1: forma (antes de qualquer código de tela)

A sessão `web` faz a passada de design da `/cam` com as skills do CLAUDE.md:
- `taste-skill` (regras de app screen e anti slop);
- `impeccable` (`/impeccable shape`) para os estados da seção "Estados";
- `mobile-native` para o comportamento de celular;
- `emil-design-eng` para os detalhes de toque, transição e estado.

Entrega da fase 1: `docs/design-v0.2.0-cam.md` na branch da sessão, com, para cada estado, o layout em paisagem e em retrato (esboço em texto ou ASCII), a hierarquia, os controles e seus tamanhos, a tipografia escolhida (uma família, com justificativa e arquivo de fonte se não for do sistema), os tokens de espaço e de tipo, o movimento previsto e a skill que guiou cada decisão. Inclui também a revisão dos textos da seção "Textos".

O orquestrador revisa, o usuário aprova, e só então começa a fase 2.

## Fase 2: implementação

### Estados da `/cam`

| Estado | Quando | O que a tela mostra |
|---|---|---|
| `missing_pairing` | sem `#t=` | como parear pelo PC, e nada mais |
| `intro` | com `#t=`, antes de pedir a câmera | por que a câmera será pedida e o botão de ativar |
| `requesting` | aguardando a resposta do navegador | estado de espera, sem botão |
| `denied` | permissão negada | como liberar a câmera no navegador e tentar de novo |
| `unavailable` | sem `getUserMedia`, sem câmera, contexto inseguro ou câmera em uso por outro app | o motivo específico e o que fazer |
| `rotate` | câmera ativa, mas o quadro está em retrato | pedido para girar o celular; o visor continua visível atrás, esmaecido |
| `ready` | câmera ativa em paisagem | visor em tela cheia, controles, formato real da captura |
| `preview_off` | usuário desligou a prévia | tela preta com controles esmaecidos e a indicação de que a câmera continua ligada |

O estado é uma máquina pura (`data/cam-state.ts`), testada com Vitest. O componente só reage a ela.

### Captura

- Restrições: `facingMode` `user` por padrão, `width` ideal 1920, `height` ideal 1080, `frameRate` ideal 30, sem áudio.
- O formato real vem de `track.getSettings()` e aparece no estado `ready` (exemplo: `1920 × 1080 · 30 fps`).
- Paisagem é decidida pelo quadro real (`width > height`), não só pela orientação da tela.
- Trocar de câmera para as faixas atuais antes de abrir a nova (o iOS não mantém duas abertas).
- Câmera frontal espelhada no visor, como selfie. A traseira não.
- Se a faixa terminar (outro app tomou a câmera, a página foi para segundo plano), ao voltar a página tenta reabrir a mesma câmera; falhando, vai para `unavailable`.
- Toda chamada de API de navegador fica em `media/` (`use-camera-stream.ts`, `use-wake-lock.ts`, `use-orientation.ts`), nunca no componente.

### Tela acesa

- Wake Lock pedido ao entrar em `ready` e de novo quando a página volta a ficar visível.
- Sem suporte a Wake Lock, o estado `ready` mostra uma vez um aviso curto para manter a tela ligada nas configurações.

### Prévia desligada

- Um toque no controle de prévia cobre o visor de preto. A faixa de vídeo continua ativa. Um toque em qualquer ponto volta.

### Comportamento de celular (`mobile-native`)

- `100dvh`, áreas seguras (`env(safe-area-inset-*)`), sem zoom por toque duplo, sem destaque de toque, sem seleção de texto nos controles, sem pull-to-refresh no visor.
- Alvos de toque de pelo menos 44px, controles alcançáveis pelo polegar em paisagem.
- `prefers-reduced-motion` respeitado.

### Textos

Chaves novas em `locales/` (o orquestrador adiciona na integração depois da fase 1; a fase 1 pode propor outro texto para cada uma):

| Chave | en | pt-BR |
|---|---|---|
| `cam.missing_pairing` | Open WCam on your computer and scan the QR code with this phone camera. | Abra o WCam no computador e leia o QR code com a câmera deste celular. |
| `cam.intro_title` | Use this phone as your webcam | Use este celular como webcam |
| `cam.intro_body` | WCam needs the camera. Video only goes to your computer on this network and is never recorded. | O WCam precisa da câmera. O vídeo vai só para o seu computador nesta rede e nunca é gravado. |
| `cam.intro_action` | Turn on camera | Ativar câmera |
| `cam.requesting` | Waiting for camera permission | Aguardando permissão da câmera |
| `cam.denied_title` | Camera blocked | Câmera bloqueada |
| `cam.denied_body` | Allow the camera for this site in the browser settings, then try again. | Libere a câmera para este site nas configurações do navegador e tente de novo. |
| `cam.retry` | Try again | Tentar de novo |
| `cam.unavailable_unsupported` | This browser cannot use the camera here. Open the link in Chrome or Safari. | Este navegador não consegue usar a câmera aqui. Abra o link no Chrome ou no Safari. |
| `cam.unavailable_no_camera` | No camera found on this device. | Nenhuma câmera encontrada neste aparelho. |
| `cam.unavailable_in_use` | Another app is using the camera. Close it and try again. | Outro app está usando a câmera. Feche-o e tente de novo. |
| `cam.rotate_title` | Turn your phone sideways | Gire o celular |
| `cam.rotate_body` | WCam sends landscape video, so nothing is cropped or scaled. | O WCam envia vídeo deitado, para nada ser cortado nem reduzido. |
| `cam.capture_format` | {width} × {height} · {fps} fps | {width} × {height} · {fps} fps |
| `cam.switch_camera` | Switch camera | Trocar câmera |
| `cam.preview_off` | Turn off preview | Desligar prévia |
| `cam.preview_hidden` | Preview off. The camera is still on. Tap to show it. | Prévia desligada. A câmera continua ligada. Toque para mostrar. |
| `cam.keep_screen_on` | Keep the screen on in your phone settings while using WCam. | Mantenha a tela ligada nas configurações do celular enquanto usa o WCam. |

A chave `cam.pair_instruction` da v0.1.0 é substituída por `cam.missing_pairing`.

### Testes

Vitest:
- `cam state goes from intro to requesting to ready when permission is granted`
- `cam state goes to denied when permission is refused`
- `cam state goes to rotate when the frame is portrait`
- `cam state returns to ready when the frame turns landscape`
- `cam state maps each getUserMedia error to its unavailable reason`
- `pairing fragment is read and removed from the address`
- `capture constraints ask for 1920x1080 at 30 fps without audio`
- `front camera is mirrored and rear camera is not`

Playwright (Chromium com `--use-fake-device-for-media-stream` e `--use-fake-ui-for-media-stream`, viewport de celular):
- `/cam` sem fragmento mostra `missing_pairing`;
- `/cam#t=teste` em paisagem chega a `ready`, mostra o formato da captura e a barra de endereço fica sem o fragmento;
- em retrato mostra `rotate`;
- permissão negada (por `getUserMedia` rejeitando com `NotAllowedError` via script de inicialização) mostra `denied`;
- desligar a prévia mostra `preview_off` e a faixa continua com `readyState` `live`.

## Fora do escopo

Envio de vídeo, pareamento real, código de confirmação, pausa, console, bandeja.

## Critérios de aceitação

1. Fase 1 aprovada pelo usuário antes do código de tela, com `docs/design-v0.2.0-cam.md` registrando a skill de cada decisão.
2. Num Android com Chrome, em paisagem, a câmera traseira e a frontal ficam configuradas em 1920x1080 a 30 fps, mostrado no estado `ready`. Repetir num iPhone com Safari se houver um disponível; senão, registrar como não testado.
3. Em retrato, a página mostra `rotate` e não mostra `ready`.
4. A troca de câmera funciona nos dois sentidos sem recarregar a página.
5. Com a prévia desligada, a tela fica preta e a câmera continua ativa (indicador de câmera do sistema aceso).
6. A tela não apaga sozinha em 2 minutos parado no estado `ready` (Wake Lock), no aparelho testado.
7. Negar a permissão leva a `denied`, e "Tentar de novo" volta a pedir depois que o usuário libera.
8. O fragmento `#t=` some da barra de endereço logo ao abrir.
9. Nenhum texto de interface no código; as chaves novas existem nos dois idiomas.
10. A `/cam` continua sem carregar o chunk do console.
11. Verificação completa do web sem erros nem avisos, e2e verde no compose, CI verde.
12. `impeccable audit` da `/cam` sem pendência crítica, registrado no relatório.

## Decisões registradas na aprovação

1. Aparelhos de teste do CA 2: escolhidos pelo usuário no momento do teste e registrados no changelog.
2. Fase 1 aprovada pelo usuário em 2026-11-01: `docs/design-v0.2.0-cam.md` (skills taste-skill, impeccable shape, mobile-native e emil-design-eng). A fase 2 também usa taste-skill (`lint.mjs` e `inspect.mjs --app`), impeccable (`audit` e `polish`) e emil-design-eng, com o resultado de cada uma no relatório.
3. Textos: os quatro ajustes da §8 do design entraram em `locales/` (`cam.requesting`, `cam.rotate_title`, `cam.rotate_body`, `cam.preview_hidden`), e `cam.pair_instruction` saiu.
4. A API de tela cheia fica fora desta versão (o Safari do iPhone não a oferece para páginas).
5. O fps mostrado é o configurado na faixa (`getSettings().frameRate`), arredondado para inteiro. O fps entregue de fato é medido pelo agente a partir da v0.3.0. Nesta versão, o CA 2 confere a configuração: 1920x1080 a 30 fps.

## Changelog

### 0.2.0, 2026-11-01

Entregue pela sessão `web` (`feature/captura-web`), integrada em `feature/captura`. Design em `docs/design-v0.2.0-cam.md`, relatório em `docs/relatorio-v0.2.0-web.md`. A sessão `agent` só subiu a versão.

| CA | Resultado | Evidência |
|---|---|---|
| 1 | Verificado | Fase 1 aprovada pelo usuário antes do código; o design registra a skill de cada decisão. |
| 2 | Verificado | Usuário validou no celular real: 1920 × 1080 · 30 fps configurado, nas câmeras frontal e traseira. Aparelho e navegador não registrados. |
| 3 | Verificado | e2e `cam with a portrait frame shows rotate` e celular real. |
| 4 | Verificado | Celular real: troca nos dois sentidos sem recarregar. |
| 5 | Verificado | e2e (faixa `live` com a prévia desligada) e celular real. |
| 6 | Verificado | Celular real: tela acesa por 2 minutos parada no `ready`. |
| 7 | Verificado | e2e `denied` e celular real: "Tentar de novo" volta a pedir depois de liberar. |
| 8 | Verificado | Teste Vitest e e2e: a barra de endereço fica sem o fragmento. |
| 9 | Verificado | Textos só em `locales/`; teste de paridade de chaves. |
| 10 | Verificado | e2e `cam page does not load the console chunk`. |
| 11 | Verificado | Build sem avisos, lint, 18 testes Vitest; compose e2e 7 de 7; CI e CodeQL verdes. |
| 12 | Verificado | `impeccable audit` de 16/20 para 18/20, sem P0. |

Skills na fase 2: taste-skill (`lint.mjs` 0/0; `inspect.mjs --app` com 2 FAIL de título corrigidos e 0 FAIL no fim), impeccable (`detect` sem achados, `audit` e `polish`), emil-design-eng (vídeo só no primeiro quadro).

Divergências aceitas: formato da captura em uma linha sobre `--scrim`; a marca é o `h1` e os títulos dos estados são `h2` ou `<p>`; Wake Lock também em `preview_off`; tokens extras para não deixar número solto; título do console provisório de 32 para 24px; textos de `cam.missing_pairing`, `cam.unavailable_unsupported` e `cam.unavailable_in_use` encurtados para caber em duas linhas.

Pendências para a spec de polimento do front: anel de foco sobre imagem clara, disco do trilho encostado na borda da imagem em telas 20:9, anúncio do `rotate` por leitor de tela.
