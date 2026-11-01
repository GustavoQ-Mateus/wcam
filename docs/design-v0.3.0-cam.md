# Design v0.3.0, `/cam`

Spec: `docs/specs/spec-v0.3.0.md`, fase 1
Base: `docs/design-v0.2.0-cam.md` (tokens, tipografia, composições e movimento continuam valendo)
Status: proposta, aguardando aprovação do usuário

Legenda das skills: **[taste]** `taste-skill` (`references/app-screens.md`), **[shape]** `impeccable shape`, **[mobile]** `mobile-native`, **[emil]** `emil-design-eng`, **[usuário]** resposta do usuário na rodada de perguntas do `shape`, **[spec]** decidido na spec, no contrato ou no planejamento.

## 1. Brief

- **O que muda.** A `/cam` deixa de ser só um visor e passa a ser uma ponta da transmissão. Depois de `ready`, a página abre a sessão sozinha, mostra o código para conferir, espera o Confirmar no PC e acende a tally. **[spec]**
- **A pergunta da tela, agora.** Primeiro: "este celular está falando com o meu computador?" (o código igual nas duas telas responde). Depois: "a imagem está saindo?" (a tally responde). **[taste]** §2.2
- **Onde a pessoa está.** Com o celular já no suporte, olhando para o PC; a tela do celular é lida de relance, a um braço de distância. O código precisa ser legível daí. **[shape]**
- **A ação mais frequente.** Nenhuma no celular: o Confirmar é no PC. A `/cam` não tem botão em nenhum estado novo. **[spec] [shape]**
- **Contexto do `impeccable`.** Sem `PRODUCT.md` (fora do escopo desta sessão); contexto da spec, do contrato, do planejamento e do design da v0.2.0. **[shape]**

## 2. Decisões da rodada de perguntas

| Pergunta | Resposta | Consequência |
|---|---|---|
| Sobre o que o código aparece? | Visor esmaecido | o vídeo continua ao fundo sob `--scrim`, como no `rotate`; dá para ajustar o enquadramento enquanto confere |
| Forma da tally | Pílula no canto | pílula no canto superior direito, fora do trilho; o trilho continua só com os dois botões |
| Câmera nos estados finais | Desliga | `ended`, `pairing_failed`, `blocked` e `busy` param a câmera; o indicador de privacidade do sistema apaga |

Todas **[usuário]**.

## 3. Fluxo

```
ready ──(automático)──> connecting ──(DataChannel abre)──> awaiting_confirmation ──(Confirmar no PC)──> live
  │                        │                                     │                                    │
  │                        └── erro do POST ──> pairing_failed | blocked | busy                        │
  │                                                              └────────── session_state ended ──────┴──> ended
  └── sem token na memória: continua missing_pairing (v0.2.0)
```

- `ready` vira passagem: aparece por um instante, só até o `POST /api/sessions` sair. **[spec]**
- **O `rotate` continua mandando.** Se o quadro virar retrato em `connecting`, `awaiting_confirmation` ou `live`, o `rotate` cobre a tela como na v0.2.0; a sessão continua por baixo, e ao voltar a paisagem a tela volta ao estado da sessão. Assim o PC nunca recebe imagem em retrato sem a pessoa saber. **[shape] [spec]** (CA-2)
- **Prévia desligada** continua possível em `live`, e a tally aparece sobre o preto. **[spec]** §5.3 do planejamento
- **Estados finais** param a câmera e liberam o Wake Lock. **[usuário]**

## 4. Estados

### 4.1 `connecting`

Paisagem (844 × 390):
```
+--------+------------------------------------+--------+
|░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|  visor sob --scrim
|░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|
|░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|
|░ ○ Conectando ao computador ░░░░░░░░░░░░░░░░░░░░░░░░░|  anel vazio pulsando + 24/600
+------------------------------------------------------+
```
- Mesma composição do `rotate`: `--scrim` sobre o visor, texto no pé, à esquerda. **[taste]** (uma composição por grupo de estados) **[emil]** (nada pula entre estados)
- Marca: o anel vazio pulsando de `requesting`, porque é a mesma espera. **[shape]** (vocabulário de estado da v0.2.0)
- Sem trilho e sem leitura do formato: só uma coisa na tela. **[taste]** §2.2 **[shape]**

### 4.2 `awaiting_confirmation`

Paisagem:
```
+------------------------------------------------------+
|░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|
|░ Confira o código no computador ░░░░░░░░░░░░░░░░░░░░░|  24/600, --ink
|░                                ░░░░░░░░░░░░░░░░░░░░░|
|░ 92Q  M2H ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░|  --text-code (até 96px), 600, tabular
|░                                ░░░░░░░░░░░░░░░░░░░░░|
|░ Se for igual, clique em Confirmar no computador. ░░░|  16, --muted
+------------------------------------------------------+
```
- **O código é o maior elemento da tela** e o único dado. Tamanho `--text-code: clamp(3.5rem, 24dvh, 6rem)`: 96px num celular de 390px de altura em paisagem, legível a um braço de distância; em telas baixas encolhe sem cortar o texto. **[taste]** §2.2 (o maior elemento responde à pergunta) **[shape]**
- **Os dois grupos de três** com um espaço entre eles (`--space-4`), e o hífen do contrato vira esse espaço na tela. Lido em dois blocos, como o console vai mostrar. O texto do código vem do cálculo, não de `locales/`. Leitor de tela recebe o código com o hífen (`aria-label`). **[emil]** (detalhe invisível) **[taste]** §9.1
- Algarismos e letras da mesma família do sistema, peso 600, `font-variant-numeric: tabular-nums`, tracking `0.04em` para as letras parecidas (`M`, `N`, `H`) não se encostarem. O alfabeto do contrato já tira `0/O`, `1/I/L` e `U`. **[taste]** §9.1 **[spec]**
- Sem trilho, sem formato, sem tally: a tela inteira é para conferir. **[shape]**
- Retrato: não acontece (o `rotate` cobre). **[spec]**

### 4.3 `live`

Paisagem num 20:9:
```
+--------+------------------------------------+---------+
|1920 ×  1080 · 30 fps |                 | ● Ao vivo |  leitura à esquerda, tally à direita
|        |                                    |         |
|        |                                    |  ( ◐ )  |
|        |        imagem da câmera, 16:9      |         |
|        |                                    |  ( ⟲ )  |
|        |                                    |         |
+--------+------------------------------------+---------+
```
- **Tally:** pílula no canto superior direito, alinhada à margem direita, na mesma linha da leitura do formato. Disco de `--indicator-size` cheio em `--data` e o texto `cam.live` em 16/600 `--data`, sobre `--positive-tint` (7,7:1). A pílula é opaca: lê igual sobre qualquer imagem. **[usuário] [spec]** (tally em `--data`, forma e texto) **[taste]** §7.6 (estado como tom sobre o próprio tint)
- **Nunca só cor:** o disco cheio e a palavra "Ao vivo" existem só neste estado; nenhum outro estado mostra pílula. **[spec]**
- Altura da pílula: 32px; não é botão, então não precisa de 44px. **[taste]** §7.6
- Trilho e leitura do formato iguais aos do `ready` da v0.2.0. **[spec]**
- Com a prévia desligada, a pílula continua acesa (sem esmaecer), porque a transmissão continua. **[spec]** §5.3 do planejamento

### 4.4 Estados finais: `pairing_failed`, `blocked`, `busy`, `ended`

Composição de `unavailable` da v0.2.0: marca `WCam` no topo, frase no pé, sem botão. A câmera para, então não há visor. **[usuário] [shape]**

Retrato e paisagem (o celular pode estar em qualquer posição quando a sessão cai):
```
+------------------------------+
| WCam                         |
|                              |
|                              |
| ■ O computador não aceitou   |  frase 24/600
|   este celular.              |
+------------------------------+
```

| Estado | Motivo | Texto | Marca |
|---|---|---|---|
| `pairing_failed` | `pairing_token_invalid`, `pairing_token_expired`, `pairing_window_closed` | `cam.pairing_failed` | quadrado `--negative` |
| `blocked` | `not_same_network` | `cam.blocked_network` | quadrado `--negative` |
| `blocked` | `too_many_attempts` | `cam.blocked_attempts` | quadrado `--negative` |
| `busy` | `session_already_active` | `cam.busy` | quadrado `--negative` |
| `ended` | `rejected` | `cam.ended_rejected` | quadrado `--negative` |
| `ended` | `disconnected_by_pc` | `cam.ended_disconnected` | nenhuma, texto em `--ink`: foi uma escolha, não uma falha |
| `ended` | `connection_failed`, `disconnected_by_phone`, conexão caída sem mensagem | `cam.ended_lost` | quadrado `--negative` |
| `ended` | `confirmation_timeout` | `cam.ended_timeout` | quadrado `--negative` |

- **Sem botão.** Nenhum desses estados se resolve no celular: todos pedem um QR novo no PC, e o texto diz isso. **[taste]** §11 (ação só quando ela existe) **[shape]**
- `invalid_request` (422) e erros desconhecidos do `POST` caem em `ended` com `cam.ended_lost`: para a pessoa, a conexão não aconteceu. **[shape]**
- Frase sempre em até duas linhas a 360px (regra do `inspect` da v0.2.0); ver os textos na §7. **[taste]**

## 5. Tokens novos

| Token | Valor | Uso | Skill |
|---|---|---|---|
| `--text-code` | `clamp(3.5rem, 24dvh, 6rem)` | código de confirmação | [taste] [shape] |
| `--tracking-code` | `0.04em` | código | [taste] §9.1 |
| `--tally-height` | `2rem` | pílula da tally | [taste] §7.6 |

O resto vem da v0.2.0 (`--scrim`, `--indicator-size`, `--positive-tint`, `--data`, margens, tipo, movimento).

## 6. Movimento

Mesmas regras da v0.2.0: só `opacity` e `transform`, só transições, até 200ms. **[emil] [taste]** §2.8

| Momento | Movimento | Por quê | Skill |
|---|---|---|---|
| `ready` para `connecting` | o `--scrim` e o texto entram em `--duration-state` | o visor escurece, o que já diz "espere" | [emil] |
| `connecting` para `awaiting_confirmation` | só o conteúdo troca, por opacidade; o `--scrim` fica | nada pula; o código aparece no lugar do texto | [emil] |
| `awaiting_confirmation` para `live` | o `--scrim` sai em `--duration-state`, a tally, o trilho e a leitura entram juntos por opacidade | o visor "acende" no momento em que vai ao ar: é o único momento da tela que merece ser percebido | [emil] (propósito: indicar mudança de estado) |
| Tally acesa | parada, sem pulso | lâmpada de estúdio é fixa; pulso cansaria numa reunião de uma hora | [emil] (frequência alta, nada se mexe) |
| Estado final | o vídeo apaga em `--duration-press` ao parar a câmera; a frase entra em `--duration-state` | a câmera desligando fica visível | [emil] |
| Código | sem animação de número | dado não se anima | [taste] §2.8 |

Movimento reduzido: o pulso do anel em `connecting` para; as trocas de opacidade ficam. **[emil] [spec]**

## 7. Comportamento de celular

- Wake Lock pedido em `connecting`, `awaiting_confirmation` e `live`, e solto nos estados finais. **[mobile] [spec]**
- Nenhum alvo novo: os estados novos não têm botão. A pílula da tally não é tocável. **[mobile]**
- Áreas seguras nas duas pontas de cima (leitura e tally usam `--margin-top`, `--margin-left` e `--margin-right`). **[mobile]** §7
- O resto continua como na v0.2.0. **[mobile]**

## 8. Revisão dos textos

Regra: frase principal em até duas linhas a 24px num celular de 360px (cerca de 27 caracteres por linha com a marca ao lado, então até uns 52 caracteres). **[taste]**

| Chave | Hoje (pt-BR / en) | Proposta pt-BR | Proposta en | Motivo |
|---|---|---|---|---|
| `cam.confirm_body` | Tem de ser igual ao do computador. Confirme lá. / It must be the same as on the computer. Confirm there. | Se for igual, clique em Confirmar no computador. | If it matches, click Confirm on your computer. | o título já diz "confira"; o corpo diz o que fazer e o nome do botão [shape] |
| `cam.pairing_failed` | Este QR code não vale mais. Leia um novo no computador. (55) | Este QR code não vale mais. Leia um novo. (41) | This QR code is no longer valid. Scan a new one. (48) | 3 linhas a 360px [taste] |
| `cam.blocked_network` | Este celular não está na mesma rede que o computador. (53) | Este celular não está na rede do computador. (44) | This phone is not on the computer's network. (44) | 3 linhas a 360px [taste] |
| `cam.blocked_attempts` | Muitas tentativas. Espere 10 minutos e leia um novo QR code. (59) | Muitas tentativas. Espere 10 minutos. (37) | Too many attempts. Wait 10 minutes. (35) | 3 linhas a 360px; depois de 10 minutos o QR antigo já venceu, e todos os estados finais já ensinam a ler um novo [taste] [shape] |
| `cam.ended_lost` | A conexão caiu. Leia um novo QR code para conectar de novo. (59) | A conexão caiu. Leia um QR code novo. (37) | Connection lost. Scan a new QR code. (36) | 3 linhas a 360px [taste] |

Ficam como estão: `cam.connecting`, `cam.confirm_title`, `cam.live`, `cam.busy`, `cam.ended_rejected`, `cam.ended_disconnected`, `cam.ended_timeout` (49 caracteres, cabe em duas linhas).

Nenhuma chave nova na `/cam`.

## 9. Perguntas para o orquestrador

1. Os cinco textos da §8 entram em `locales/`?
2. `invalid_request` e erros desconhecidos do `POST /api/sessions` levam a `ended` com `cam.ended_lost` (§4.4). Confirma?
