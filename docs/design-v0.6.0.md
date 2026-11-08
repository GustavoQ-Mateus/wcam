# Design v0.6.0, seletor de qualidade

Spec: `docs/specs/spec-v0.6.0.md` §3, handoff `docs/handoff-v0.6.0.md` (sessão web, itens 1, 4 e 5)
Base: `docs/design-v0.2.0-cam.md` e `docs/design-v0.3.0-cam.md` (tokens, tipo, composições e movimento continuam valendo); `docs/planejamento.md` §5.3, §5.4, §5.6, §5.7
Status: aprovado pelo orquestrador em 2026-11-06, com o ícone do trilho trocado (§2.1)

Legenda: **[shape]** `impeccable shape`, **[orq]** decisão do orquestrador, **[spec]** spec, contrato, handoff ou planejamento, **[mobile]** `mobile-native`, **[emil]** `emil-design-eng`, **[taste]** `taste-skill`. Esta proposta saiu do `shape`; `taste`, `emil` e `mobile-native` entram na implementação e no polimento, e cada ajuste que fizerem é registrado no relatório.

Contexto do `impeccable`: sem `PRODUCT.md` nem `DESIGN.md`; o mundo visual é o das versões anteriores, e esta é uma peça dentro dele, não uma superfície nova. **[shape]**

## 1. Brief

- **Para quê.** Baixar a taxa de dados quando o Wi-Fi ou o PC não aguentam, ou subir para a Máxima quando aguentam. É ajuste de vez em quando, não de toda hora: o padrão (Equilibrada) serve à maioria. **[spec]**
- **Quem, onde.** No celular, com o aparelho já no suporte e em paisagem, a imagem travando ou pixelando: a pessoa estica a mão e troca. No PC, a mesma pessoa olhando o console de relance, com ou sem celular conectado. **[shape]**
- **Sucesso.** Trocar em dois toques sem perder o enquadramento de vista, e as duas telas mostrarem sempre a mesma opção. **[spec]** (§5.4)
- **Fonte da verdade.** A opção marcada vem sempre do agente (`quality_preset` no celular, `qualityPreset` do status no console), nunca do toque local. **[spec]**

## 2. Celular (`/cam`, `live`)

### 2.1 Fechado: terceiro botão no trilho

```
+------------------------------------------------------+
| 1920 × 1080 · 30 fps                     | ● Ao vivo  |
|                                                 (◐)  |   desligar prévia
|               imagem da câmera, 16:9            (⟲)  |   trocar câmera
|                                                 (■■□)|   qualidade
+------------------------------------------------------+
```

- **Um botão a mais no trilho que já existe**, mesmo tamanho (56px), mesmo `--scrim`, mesma posição na zona do polegar. Nada novo cobre a imagem enquanto fechado. **[shape] [spec]**
- **Ícone: medidor de três segmentos iguais, lado a lado na horizontal, com os segmentos cheios da esquerda para a direita conforme a opção** (3 Máxima, 2 Equilibrada, 1 Leve; os vazios só em contorno, no traço de 2px dos outros ícones do trilho). O estado aparece pela forma, sem depender de cor, e sem abrir nada. **[shape] [spec]** (cor nunca é o único sinal)
- **Por que não barras de altura crescente** (a primeira proposta): é o ícone universal de força de sinal, e no trilho de uma câmera sem fio a pessoa leria "força do Wi-Fi", não "qualidade escolhida". **[orq]** Segmentos de mesma altura tiram a leitura de sinal e ficam com a de quantidade: um trilho do tamanho do máximo com a parte usada cheia, que é a forma com que as telas de app estudadas mostram "quanto do total" **[taste]** (`app-screens.md`, medidor de uso do plano). Segmentos retangulares iguais (4 por 7 no quadro de 24) com canto de 1px, no mesmo desenho de traço e canto dos ícones de prévia e de troca de câmera, para o trilho ler como uma família só **[emil]** (detalhes invisíveis que somam); sem contorno externo nem polo, que fariam o desenho ler como bateria.
- Nome acessível: `quality.label`, com a opção atual como descrição (`aria-describedby`), lida logo depois do nome ("Qualidade, botão, Equilibrada"), sem chave nova. `aria-expanded` diz se o painel está aberto. **[shape]**
- Só aparece depois do primeiro `quality_preset`; antes disso o trilho fica como hoje. Com a prévia desligada, esmaece e fica inerte junto com os outros dois, como hoje. **[shape] [spec]**

### 2.2 Aberto: painel ao lado do trilho

```
+------------------------------------------------------+
| 1920 × 1080 · 30 fps                     | ● Ao vivo  |
|              +---------------------------+      (◐)  |
|              | Qualidade                 |      (⟲)  |
|              | ○ Máxima                  |   [ (■■□) ]|
|              |   A mais próxima do que o |           |
|              |   celular mostra. Precisa |           |
|              |   de um Wi-Fi bom.        |           |
|              | ● Equilibrada             |           |
|              |   Boa imagem na maioria...|           |
|              | ○ Leve                    |           |
|              |   Para Wi-Fi fraco ou ... |           |
|              +---------------------------+           |
+------------------------------------------------------+
```

- **Painel opaco em `--surface`, à esquerda do trilho e centrado nele**, perto do polegar. Centrado, e não alinhado à base do botão como na primeira proposta, porque com três opções e dicas ele passa de 290px e, alinhado à base, cortaria em celulares de 360px a 390px de altura em paisagem; acima disso a altura fica limitada à tela, com rolagem própria. Cobre parte da imagem só enquanto está aberto, que é o momento da escolha. **[shape] [mobile]** (`overscroll-behavior: contain` na rolagem do painel)
- **Três linhas, cada uma alvo inteiro de toque (pelo menos 56px)**: nome em 16/600 `--ink`, dica (`quality.*_hint`) em `--text-meta` `--muted`, até duas linhas. Sem taxa em Mbit/s. **[spec]**
- **Marca de escolha por forma**: anel vazio nas outras, disco cheio na marcada, mais o nome em `--ink` contra `--muted` nas outras. Semântica de `radiogroup`, `aria-checked`. **[spec]** (não só por cor)
- **Toque numa opção**: envia `set_quality_preset`; a linha tocada mostra o anel pulsando de `connecting` (mesmo vocabulário de espera da v0.3.0) até chegar o `quality_preset`; aí o disco passa para ela e o painel fecha. Se o `quality_preset` não chegar em 2 s, o anel some e o disco continua onde o agente disse: nada de mostrar uma escolha que não vale. **[shape] [spec]**
- **Fecha** tocando fora, no próprio botão ou ao receber a confirmação. Mudança vinda do console com o painel aberto só move o disco. **[shape]**
- Largura fixa em `--measure` estreito (cerca de 18rem), para a dica não passar de duas linhas a 360px de altura de tela. **[shape]**

### 2.3 Movimento

- Painel: entra por opacidade e escala de 0,96 a 1 com origem no canto de baixo à direita, o lado do botão que o abriu, em `--duration-state` e `--ease-out`; sai mais rápido, em `--duration-cover`. **[emil]** (popover sai do gatilho; nunca de `scale(0)`; saída mais rápida que a entrada)
- Disco trocando de linha: sem animação, só troca. É dado de estado, e um disco viajando entre linhas faria parecer que a escolha ainda está acontecendo. **[emil]** (dado não se anima) **[taste]**
- Linhas do painel e botão: `scale(0.97)` no toque, em `--duration-press`, como os outros controles. **[emil] [mobile]** (resposta no toque, não na soltura)
- Movimento reduzido: o painel só por opacidade, e o anel de espera para de pulsar. **[emil]**

## 3. Console (`/`)

### 3.1 Onde fica

O handoff põe o seletor "no painel da sessão", mas também pede que ele funcione sem celular conectado. Hoje o `SessionPanel` só existe com sessão, e sem ela o console mostra o `PairingPanel`. Decisão: **um painel próprio de qualidade, sempre presente quando há status, abaixo do painel da sessão ou do QR**. **[shape] [orq]**

```
+--------------------------------------+
| ● Ao vivo                            |
| iPhone · Safari   192.168.100.31     |
| 1920 × 1080 · 30.0 fps · 9.8 Mbit/s  |
| [Desconectar]                        |
+--------------------------------------+
+--------------------------------------+
| Qualidade                            |
| ( Máxima | •Equilibrada• | Leve )    |   controle segmentado, 3 opções
| Boa imagem na maioria das redes Wi-Fi.|  dica da opção marcada
| Até 10 Mbit/s                        |   detalhe: --text-meta, --faint
+--------------------------------------+
```

- **Controle segmentado** de três partes (`radiogroup`, setas do teclado), em `--raised`; a marcada vira a pílula branca do botão primário (fundo `--ink`, texto preto), então a marcação aparece por contraste e forma, não por matiz. **[shape] [spec]**
- **Dica só da opção marcada**, embaixo, em `--muted`. No PC há espaço, mas três dicas lado a lado brigariam com o resto do painel. **[shape]**
- **Taxa em Mbit/s** (`quality.bitrate_limit`) numa linha de detalhe em `--text-meta` `--faint`, a última do painel, como pede o glossário (§5.7), sem chave nova. O `<details>` com rótulo fica para o console definitivo da v0.8.0. **[spec] [orq]**
- **Leitura do status a cada 250 ms** (antes 1 s) para a troca feita no celular aparecer no console em menos de 300 ms (CA 8). O status é local (`127.0.0.1`) e barato; o SSE da v0.8.0 substitui esta leitura. **[orq]**
- **Clique** chama `PUT /api/quality-preset`; enquanto a resposta não chega, a opção clicada ganha o anel de espera e a marcada continua a do status. Erro: a mensagem de `errors.<code>` que o console já mostra. **[shape] [spec]**

## 4. Estado congelado

`virtualCamera.source` `frozen` mostra `console.source_frozen` no painel da câmera virtual. Já está no código (commit `28057b6`), só troca o texto, sem forma nova. **[spec]**

## 5. Decisões do orquestrador (2026-11-06)

1. Painel próprio de qualidade no console, sempre presente quando há status (§3.1).
2. Leitura do status a cada 250 ms, sem mudança de contrato, até o SSE da v0.8.0 (§3.1).
3. Linha de detalhe em `--faint` no próprio painel, sem chave nova (§3.1).
4. Ícone do trilho: medidor de três segmentos iguais na horizontal, em vez de barras de altura crescente (§2.1).

## 6. Comparação lado a lado (ferramenta de desenvolvimento, 2026-11-07)

Spec §6, CA 3.3, decisão 9. Modo **Operate**: quem usa é o desenvolvedor (o usuário, validando a calibração), com o console aberto num monitor ao lado do celular. Só existe com `devTools` no status; o produto não muda.

### 6.1 Console

- **Botão no painel da sessão**, `console.dev_compare`, secundário (`--raised`), depois do Desconectar, só com `devTools` e sessão `live` (função pura `comparisonAvailable`, com Vitest). Não compete com a ação principal do painel. **[shape] [spec]**
- **Painel próprio, largura total da página**, em `--surface` como os outros painéis (elevação só por luminosidade, `true-black-flat`). As imagens precisam de largura; o `--measure` dos outros painéis as deixaria pequenas demais para comparar cor. **[taste-skill] [shape]**
- **Imagens lado a lado no mesmo tamanho**: grade `auto-fit` com mínimo de `--comparison-image-min` (24rem); em tela estreita empilham. Cada imagem num quadro com a proporção dela (`aspect-ratio`), fundo `--ground`, `object-fit: contain`. Legenda embaixo: nome em peso forte e o horário da captura em `--muted`, números tabulares, com milissegundos, porque a diferença entre as capturas importa. **[taste-skill] [spec]**
- **Grade 8x4 sobre a imagem do PC** (decisão do orquestrador): linhas finas em `--reference`, número em cada célula sobre um fundo `--scrim` pequeno, só atrás do número, sem preencher a imagem. Célula com ΔE acima de 2 (pelo valor mostrado, para o número e o contorno nunca discordarem) ganha contorno `--warning` mais grosso e número em `--warning` e peso forte: forma, número e cor, nunca só cor. A grade é uma lista (`aria-label` `console.dev_compare_grid`). **[shape] [orq] [emil-design-eng]**
- **Dados na área de detalhes**, em grupos com título: "Celular / Câmera WCam no computador" e, com o print, "Tela do celular / Celular" e "Tela do celular / Câmera WCam no computador". Linhas em `--text-meta` `--muted`, números tabulares, sinal explícito em ΔL* e matiz. Métricas técnicas só aqui, como manda o glossário. **[spec] [taste-skill]**
- **Downloads** como links (`<a download>`) com a forma do botão secundário: imagem do celular (rota do agente), imagem do PC (o PNG capturado, por `blob:`), print (rota do agente) e o JSON do relatório (`data:` com o relatório como chegou). Nada passa pelo disco do agente. **[spec]**
- **Print pelo console**: rótulo com a forma do botão secundário envolvendo um `input type=file` escondido (`accept="image/png"`), dica `console.dev_compare_screen_hint` em `--faint` ligada por `aria-describedby`. Some quando o print chega. **[spec] [shape]**
- **Espera**: anel pulsando em `--muted` com `console.dev_compare_pending` (`role="status"`), o mesmo anel da escolha de qualidade; sem animação com `prefers-reduced-motion`. **Falha**: quadrado `--negative` mais `console.dev_compare_failed` com o motivo do agente (`role="alert"`); o quadrado repete a forma de erro do console. **[emil-design-eng] [shape]**
- Sem animação de entrada no painel: é ferramenta usada em sequência, e o conteúdo chegando já é a resposta. **[emil-design-eng]**

### 6.2 Celular

- **Botão `cam.dev_send_screenshot`** só depois de um `snapshot_request` (só existe com as ferramentas de desenvolvimento), no canto inferior direito, abaixo do trilho: é onde o polegar direito já está, segurando o celular em paisagem, e não cobre o centro do visor. Pílula pequena em `--scrim`, `--text-meta` em peso forte, altura mínima de 44 px. **[mobile-native] [orq]**
- `touch-action: manipulation`, sem seleção de texto no toque longo, `scale(0.97)` no `:active`, foco visível pelo `:has(:focus-visible)`. Abre o seletor de arquivo do iOS (`accept="image/png"`). **[mobile-native] [emil-design-eng]**
- **Resultado ao lado do botão**, na mesma linha, por 3 s: `cam.dev_screenshot_sent`, ou `cam.dev_screenshot_failed` em `--warning` (o texto já diz o que houve, então a cor não é o único sinal). Ao lado e não acima, para não encostar no trilho em telas de 390 px de altura. `role="status"`. **[mobile-native] [shape]**
- O arquivo só é enviado se começar pela assinatura PNG (`isPng`, com Vitest); um JPEG renomeado também é recusado. **[spec]**

