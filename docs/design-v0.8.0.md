# Design v0.8.0, web

Registro das decisões de interface da sessão web na v0.8.0, com a skill que guiou cada uma (CLAUDE.md, seção Front). Direção: protótipo aprovado pelo usuário em 2026-11-12 (https://claude.ai/artifact/4j5uK8opMCjxa2iy1p1F8b), tokens de `docs/planejamento.md` §5.6.

## Celular: confirmação nos dois lados (`mobile-native`)

- A tela Confirmar é o mesmo prompt sobre o visor (`ScrimLayer`), com o conteúdo alinhado embaixo: título, código enorme e dois botões lado a lado na zona do polegar, já que o celular é operado com uma mão (planejamento §5.3).
- É igual é a pílula branca (ação primária); É diferente é a pílula vazada com o anel `--control-ring`, mesma altura e mesma largura. As duas respostas têm peso visual parecido de propósito: recusar não pode parecer um erro de toque.
- O feedback de toque vem do `:active` existente (escala 0,97 em 120 ms). `touch-action: manipulation`, `user-select: none` e o realce de toque transparente já vêm de `base.scss` e valem para os dois botões.
- Depois de É igual, os botões somem e uma linha com a marca de espera diz "Agora confirme no computador." O celular não oferece desfazer: a resposta é única, como no contrato.
- Depois de É diferente, os botões somem e a tela de encerramento explica que outra pessoa pode ter lido o QR code (`cam.ended_code_different`).
- Não verificado ainda num celular real.

## Console: brief do `impeccable shape`

A skill pede uma rodada de perguntas antes do brief. Ela foi substituída pelos documentos já aprovados: spec v0.8.0 §2, planejamento §5.1 a §5.7 e o protótipo aprovado. Suposições marcadas com (S).

1. **Tarefa e público.** Quem usa o WCam no próprio PC, antes ou durante uma reunião, olhando de relance. Modo Operate: a pessoa quer saber se a imagem está saindo nos apps e agir em um clique. Uma coisa domina a tela em cada estado (planejamento §5.1).
2. **Resultado.** Aguardando: ler o QR. Confirmar: comparar o código e responder. Ao vivo: ver o que os apps recebem e controlar. A prova é a prévia real (o quadro entregue à câmera, com espelho, congelamento e câmera desligada aplicados) e a cadeia de sinal Celular, Wi-Fi, WCam no computador, Apps.
3. **Direção.** A do protótipo: cabeçalho com marca, pílula de estado (cor, forma e texto) e link Desenvolvedor; corpo de uma coluna com o foco do estado. Ao vivo tem duas colunas: prévia 16:9 com a fileira de controles embaixo, à esquerda; painéis Celular, Caminho da imagem e Detalhes à direita. Elevação só por luminosidade (`--surface` nos painéis, `--raised` nos botões secundários), sem sombra nem borda.
4. **Escopo.** Histórico e Ajustes do protótipo ficam fora (persistência, v1.0.0) (S): o cabeçalho leva só o link Desenvolvedor. O botão "Simular" do protótipo é só do protótipo. A comparação lado a lado da v0.6.0 continua atrás de `devTools`. O seletor de formato da v0.7.0 continua, refeito como painel do lado direito.
5. **Estados.** Aguardando (QR, contagem, três passos, QR code novo); Conectando (S: pílula de espera, sem prévia); Confirmar (aparelho e IP, pergunta, código em caixas, estado de cada lado, É igual e É diferente); Ao vivo; Imagem congelada (prévia parada, aviso com a hora, Descongelar em destaque); Câmera desligada (prévia preta com texto e Ligar câmera); Sinal perdido (`virtualCamera.source` `frozen`: prévia esmaecida, trecho do celular com problema) (S); Problema (câmera virtual indisponível: trecho Apps com problema e a correção em texto) (S). Prévia desligada: texto no lugar da imagem.
6. **Interação.** Os controles mostram sempre o estado do último `status` do SSE, nunca a escolha local. Congelar fica desabilitado com a câmera desligada. Desconectar fica separado à direita, em `--negative`. Detalhes é recolhível e é o único lugar com resolução, fps, taxa, codec, formato da câmera e CPU. Responsivo: abaixo da largura das duas colunas, a coluna lateral desce para baixo da prévia.
7. **Restrições.** Textos só em `locales/`; termos do glossário §5.7; contraste da §5.6; foco visível de 2 px; cor nunca é o único sinal (pílula e caminho levam forma e texto).

## Console: construção (`taste-skill`, regras de app screen)

- Modo Operate: cor só em dado e estado. O verde (`--data`) aparece na pílula Ao vivo, nas marcas "Funcionando" do caminho e na série principal dos gráficos. Botões e navegação ficam em neutros (`--raised`, pílula branca para a ação principal).
- Painéis planos em `--surface`, sem borda nem sombra. Elevação por luminosidade: `--raised` nos botões, `--raised-hover` (novo, #353535) no hover com mouse.
- Rótulos pequenos em caixa normal ("Celular", "Caminho da imagem", "Detalhes"), sem maiúsculas espaçadas. O protótipo usava caixa alta nos títulos dos painéis, e a regra de app screen da skill pede no máximo um rótulo assim por tela.
- Números em figuras tabulares (`font-variant-numeric: tabular-nums`) no código, nos detalhes e em `/dev`. Nenhuma fonte monoespaçada: o protótipo usava JetBrains Mono no código e nos números, e a skill trata isso como fantasia.
- Estado sempre com cor, forma e texto (`StatusMark`): círculo vazado aguardando, círculo cheio ao vivo, quadrado congelada, duas barras câmera desligada, triângulo problema ou sinal perdido. Mesmas formas da bandeja (spec §5).
- Fora do protótipo: Histórico e Ajustes (persistência) e o botão "Simular" (só do protótipo).

## `/dev` (`dataviz`, `taste-skill`)

- Gráficos em SVG próprio, sem biblioteca. Linha de 2 px para a série principal (`--data`); segunda série em `--data-2`, 1,5 px e tracejada; terceira em `--data-3`, pontilhada. Linha de referência tracejada em `--reference`; marcas de evento em `--warning` tracejadas e de perda em `--negative` cheias. Legenda sempre presente com mais de uma série.
- Validador da `dataviz` sobre `#3ecf8e,#e6e6e6,#6b6b6b` no fundo `#111111`: separação para daltonismo (ΔE 14,1), visão normal (22,4) e contraste passam. Faixa de luminosidade e croma falham porque a paleta do projeto (planejamento §5.6, travada) é um verde mais neutros, não uma paleta categórica. Compensação: espessura e tracejado diferentes por série e legenda sempre visível, para a cor nunca ser o único sinal.
- Camada de hover: linha vertical e tooltip com os valores do segundo apontado, sem animação (uso frequente).
- Minigráficos na faixa de saúde: a regra de app screen da `taste-skill` desaconselha, mas a spec §4.1 pede "um minigráfico" por número, e a spec vence.
- Escalas com teto arredondado (`niceCeiling`: 1, 2, 2,5, 5, 10 × potência de 10) e o valor do teto escrito no canto do gráfico.

## Revisão (`emil-design-eng`)

| Antes | Depois | Por quê |
| --- | --- | --- |
| Barra do QR com `transition: inline-size` | `transform: scaleX()` com origem à esquerda | Animar largura força layout; `transform` vai para a GPU |
| Botões da fileira de controles sem hover | Hover em `--raised-hover`, só com mouse | O mouse precisa saber que o elemento é clicável; o hover não gruda no toque |
| Botões de janela, pausa e exportação de `/dev` sem hover | O mesmo hover restrito ao mouse | Coerência com o console |
| Tooltip dos gráficos | Sem animação (mantido) | Segue o ponteiro o tempo todo; animar atrasaria a leitura |
| Troca de cor da pílula de estado | Instantânea (mantido) | Dado em tempo real; transição atrasaria a percepção |
| Coluna de controles do celular centralizada, sobrepondo a tally | Começa abaixo da tally; em altura curta, botões de 48 px e espaço de 8 px | Visto na captura do celular deitado (844 × 390) |

## Auditoria (`impeccable audit`)

Detector mecânico em `web/src/console`, `web/src/dev`, `web/src/cam` e `web/src/styles`: nenhum achado.

| # | Dimensão | Nota | Achado principal |
| --- | --- | --- | --- |
| 1 | Acessibilidade | 3 | Gráficos têm `role="img"` e rótulo, mas não há tabela equivalente na página (só o CSV), e o tooltip só responde ao ponteiro, não ao teclado |
| 2 | Desempenho | 4 | Só `transform` e `opacity` animam; a prévia fecha a conexão quando desligada |
| 3 | Temas | 4 | Tudo em tokens; um tema escuro só, por decisão do planejamento |
| 4 | Responsivo | 3 | Console e `/dev` empilham em tela estreita; `/dev` estreito não foi visto renderizado (a rota dava 404 no agente na hora da captura) |
| 5 | Integridade | 4 | Nenhum padrão genérico; o caminho da imagem e as marcas de forma vêm do produto |
| **Total** | | **18/20** | Excelente, com as duas lacunas acima |

Verificado com capturas renderizadas (Chromium no compose, câmera falsa): console Aguardando, Confirmar, Ao vivo, Congelada, Câmera desligada e Ao vivo em 390 px; celular Confirmar, esperando o PC, Ao vivo e Câmera desligada. Não verificado num celular real nem no iPhone.
