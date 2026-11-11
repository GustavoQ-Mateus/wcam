# Design v0.7.0, seletor de formato e celular em pé

Spec: `docs/specs/spec-v0.7.0.md` §1.1, §1.4, §2 e §4; handoff `docs/handoff-v0.7.0.md` (sessão web, itens 2 a 5)
Base: `docs/design-v0.2.0-cam.md`, `docs/design-v0.3.0-cam.md` e `docs/design-v0.6.0.md` (tokens, tipo, composições e movimento continuam valendo); `docs/planejamento.md` §5.3, §5.4, §5.6, §5.7
Status: direção aprovada pelo orquestrador em 2026-11-10, com os ajustes da §6. A aprovação visual final é do usuário (CA 9), com as telas prontas.

Legenda: **[shape]** `impeccable shape`, **[orq]** decisão do orquestrador, **[spec]** spec, contrato, handoff ou planejamento, **[mobile]** `mobile-native`, **[emil]** `emil-design-eng`, **[taste]** `taste-skill`. A direção saiu do `shape`; `taste`, `emil` e `mobile-native` entram na implementação e no polimento, e cada ajuste que fizerem é registrado aqui e no relatório.

Contexto do `impeccable`: sem `PRODUCT.md` nem `DESIGN.md`. O mundo visual é o `true-black-flat` das versões anteriores: elevação só por luminosidade, cor só em dado e estado. Modo **Operate**. O seletor de qualidade da v0.6.0, achado "feio" pelo usuário, é refeito do zero: não é ponto de partida, só evidência do que evitar (controle flutuando num painel vazio, rótulo genérico sobre um controle sem leitura do estado). **[shape] [taste]**

## 1. Brief

- **Para quê.** Escolher quanto de imagem o celular manda: resolução (720p a 4K) e fluidez (30 ou 60 fps), entre o que a câmera em uso entrega. A taxa de dados acompanha o formato, sem escolha separada. **[spec]**
- **Quem, onde.** O dono do celular, antes ou durante uma chamada, trocando nitidez por fluidez sem saber o que é codec ou taxa. No celular, com o aparelho no suporte, deitado ou em pé, a mão vai até a borda e troca. No PC, a mesma pessoa olhando o console de relance. **[shape]**
- **Sucesso.** Ver qual formato está em uso com um olhar e trocar resolução ou fluidez com um toque, sem chegar a uma combinação que não existe. As duas telas mostram sempre o mesmo formato, em menos de 300 ms (§5.4). **[spec]**
- **Fonte da verdade.** O formato marcado vem sempre do agente: o último `video_format` no celular, `videoFormat.selected` no console. Nunca da escolha local. **[spec]**

## 2. Regra das duas escolhas

Função pura em `data/`, com Vitest, usada pelas duas telas. **[shape] [orq]**

- **Resolução:** só as que existem em `available`, em ordem crescente: 720p, 1080p, 1440p, 4K.
- **Fluidez:** só os fps que a resolução marcada tem em `available`.
- **Escolher uma resolução** mantém a fluidez atual se ela existir nessa resolução; senão, usa a que existir.
- **Escolher uma fluidez** mantém a resolução atual se ela tiver essa fluidez; senão, usa a maior resolução que tenha.
- Cada toque gera uma única chave final (`set_video_format` no celular, `PUT /api/video-format` no console). Não há passo intermediário com combinação inválida.
- **Grupo com uma opção só não aparece.** Se a resolução marcada só tem uma fluidez em `available`, o grupo Fluidez some; o mesmo vale para Resolução com uma só (por exemplo, até a primeira `camera_capabilities`, quando só existe 1080p30). O formato atual em destaque já diz o valor, e um controle de uma opção é ruído. Se os dois somem, o seletor mostra só o formato atual. **[orq]**
- **Espera:** a opção tocada ganha o anel de espera da v0.6.0 até a confirmação chegar, ou por no máximo 2 s; o marcado continua o confirmado. **[spec] [emil]**

## 3. Celular (`/cam`, `live`)

### 3.1 Fechado

O terceiro botão do trilho continua no lugar do de qualidade. Ícone novo: um quadro 16:9 com dois cantos marcados ("enquadramento"), no lugar do medidor de três segmentos, que lia como "nível de qualidade". Mesmo traço e tamanho dos outros dois ícones. Nome acessível `format.label` ("Imagem"); o formato atual (`format.name`, por exemplo "1080p, 30 fps") vai em `aria-describedby`, sem chave nova. **[shape] [taste]**

Os botões do trilho mantêm o anel `--control-ring` da v0.6.0, para não sumir sobre faixas pretas. **[mobile]**

### 3.2 Aberto

Painel opaco em `--surface`, que abre a partir do botão com `scale(0.96)` e opacidade, saída mais rápida que a entrada, `ease-out` forte, como na v0.6.0. Fecha tocando fora ou com Esc, e ao confirmar a escolha. **[emil]**

```
 Paisagem (por exemplo 932x430)

 [visor .....................]  +------------------------+  ( )
                                | 1080p, 30 fps          |  ( )
                                |                        |  (▭)  <- aberto
                                | Resolução              |
                                | (720p) [1080p] (4K)    |
                                |                        |
                                | Fluidez                |
                                | ● 30 fps               |
                                |   O padrão das chamadas|
                                | ○ 60 fps               |
                                |   Movimento mais suave.|
                                +------------------------+
```

- **Topo: o formato atual em destaque** (`format.name`, peso forte, um passo acima do corpo). É a leitura de um relance, e repete de propósito o que os controles marcam. **[orq]**
- **Resolução** (`format.resolution_label`): uma fileira de pílulas de largura igual, de 44 px de altura. A marcada fica em `--ink` com texto preto, como o botão primário; as outras em `--raised`, como o secundário. A marcação aparece por contraste e forma, não por matiz. **[shape] [mobile]**
- **Fluidez** (`format.frame_rate_label`): linhas "30 fps" e "60 fps", cada uma com a sua dica (`format.frame_rate_30_hint`, `format.frame_rate_60_hint`), marcadas por disco cheio (marcada) ou anel vazio (as outras), como a v0.6.0. Só a fluidez tem uma troca a explicar (suavidade contra Wi-Fi); a resolução se explica pelo nome. Os dois tratamentos diferentes são de propósito. **[shape] [orq]**
- Sem Mbit/s no celular. **[spec]**
- Rádios nativos escondidos, `radiogroup` com `aria-labelledby` para cada grupo, e o foco visível no rótulo. **[spec]**
- Resposta no toque com `scale(0.97)` no `:active`, `touch-action: manipulation` e hover só com `(hover: hover) and (pointer: fine)`. **[mobile] [emil]**

### 3.3 Em pé (spec §2)

A partir desta versão o celular pode ficar em pé e continuar "Ao vivo". Saem o bloqueio e o pedido de girar. **[spec]**

```
 Retrato (por exemplo 390x844)

 +--------------------------+
 | 1080 × 1920 · 30 fps     |   leitura do formato, como hoje
 | (Deite o celular para…)  |   cam.portrait_hint, uma linha, topo
 |                ● Ao vivo |
 |                          |
 |     imagem da câmera     |
 |                          |
 |  +--------------------+  |
 |  | 1080p, 30 fps      |  |   painel aberto, acima da fileira
 |  | Resolução  ...     |  |
 |  | Fluidez    ...     |  |
 |  +--------------------+  |
 |     ( )   ( )   (▭)      |   trilho vira fileira, embaixo
 |   [Enviar print]         |   (só com as ferramentas de dev)
 +--------------------------+
```

- **Trilho:** em retrato, vira uma fileira horizontal centrada embaixo, acima da área segura. É onde o polegar alcança com uma mão; no meio da lateral direita, a mão teria de subir. **[mobile] [orq]**
- **Painel:** em retrato, abre acima da fileira, centrado, a partir do botão de formato, com a mesma animação. É o único elemento que cobre a imagem além dos controles, e só enquanto está aberto. **[orq] [emil]**
- **Dica de retrato** (`cam.portrait_hint`): uma pílula de uma linha em `--scrim`, com `--text-meta`, no topo, abaixo da leitura do formato, sobre o espaço acima da cabeça, a parte menos importante do enquadramento. Sem animação além do surgimento. Não é botão e não fecha: some sozinha ao deitar o celular. **[mobile] [orq]**
- **Ao girar,** o formato é aplicado de novo com largura e altura trocadas; o seletor não muda. **[spec]**
- O aviso de tela acesa e o botão do print (ferramentas de dev) continuam nas bordas de baixo, acima da fileira, sem sobrepor. Verificado em captura nos dois sentidos. **[mobile]**

## 4. Console (`/`)

Painel novo no lugar do de qualidade. **[shape] [orq]**

```
+ 1080p, 30 fps ----------------------------------+   formato atual = título do painel
| ▲ O novo formato de imagem começa quando…       |   só com videoFormat.pending
|                                                 |
| Resolução   [ 720p | 1080p | 1440p | 4K ]       |
| Fluidez     [ 30 fps | 60 fps ]                 |
|             O padrão das chamadas de vídeo.     |
|                                                 |
| Até 10 Mbit/s                                   |   detalhe: --text-meta, --faint
+-------------------------------------------------+
```

- **O título do painel é o formato atual**, em tamanho de título, e não um rótulo genérico sobre um controle. Responde de cara "o que está saindo agora". **[shape] [orq]**
- **Grade de duas colunas:** rótulo à esquerda em `--muted`, controle à direita, as duas linhas alinhadas pela mesma coluna. **[shape] [taste]**
- **Resolução e Fluidez:** controles segmentados de largura igual, só com as opções existentes; a marcada é a pílula branca. A dica da fluidez marcada fica logo abaixo do controle de fluidez. Grupos de uma opção não aparecem (§2). **[orq]**
- **Detalhe:** só `format.bitrate_limit` ("Até 10 Mbit/s"), em `--text-meta` `--faint`, números tabulares. O fps medido e o codec continuam na linha `console.video_format` do painel da sessão, sem chave nova. **[orq]**
- **`console.format_pending`** (com `videoFormat.pending`): linha com o triângulo `--warning` do painel da sessão, logo abaixo do título. Nesse estado, o título mostra o formato escolhido, e a linha diz que ele ainda não está saindo. **[spec] [orq]**
- **Clique:** `PUT /api/video-format`. Enquanto a confirmação não chega, a opção clicada ganha o anel de espera e a marcada continua a do status; erro mostra a mensagem de `errors.<code>`. **[spec]**

## 5. Fora

- Sem animação além do painel do celular e do anel de espera. Trocar de formato é ação rara: não ganha transição própria. **[emil]**
- Sem ícone por opção, sem cor por formato, sem Mbit/s no celular. **[shape] [spec]**
- Sem controles manuais de câmera (exposição, balanço de branco, foco): os modos `continuous` são pedidos sem nada na tela. **[spec]**

## 6. Decisões do orquestrador (2026-11-10)

1. O formato atual fica em destaque nas duas telas.
2. O fps medido e o codec ficam na linha `console.video_format` da sessão, sem chave nova; no painel de formato, só `format.bitrate_limit`.
3. Pílulas para a resolução e linhas com dica para a fluidez.
4. Grupo com uma opção só não aparece, tanto Fluidez quanto Resolução.
5. Em retrato, o trilho, o painel e `cam.portrait_hint` funcionam na zona do polegar, sem cobrir a imagem além do painel aberto (§3.3).
6. A regra das duas escolhas (§2) é registrada aqui.

## 7. Audit e polish (2026-11-10)

Só pela leitura do código e pelo e2e, sem captura de tela; a validação visual é do usuário, no navegador e no iPhone. **[orq]**

- **Detector** (`impeccable detect`) nos arquivos do seletor, do retrato e do console: nenhum achado. **[shape]**
- **Linhas de fluidez no celular** (`frame-rate-option`): ganharam `touch-action: manipulation`, sem seleção de texto no toque longo e `cursor: pointer`, como as pílulas de resolução. São `<label>`, que a base não cobre. **[mobile]**
- **Leitor do formato no celular:** mostrava o tamanho da abertura da câmera e não acompanhava a troca de formato. Agora se atualiza com o `getSettings` depois de cada formato aplicado. **[shape]**
- **Formato e modos em duas chamadas:** o Chromium mantém o tamanho antigo quando os modos da câmera (`advanced`) vêm na mesma chamada do `applyConstraints`. O formato é aplicado sozinho e depois repetido com os modos. **[spec]**
- Sem mudança de cor, espaço ou movimento. O painel e a dica em retrato seguem a §3.3. **[emil]**

