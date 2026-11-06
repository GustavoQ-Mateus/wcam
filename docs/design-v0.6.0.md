# Design v0.6.0, seletor de qualidade

Spec: `docs/specs/spec-v0.6.0.md` §3, handoff `docs/handoff-v0.6.0.md` (sessão web, itens 1, 4 e 5)
Base: `docs/design-v0.2.0-cam.md` e `docs/design-v0.3.0-cam.md` (tokens, tipo, composições e movimento continuam valendo); `docs/planejamento.md` §5.3, §5.4, §5.6, §5.7
Status: proposta, aguardando aprovação do orquestrador

Legenda: **[shape]** `impeccable shape`, **[spec]** spec, contrato, handoff ou planejamento, **[mobile]** `mobile-native`, **[emil]** `emil-design-eng`, **[taste]** `taste-skill`. Esta proposta saiu do `shape`; `taste`, `emil` e `mobile-native` entram na implementação e no polimento, e cada ajuste que fizerem é registrado no relatório.

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
|                                                 (▂▄▆)|   qualidade
+------------------------------------------------------+
```

- **Um botão a mais no trilho que já existe**, mesmo tamanho (56px), mesmo `--scrim`, mesma posição na zona do polegar. Nada novo cobre a imagem enquanto fechado. **[shape] [spec]**
- **Ícone de três barras de altura crescente, com o número de barras cheias igual à opção** (3 Máxima, 2 Equilibrada, 1 Leve; as vazias só em contorno). O estado aparece pela forma, sem depender de cor, e sem abrir nada. **[shape] [spec]** (cor nunca é o único sinal)
- Nome acessível: `quality.label` com a opção atual ("Qualidade: Equilibrada"). **[shape]**
- Só aparece depois do primeiro `quality_preset`; antes disso o trilho fica como hoje. Com a prévia desligada, esmaece e fica inerte junto com os outros dois, como hoje. **[shape] [spec]**

### 2.2 Aberto: painel ao lado do trilho

```
+------------------------------------------------------+
| 1920 × 1080 · 30 fps                     | ● Ao vivo  |
|              +---------------------------+      (◐)  |
|              | Qualidade                 |      (⟲)  |
|              | ○ Máxima                  |   [ (▂▄▆) ]|
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

- **Painel opaco em `--surface`, à esquerda do trilho, alinhado à base dele**, para o polegar descer do botão direto para as opções. Cobre parte da imagem só enquanto está aberto, que é o momento da escolha. **[shape]**
- **Três linhas, cada uma alvo inteiro de toque (pelo menos 56px)**: nome em 16/600 `--ink`, dica (`quality.*_hint`) em `--text-meta` `--muted`, até duas linhas. Sem taxa em Mbit/s. **[spec]**
- **Marca de escolha por forma**: anel vazio nas outras, disco cheio na marcada, mais o nome em `--ink` contra `--muted` nas outras. Semântica de `radiogroup`, `aria-checked`. **[spec]** (não só por cor)
- **Toque numa opção**: envia `set_quality_preset`; a linha tocada mostra o anel pulsando de `connecting` (mesmo vocabulário de espera da v0.3.0) até chegar o `quality_preset`; aí o disco passa para ela e o painel fecha. Se o `quality_preset` não chegar em 2 s, o anel some e o disco continua onde o agente disse: nada de mostrar uma escolha que não vale. **[shape] [spec]**
- **Fecha** tocando fora, no próprio botão ou ao receber a confirmação. Mudança vinda do console com o painel aberto só move o disco. **[shape]**
- Largura fixa em `--measure` estreito (cerca de 18rem), para a dica não passar de duas linhas a 360px de altura de tela. **[shape]**

### 2.3 Movimento

- Painel: entra e sai por opacidade e um deslocamento curto vindo do trilho, em `--duration-state`. Disco trocando de linha: sem animação de posição, só troca. Movimento reduzido: só opacidade. **[shape]**; `emil` e `review-animations` confirmam na implementação.

## 3. Console (`/`)

### 3.1 Onde fica

O handoff põe o seletor "no painel da sessão", mas também pede que ele funcione sem celular conectado. Hoje o `SessionPanel` só existe com sessão, e sem ela o console mostra o `PairingPanel`. Proposta: **um painel próprio de qualidade, sempre presente quando há status, abaixo do painel da sessão ou do QR**. **[shape]** (ponto 1 da §5)

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
- **Taxa em Mbit/s** (`quality.bitrate_limit`) numa linha de detalhe em `--text-meta` `--faint`, a última do painel, como pede o glossário (§5.7). **[spec]**
- **Clique** chama `PUT /api/quality-preset`; enquanto a resposta não chega, a opção clicada ganha o anel de espera e a marcada continua a do status. Erro: a mensagem de `errors.<code>` que o console já mostra. **[shape] [spec]**

## 4. Estado congelado

`virtualCamera.source` `frozen` mostra `console.source_frozen` no painel da câmera virtual. Já está no código (commit `28057b6`), só troca o texto, sem forma nova. **[spec]**

## 5. Pontos para o orquestrador decidir

1. **Lugar do seletor no console** (§3.1): painel próprio, sempre presente, em vez de dentro do painel da sessão.
2. **300 ms do celular para o console.** O console lê `GET /api/status` a cada 1 s (`POLL_INTERVAL_MS` em `use-console.ts`) e o SSE só chega na v0.8.0. Uma troca feita no celular pode levar até 1 s para aparecer no console, então o CA 8 não passa como está. Opções: (a) baixar a leitura do status para 250 ms (o status é local, em `127.0.0.1`, e barato); (b) aceitar 1 s até o SSE e registrar no CA 8. Recomendo **(a)**, porque cumpre o CA sem contrato novo. O sentido console para celular já cumpre (mensagem no DataChannel).
3. **Área de detalhes no console.** Não existe ainda uma área "Detalhes" nem uma chave para ela; proponho a linha de detalhe em `--faint` no próprio painel, sem chave nova. Se preferir um `<details>` com rótulo, precisa da chave `console.details` nos dois idiomas.
4. **Ícone de barras** no celular (§2.1): desenho próprio em SVG, no padrão dos ícones do trilho.
