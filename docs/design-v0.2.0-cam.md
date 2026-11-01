# Design v0.2.0, `/cam`

Spec: `docs/specs/spec-v0.2.0.md`, fase 1
Referências: `docs/planejamento.md` §5.1, §5.3 e §5.6; CLAUDE.md (Front)
Status: proposta, aguardando aprovação do usuário

Legenda das skills: **[taste]** `taste-skill` (`references/app-screens.md`), **[shape]** `impeccable shape`, **[mobile]** `mobile-native`, **[emil]** `emil-design-eng`, **[usuário]** escolha do usuário na rodada de perguntas do `shape`, **[spec]** já decidido na spec ou no planejamento.

## 1. Brief

- **Quem e onde.** Uma pessoa que acabou de ler o QR do PC com o celular, em pé ou sentada perto do computador, com o celular numa mão. Depois de pronto, o celular fica parado num suporte por uma reunião inteira: a tela é olhada de relance, não usada. **[shape]**
- **Modo.** Operate (`impeccable`): a pessoa completa uma tarefa (ligar a câmera e deixá-la enquadrada). Ambição aqui é precisão e silêncio, não expressão. **[shape]**
- **A pergunta da tela.** "A câmera está ligada e enquadrada do jeito que o PC vai receber?" A resposta é o maior elemento: o próprio visor. **[taste]** §2.2
- **A ação mais frequente.** Antes da câmera: ativar a câmera (um botão, sempre no mesmo lugar). Com a câmera: nenhuma; a tela fica quieta. Trocar câmera e desligar a prévia ficam a um toque. **[taste]** §2.2
- **O que só este produto tem (a face).** O quadro do visor é a verdade da captura: a imagem aparece inteira, sem corte, na proporção real de 16:9, e as faixas pretas que sobram na tela larga do celular viram o lugar dos controles e da leitura do formato. O formato real (`1920 × 1080 · 30 fps`) é o único dado na tela, e prova o CA-2 sem precisar de outra explicação. **[taste]** §2.3 ("Its face"), estilo `true-black-flat`
- **Fora desta versão.** Tally "ao vivo", cadeia de sinal, pausa, código de confirmação: entram na v0.3.0 em diante. Nada no layout depende delas, mas o trilho de controles já reserva o lugar da tally no topo. **[spec]**
- **Contexto do `impeccable`.** O projeto não tem `PRODUCT.md` e este escopo não permite criar um; o contexto veio da spec, do planejamento e do CLAUDE.md. O `detect` e o `audit` do `impeccable` rodam na fase 2, sobre o código. **[shape]**

## 2. Estilo e regras herdadas

| Decisão | Skill |
|---|---|
| Estilo `true-black-flat` com a paleta de §5.6: fundo `--ground`, elevação só por luminosidade, sem borda nem sombra em superfície. Folha do estilo tirada com `draw.mjs --app --style true-black-flat --keep palette,type` (seed 765827752). | [spec] [taste] |
| Shell: nenhum. Sem barra, sem navegação; a `/cam` é uma tela só. O nome do produto aparece como marca pequena nos estados antes da câmera e some no visor. | [taste] §3, §12 |
| Cor só em dado e estado: `--negative` só nos estados de falha (marca e título), `--data` reservado para a tally da v0.3.0 e ausente nesta versão. Nenhum pixel colorido no estado `ready`. | [spec] [taste] §9.3 |
| Botão primário por inversão: pílula branca (`--ink`) com texto preto. Um por tela. | [taste] (move do estilo), §4.3 |
| Única transparência: `--scrim`, atrás de texto e controles sobre a imagem e no visor esmaecido do `rotate`. | [spec] |
| Cor nunca é o único sinal: cada estado tem texto e uma forma (ver §5). | [spec] |

## 3. Tipografia

**Uma família: a do sistema** (`system-ui`, que resolve para SF Pro no iPhone e Roboto no Android). **[usuário] [taste]**

Justificativa:
- A `/cam` abre por HTTPS autoassinado numa rede local; uma fonte própria seria mais um arquivo no primeiro carregamento e uma troca de fonte visível na tela que já é a mais simples do produto.
- Num visor de câmera, a fonte do sistema é a do app de câmera nativo: a página parece parte do celular, não um site. **[mobile]**
- SF Pro e Roboto têm algarismos tabulares de verdade (`font-variant-numeric: tabular-nums` muda a largura dos dígitos), exigência do `taste` para número que muda (o fps). **[taste]** §9.1
- O console pode ganhar outra face na v0.5.0 sem conflito: as superfícies não se misturam (CA-3).

Escala: três tamanhos e dois pesos. **[taste]** §9.1 (app type não é display type; título de 20 a 24px no celular, §12)

| Token | Valor | Uso |
|---|---|---|
| `--font-system` | `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | tudo (já existe) |
| `--text-meta` | `0.8125rem` (13px) | formato da captura, marca, aviso de tela acesa |
| `--text-body` | `1rem` (16px) | corpo dos estados, rótulo do botão (já existe) |
| `--text-title` | `1.5rem` (24px) | título de cada estado e a instrução de `missing_pairing` (substitui os 32px provisórios) |
| `--line-body` | `1.5` | corpo (já existe) |
| `--line-tight` | `1.2` | título (já existe) |
| `--weight-strong` | `600` | título, marca, rótulo do botão (já existe) |
| `--tracking-title` | `-0.01em` | só no título |

`--text-small` e `--text-lead` da v0.1.0 deixam de ser usados e saem do arquivo.

Títulos com `text-wrap: balance`, no máximo duas linhas a 320px de largura (o mais longo, "Use este celular como webcam", fica em duas). Corpo em `--muted` (10,1:1 sobre `--ground`), título em `--ink`. **[taste]** §9.3

## 4. Espaço, tamanhos e movimento (tokens novos)

| Token | Valor | Uso | Skill |
|---|---|---|---|
| `--space-5` | `1.25rem` (20px) | margem lateral do celular | [taste] §12 (16 a 20px) |
| `--margin` | `max(var(--space-5), env(safe-area-inset-*))` por lado | moldura de todos os estados | [mobile] §7 |
| `--hit-min` | `44px` | menor alvo de toque | [spec] [mobile] |
| `--control-size` | `56px` | botão redondo do visor | [emil] (alvo folgado sobre imagem em movimento) |
| `--button-height` | `52px` | botão primário | [mobile] [taste] §12 |
| `--radius-pill` | `999px` | botão primário e botão do visor | [taste] §9.4 (raio bimodal: pílula) |
| `--icon-size` | `24px` | ícone dos controles | [taste] §9.4 |
| `--icon-stroke` | `2px` | traço dos ícones | [taste] §9.4 |
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | entradas e resposta | [emil] |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | o giro do ícone do `rotate` | [emil] |
| `--duration-press` | `120ms` | toque | [emil] |
| `--duration-state` | `200ms` | troca de estado, prévia, câmera | [emil] |

A escala `--space-1` a `--space-12` da v0.1.0 continua.

## 5. Estados

Dois grupos com composições diferentes:

- **Antes da câmera** (`missing_pairing`, `intro`, `requesting`, `denied`, `unavailable`): o celular ainda está na mão, quase sempre em retrato, porque a pessoa acabou de ler o QR. Uma composição só: marca pequena no topo, bloco de texto e ação ancorados embaixo, na zona do polegar. A mesma composição serve em paisagem. **[shape] [mobile]**
- **Com a câmera** (`rotate`, `ready`, `preview_off`): o visor ocupa a tela e os controles moram nas bordas. **[spec] [taste]**

O botão de ação ocupa sempre o mesmo lugar nos estados de antes da câmera, e o texto acima dele cresce para cima: nada pula quando o estado muda. **[emil]**

### 5.1 Marca de estado

Mesmo vocabulário do console da v0.1.0, para o estado não depender só da cor: **[spec] [shape]**

| Estado | Marca ao lado do título |
|---|---|
| `requesting` | anel vazio em `--muted` |
| `denied`, `unavailable` | quadrado cheio em `--negative`, título em `--negative` |
| demais | nenhuma |

### 5.2 `missing_pairing`

Retrato (390 × 844):
```
+------------------------------+
| WCam                         |  marca, 13/600, --muted
|                              |
|                              |
|                              |
|                              |
|                              |
| Abra o WCam no computador    |  24/600, --ink, até 3 linhas
| e leia o QR code com a       |
| câmera deste celular.        |
|                              |  margem inferior + área segura
+------------------------------+
```
Paisagem (844 × 390):
```
+----------------------------------------------------+
| WCam                                               |
|                                                    |
|                                                    |
| Abra o WCam no computador e leia o QR code         |
| com a câmera deste celular.                        |
+----------------------------------------------------+
```
- Hierarquia: a instrução é a única coisa; não há botão porque não há o que fazer aqui. **[spec] [shape]**
- Largura do texto limitada a ~32 caracteres por linha em retrato e a 28rem em paisagem. **[taste]**

### 5.3 `intro`

Retrato:
```
+------------------------------+
| WCam                         |
|                              |
|                              |
|                              |
| Use este celular como        |  título 24/600
| webcam                       |
|                              |  16px
| O WCam precisa da câmera.    |  corpo 16/400, --muted
| O vídeo vai só para o seu    |
| computador nesta rede e      |
| nunca é gravado.             |
|                              |  24px
| (       Ativar câmera      ) |  pílula branca, 52px, largura do bloco
+------------------------------+
```
Paisagem:
```
+----------------------------------------------------+
| WCam                                               |
|                                                    |
| Use este celular como webcam                       |
| O WCam precisa da câmera. O vídeo vai só para o    |
| seu computador nesta rede e nunca é gravado.       |
| ( Ativar câmera )                                  |  largura do rótulo + 24px de cada lado
+----------------------------------------------------+
```
- O botão em retrato tem a largura do bloco de texto (polegar não precisa mirar); em paisagem, a largura do rótulo, alinhado à esquerda com o texto. **[mobile] [taste]** §12
- Em 360 × 640 (Android pequeno) o bloco inteiro cabe na metade de baixo. Em paisagem com 360px de altura, o bloco tem ~250px: cabe. **[shape]** (faixas reais de tela)

### 5.4 `requesting`

Mesma composição do `intro`. O título vira o texto de `cam.requesting` com o anel vazio; o corpo fica; o lugar do botão fica vazio com a mesma altura, para nada se mexer quando o diálogo do navegador fechar. Sem botão, sem spinner: o anel pulsa em opacidade (1,0 a 0,4 em 1,2s, contínuo), e para com movimento reduzido. **[spec] [emil] [shape]**

Detalhe: em muitos aparelhos o diálogo do navegador cobre a metade de baixo da tela; o título fica acima do bloco do corpo, então continua visível na maior parte dos casos. **[shape]**

### 5.5 `denied`

```
+------------------------------+
| WCam                         |
|                              |
|                              |
| ■ Câmera bloqueada           |  quadrado + título em --negative
|                              |
| Libere a câmera para este    |  corpo, --muted
| site nas configurações do    |
| navegador e tente de novo.   |
|                              |
| (      Tentar de novo      ) |  primário
+------------------------------+
```
- "Tentar de novo" chama o pedido de novo; se o navegador lembrar a recusa, o estado volta a `denied` sem passar por `requesting` visível por mais que um quadro. **[spec]**
- Paisagem: mesma regra do `intro`. **[mobile]**

### 5.6 `unavailable`

Mesma composição do `denied`, sem título próprio: o texto do motivo é o título (24/600, `--negative`, com o quadrado), e não há corpo.

| Motivo | Texto | Ação |
|---|---|---|
| `unsupported` (sem `getUserMedia` ou contexto inseguro) | `cam.unavailable_unsupported` | nenhuma |
| `no_camera` | `cam.unavailable_no_camera` | nenhuma |
| `in_use` (também a câmera perdida que não reabriu) | `cam.unavailable_in_use` | "Tentar de novo" (`cam.retry`) |

Sem botão onde tentar de novo não muda nada. **[taste]** §11 (erro honesto, com a próxima ação só quando ela existe) **[shape]**

### 5.7 `rotate`

Retrato (o quadro da câmera está em retrato):
```
+------------------------------+
| ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ |  visor ao vivo atrás, coberto por --scrim
| ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ |
| ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ |
| ░░░░░░░ [▯ → ▭] ░░░░░░░░░░░░ |  ícone do celular, 48px, gira 90° uma vez
| ░░░░░░░░░░░░░░░░░░░░░░░░░░░░ |
| Vire o celular na horizontal |  título 24/600, --ink
| O WCam envia vídeo na        |  corpo 16, --muted
| horizontal, sem cortar nem   |
| reduzir a imagem.            |
+------------------------------+
```
- O visor continua ao vivo atrás, para a pessoa ver que a câmera já funciona; o `--scrim` garante o contraste do texto. **[spec]**
- O ícone é um retângulo de celular desenhado em SVG (contorno, `--icon-stroke`), que gira de retrato para paisagem uma vez ao entrar no estado. Propósito: explicar o gesto. **[emil]** (animação de explicação, rara)
- Sem controles neste estado: trocar câmera em retrato não ajuda a sair dele. **[shape]**
- Se o celular estiver deitado mas o quadro vier em retrato (raro, alguns Android), a mesma tela aparece em paisagem, com o texto à esquerda e o ícone acima dele. A regra é o quadro, como a spec pede. **[spec]**

### 5.8 `ready`

Paisagem num celular 20:9 (844 × 390). A imagem 16:9 inteira ocupa a altura toda, 693px de largura, e sobram ~75px de cada lado:
```
+--------+------------------------------------+--------+
|1920 ×  |                                    |        |
|1080    |                                    |  ( ◐ ) |  desligar prévia
|30 fps  |                                    |        |
|        |        imagem da câmera, 16:9      |        |
|        |        inteira, sem corte           |  ( ⟲ ) |  trocar câmera
|        |                                    |        |
|        |                                    |        |
+--------+------------------------------------+--------+
  faixa       quadro real da captura            trilho
 esquerda                                      direito
```
- **O quadro é a verdade.** O vídeo usa `object-fit: contain`: o celular mostra exatamente o que o PC vai receber, sem corte. Num 16:9 ou mais estreito, os controles ficam sobre a imagem, cada um no seu disco de `--scrim`. **[taste]** (face) **[spec]** (CA-2)
- **Trilho à direita.** Dois botões redondos de 56px, centrados na altura da tela, 16px entre eles, a `--margin` da borda direita mais a área segura. Desligar prévia em cima, trocar câmera embaixo (a mais usada fica mais perto do polegar, que repousa abaixo do meio). O topo do trilho fica livre para a tally da v0.3.0. **[usuário] [mobile] [taste]** §12
- **Botões.** Ícone em SVG de contorno, 24px, `--ink`, sobre disco `--scrim`; nome em `aria-label` vindo de `locales/` (`cam.preview_off`, `cam.switch_camera`). Sem texto visível no visor. **[usuário] [taste]** §9.4
- **Formato da captura** no canto superior esquerdo, em três linhas curtas (`1920 ×` / `1080` / `30 fps`) quando cabe só na faixa, ou uma linha (`1920 × 1080 · 30 fps`) sobre `--scrim` quando cai sobre a imagem. 13/400, `--muted`, algarismos tabulares, fps arredondado para inteiro. É o único dado da tela e não pisca quando o fps oscila (só atualiza se mudar o inteiro). **[taste]** §5, §9.1 **[emil]**
- **Espelho.** Câmera frontal espelhada no visor, traseira não. **[spec]**
- **Aviso de tela acesa** (só sem Wake Lock, uma vez): uma linha `--text-meta` em `--scrim`, no rodapé do quadro, à esquerda. O aviso inteiro é um botão: tocar nele o fecha. Não some sozinho, para não sumir antes de ser lido. Sem chave nova. **[taste]** §11 **[shape]**
- **Toques no vídeo** não fazem nada em `ready` (sem foco por toque nesta versão); só os botões respondem. **[shape]** (YAGNI)

Não existe `ready` em retrato: o quadro em retrato é o `rotate`. **[spec]**

### 5.9 `preview_off`

```
+--------+------------------------------------+--------+
|1920 ×  |                                    |        |
|1080    |                                    |  ( ◐ ) |  controles a 40% de opacidade
|30 fps  |                                    |        |
|        |                                    |        |
|        |                                    |  ( ⟲ ) |
|        |  Prévia desligada. A câmera        |        |
|        |  continua ligada. Toque para       |        |
|        |  mostrar.                          |        |
+--------+------------------------------------+--------+
              tudo em --ground (preto puro)
```
- Preto puro (`--ground`) sobre o visor: em OLED, quase todos os pixels apagados. **[spec]** §5.3
- O formato da captura continua visível e atualizado, em `--faint`: é a prova de que a câmera segue ligada, além do texto. **[taste]** (dado honesto) **[shape]**
- O texto `cam.preview_hidden` em `--faint` (6,9:1), no pé do quadro. **[spec]**
- A tela inteira é um botão só, com o texto como nome acessível; qualquer toque volta ao `ready`. Os controles aparecem esmaecidos a 40% e não reagem neste estado, para o primeiro toque nunca trocar a câmera por engano. **[spec] [emil]**

## 6. Movimento

Regra do `taste` para telas de uso: movimento é resposta, nada encena entrada. Só `transform` e `opacity`, só transições (interrompíveis), nada passa de 300ms exceto o giro explicativo. **[taste]** §2.8 **[emil]**

| Momento | Movimento | Por quê | Skill |
|---|---|---|---|
| Tocar qualquer botão | `scale(0.97)` em `:active`, `--duration-press`, `--ease-out` | resposta no toque, não na soltura | [emil] [mobile] §5 |
| Troca entre estados de antes da câmera | o conteúdo que muda faz `opacity` 0 a 1 em `--duration-state`; nada se desloca | evitar troca seca sem distrair | [emil] |
| A câmera abre (`requesting` para `ready` ou `rotate`) | o vídeo entra de preto para a imagem em `--duration-state` depois do primeiro quadro (`loadeddata`), nunca antes | sem flash de vídeo vazio | [emil] |
| Trocar câmera | o vídeo vai a preto em 120ms; o espelho muda com a tela preta; a nova câmera entra em `--duration-state` no primeiro quadro | o espelhamento nunca aparece como um "pulo" | [emil] |
| Desligar e ligar a prévia | a cobertura preta entra em 160ms e sai em `--duration-state` | a saída é o que a pessoa quer ver logo | [emil] (assimetria) |
| `rotate` | o `--scrim` entra em `--duration-state`; o ícone gira 90° uma vez, 600ms, `--ease-in-out`, 300ms depois de entrar | explicar o gesto, uma vez só | [emil] |
| `requesting` | o anel pulsa em opacidade | mostrar que a página espera | [emil] |
| Formato da captura | sem animação; o número troca seco | dado não se anima | [taste] §2.8 |

**Movimento reduzido** (`prefers-reduced-motion: reduce`): o giro do ícone e o pulso do anel param (o ícone já aparece em paisagem); as trocas de opacidade ficam, porque ajudam a entender a mudança. **[spec] [emil]**

## 7. Comportamento de celular

| Regra | Como | Skill |
|---|---|---|
| Altura certa | `100dvh` na raiz da `/cam` | [mobile] §3 |
| Áreas seguras | `viewport-fit=cover` (já no `index.html`) e `env(safe-area-inset-*)` em `--margin`, nos quatro lados, porque em paisagem o recorte da câmera fica à esquerda ou à direita | [mobile] §7 |
| Sem zoom por toque duplo | `touch-action: manipulation` na `/cam`; o zoom de pinça continua permitido (nunca `user-scalable=no`) | [mobile] §5, regra 4 |
| Sem destaque de toque | `-webkit-tap-highlight-color: transparent` (já no `base.scss`) | [mobile] §2 |
| Sem seleção nos controles | `user-select: none` e `-webkit-touch-callout: none` só nos botões; o texto dos estados continua selecionável | [mobile] §8 |
| Sem pull-to-refresh | `overscroll-behavior: none` em `html` e `body` | [mobile] §6 |
| Hover | nenhum estilo de hover na `/cam`; se aparecer algum, só dentro de `(hover: hover) and (pointer: fine)` | [mobile] §1 |
| Barra de status | `theme-color` preto (já existe; a `/cam` é só escura) | [mobile] §10 |
| Alvos | 44px no mínimo; os do visor com 56px | [spec] [mobile] |
| Verificação | no celular real (CA 2 a 7), pelo usuário; emulação não reproduz áreas seguras, barra do navegador nem Wake Lock | [mobile] §11 |

## 8. Revisão dos textos

Proponho mudar quatro textos; o resto fica como está na spec. Nenhuma chave nova: a marca usa `app.name`, o "Tentar de novo" do `in_use` usa `cam.retry`, e o aviso de tela acesa fecha com um toque nele mesmo.

| Chave | Hoje | Proposta en | Proposta pt-BR | Motivo |
|---|---|---|---|---|
| `cam.requesting` | Waiting for camera permission / Aguardando permissão da câmera | Allow camera access in the browser prompt | Permita o acesso à câmera no aviso do navegador | diz o que fazer, não só o que a página faz [shape] |
| `cam.rotate_title` | Turn your phone sideways / Gire o celular | Turn your phone sideways (mantém) | Vire o celular na horizontal | "Gire" não diz para que lado [shape] |
| `cam.rotate_body` | ... / O WCam envia vídeo deitado, para nada ser cortado nem reduzido. | WCam sends landscape video, so nothing is cropped or scaled. (mantém) | O WCam envia vídeo na horizontal, sem cortar nem reduzir a imagem. | "deitado" é informal e ambíguo [shape] |
| `cam.preview_hidden` | ... Tap to show it. / ... Toque para mostrar. | Preview off. The camera is still on. Tap anywhere to show it. | Prévia desligada. A câmera continua ligada. Toque em qualquer ponto para mostrar. | a tela inteira é o botão; o texto deve dizer isso [emil] |

`cam.capture_format` mostra o fps arredondado para inteiro (`29,97` vira `30`). Se o orquestrador preferir uma casa decimal para provar o CA 2 ("pelo menos 29 fps"), é só mudar a formatação, sem mudar a chave.

## 9. Perguntas para o orquestrador

1. **Tela cheia.** Em paisagem, a barra de endereço do Chrome no Android ocupa ~56px de uma altura de ~390px. A spec não pede a API de tela cheia, e eu não a incluí. Se entrar, seria um botão a mais no trilho (e uma chave nova). Fica para outra versão?
2. **Formato do fps.** Inteiro arredondado (proposta) ou uma casa decimal?
3. **Textos.** As quatro mudanças da §8 entram junto com as chaves novas na integração?
