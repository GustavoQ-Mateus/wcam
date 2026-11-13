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
