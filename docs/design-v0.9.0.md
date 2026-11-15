# Design v0.9.0, web

Registro das decisões de interface da sessão web na v0.9.0, com a skill que guiou cada uma (CLAUDE.md, seção Front). Mundo visual herdado da v0.8.0 (`docs/design-v0.8.0.md`), tokens de `docs/planejamento.md` §5.6.

## Área Vídeo: brief do `impeccable shape`

A skill pede uma rodada de perguntas antes do brief. Ela foi substituída pela spec v0.9.0 aprovada (§2 e §2.1), pelas decisões do usuário registradas nela e pelo console da v0.8.0, que já define o mundo visual. Suposições marcadas com (S).

1. **Tarefa e público.** Quem usa o WCam no próprio PC e quer que a câmera mostre um vídeo em vez do celular, antes de uma reunião ou durante ela. Modo Operate: escolher o arquivo, ligar, saber em um olhar que a câmera não está ao vivo e voltar ao celular.
2. **Resultado.** Enviar um vídeo, ver nome e duração, Usar vídeo; com o vídeo ativo, a prévia mostra o que os apps recebem e a linha do tempo permite pular para um ponto. A prova é a mesma prévia real da v0.8.0 (o quadro entregue à câmera).
3. **Direção.** O vídeo é um painel do mesmo sistema dos painéis Celular, Formato e Detalhes: plano em `--surface`, título pequeno em `--muted`, sem borda nem sombra. Aguardando: o painel entra na coluna do QR, abaixo de "QR code novo", como alternativa ao celular, sem competir com o QR, que continua dominante. Ao vivo com o celular: o painel entra na coluna lateral. Vídeo ativo: a tela troca o QR e a área do celular pelo estado "Vídeo em repetição", com o mesmo esqueleto do Ao vivo (prévia 16:9, linha do tempo, fileira de controles; painéis à direita).
4. **Escopo.** Escolher ou arrastar, progresso do envio, nome e duração no painel; fps, resolução e codec só em Detalhes (spec §2); Usar vídeo, Trocar vídeo, Remover vídeo; Voltar ao celular na fileira de controles, no lugar de Desconectar. Sem miniaturas, cortes ou marcadores (spec §2.1). Sem cancelar o envio (S: a spec não pede e não há texto para isso).
5. **Estados.** Sem arquivo (Escolher vídeo e "Ou solte um vídeo aqui"); arrastando por cima (o painel sobe para `--raised`, elevação por luminosidade); enviando (texto com a porcentagem e barra fina igual à da contagem do QR); com arquivo (nome em uma linha com reticências, duração, Usar vídeo em destaque); vídeo ativo (aviso "A câmera mostra o vídeo, não o celular", Trocar e Remover); erro por `code` em `--negative` dentro do painel, com o texto próprio de cada erro da spec.
6. **Interação.** A pílula de estado diz "Vídeo em repetição" com um triângulo de reprodução em `--data-2`, a mesma forma e cor do sexto estado da bandeja (spec §1.5); o verde fica reservado para o celular ao vivo, então a cor também separa os dois casos. Com Congelar, a pílula volta a ser "Imagem congelada" e a prévia mostra o aviso com Descongelar, como na v0.8.0. Desligar câmera e Trocar câmera somem da fileira com o vídeo ativo, porque exigem o celular (`409 no_live_session`).
7. **Restrições.** Textos só em `locales/`; termos do glossário §5.7 (nada de "upload", "arquivo enviado ao servidor"); foco visível de 2 px; cor nunca é o único sinal (pílula com forma e texto, progresso com porcentagem em texto).

## Linha do tempo (`emil-design-eng`, `animation-performance`)

- Uma linha só sob a prévia: "1:23 de 4:56" em figuras tabulares à esquerda e a barra ocupando o resto. A barra tem 4 px de altura visível e 44 px de área de toque, com um botão redondo de 14 px em `--ink`.
- A barra anda pelo relógio local a cada quadro (`requestAnimationFrame`) e só escreve `transform` (`scaleX` no preenchimento, `translateX` no botão): nada de `width` ou `left`, que forçariam layout 60 vezes por segundo. O React só renderiza quando o segundo mostrado muda.
- Arrastar: o botão cresce 15% enquanto segura (`--scale-grab`, 120 ms, `--ease-out`), para mostrar que pegou. O pedido sai ao soltar, não durante o arraste (spec §2.1). Depois de pular, a barra fica no ponto escolhido até o próximo valor do agente, sem voltar para a posição antiga.
- Teclado: `role="slider"` com rótulo "Posição no vídeo" e `aria-valuetext` com o mesmo texto visível; setas pulam 5 s, Home volta ao começo.
- Congelar para a barra (a posição para no agente e o relógio local não avança).
