# Design v0.10.0, web

Spec: `docs/specs/spec-v0.10.0.md` §2. Skills: `impeccable` (audit do que mudou, detector sem achados) e `emil-design-eng` (frequência e movimento do zoom).

## Detalhes do console

- Linha "Decodificação" com "Placa de vídeo" ou "Processador", logo depois do codec, só na área de detalhes (métrica técnica, §5.7). Vem de `session.video.decoder`, ou de `videoSource.decoder` com o vídeo ativo. Sem linha quando `null`: antes do primeiro quadro a linha não aparece, em vez de mostrar "Sem dados" (impeccable: nada na tela sem função).

## `/dev`

- Etapa "Cópia da placa" (`transfer`) no gráfico de tempos por etapa, logo acima de "Decodificar", porque é parte do mesmo caminho na placa de vídeo. Sem token novo (decisão do orquestrador): `--data` com hachura a 45 graus, a mesma hachura na legenda. A forma diferencia a faixa da decodificação, então a cor não é o único sinal.
- Com decodificação no processador `transfer` é 0: a faixa não tem altura e a legenda some (só aparece com algum valor acima de 0 na janela), sem deixar espaço.
- No caminho do quadro, a etapa aparece entre "Decodificar" e "Cor" só com mediana acima de 0.
- Lista de eventos: rótulos para `decoder`, `video_source` e `timeline`.
- CSV: colunas `transfer_median_ms` e `transfer_p95_ms` logo depois das de decodificação.
- Achado P3 do audit, aceito: o gráfico estica o SVG sem manter proporção (`preserveAspectRatio="none"`, como as outras séries), então a hachura muda um pouco de ângulo e espessura com a largura da tela.

## Zoom da linha do tempo por Ctrl com a roda

- Ctrl com a roda sobre a faixa (régua e clipes) aproxima e afasta pelos mesmos níveis dos botões. Fora da faixa o Ctrl com a roda continua sendo o zoom da página.
- Um entalhe da roda é um nível; os deltas pequenos do trackpad (pinça) se somam até um nível, para não pular vários de uma vez.
- O ponto sob o cursor fica parado durante o zoom: o scroll é corrigido no mesmo quadro da troca de escala. No limite do zoom nada se move.
- Sem animação (emil-design-eng: gesto repetido muitas vezes seguidas fica lento se animar). Os clipes só animam o `transform` de reordenar, que o zoom não toca.

## Não verificado

- Visual no navegador: não vi as telas (sem subir o WCam nas portas 8080 e 8443); fica com o usuário.
