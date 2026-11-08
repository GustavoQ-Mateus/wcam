# Spec v0.6.0, Fidelidade de imagem

Status: Aprovada (2026-11-06; calibração de cor, §1.1, aprovada no mesmo dia)
Branch de integração: `feature/qualidade`
Sessões: `agent`, `web`, `vcam`
Referências: `docs/planejamento.md` §1 (CA-2), §5.4; ADRs 0011 e 0012; changelog da v0.5.0 (diagnóstico da faixa de cor); diagnóstico da reunião de 2026-11-04 (imagem preta por alguns segundos)

## Objetivo

A imagem da câmera "WCam" no PC tem que estar no mesmo nível da prévia no celular. Esta versão corrige o que hoje a deixa pior, sem mudar o formato da câmera (continua 1920x1080 a 30 fps):

1. **Faixa de cor.** O Safari do iPhone envia faixa cheia (0 a 255), e a WCam é lida como faixa limitada (16 a 235). Sombras viram preto e altas luzes viram branco.
1. **Calibração de cor.** Mesmo com a faixa certa, a imagem no PC fica mais escura nos meios-tons que a prévia do celular. A cada conexão, o celular mostra ao agente o que está exibindo, e o agente iguala a cor da câmera a isso, sem nenhuma ação do usuário (§1.1).
2. **Imagem preta por alguns segundos.** Quando o vídeo do celular para de chegar por mais de 1 s, o agente troca para preto. Na reunião de 2026-11-04 isso aconteceu algumas vezes, com a prévia do celular normal.
3. **Escolha de qualidade.** O usuário escolhe a taxa de dados (Máxima, Equilibrada, Leve) no celular ou no console, e reduz se o Wi-Fi ou o PC não aguentarem.

E prepara a v0.7.0 (resolução e fps à escolha do usuário) medindo o que o navegador do celular entrega e quanto de CPU cada formato custa no PC.

## 1. Faixa de cor e matriz

Quem decide a faixa e a matriz é o celular: cada aparelho as declara no próprio fluxo H.264, e o agente lê essa declaração em cada quadro, sem supor nada pelo modelo do aparelho. Medido em 2026-11-03 no iPhone 16 Pro Max do usuário (Safari): `yuvj420p`, `color_range` 2 (faixa cheia), `colorspace`, primária e transferência não declaradas; de 3,6% a 5,3% dos pixels abaixo de 16. Outros aparelhos ainda não foram medidos.

Decisão: a câmera WCam anuncia sempre **faixa limitada (16 a 235)**, que é o padrão das webcams e o que os apps assumem. Ela só pode anunciar uma faixa, negociada uma vez com o app, então o agente traduz a faixa declarada por cada celular para a anunciada.

Agent:
- Lê a faixa de cada quadro decodificado (`color_range` do PyAV e o formato `yuvj420p`). Faixa cheia é normalizada por tabela de consulta: Y para `16 + Y × 219 / 255`, U e V para `128 + (C − 128) × 224 / 255`, com arredondamento. Faixa limitada passa sem mudança, como hoje. Faixa não declarada é tratada como limitada; isso é suposição, conferida pelo campo abaixo em cada aparelho testado.
- Registra o que o celular declarou: `session.video.colorRange` (`full`, `limited` ou `unspecified`) e `session.video.colorMatrix` (`bt709`, `bt601`, outro nome do FFmpeg ou `unspecified`), para conferir qualquer aparelho em vez de supor.
- Matriz: quando o celular declara uma matriz diferente da anunciada pela WCam, o relatório registra o caso; converter matriz fica fora desta versão até um aparelho real precisar.
- A normalização roda fora do event loop, junto da conversão para NV12.
- Isso emenda o CA-2 do produto ("sem converter cor"). Primeira redação: a única transformação permitida é ajustar a faixa ao formato anunciado pela câmera, sem tocar em resolução nem matiz. Substituída pela redação da decisão 5 (calibração, §1.1). O planejamento §1 registra a emenda.

Vcam:
- O tipo de mídia passa a declarar `MF_MT_VIDEO_NOMINAL_RANGE` (16 a 235) e a matriz de cor, a primária e a função de transferência, hoje omitidas.
- A matriz anunciada (BT.709 ou BT.601) é escolhida por medição, não suposta: o probe publica barras de cor de valores conhecidos, e o relatório compara o RGB lido no Chrome e no app Câmera com o esperado para cada matriz. Como o iPhone não declara a matriz, a mesma medição é feita com um quadro real dele contra a prévia.

## 1.1 Calibração de cor

Medição de 2026-11-06 no iPhone do usuário (spike `spike/color-space` e `spike/color-sample`, 10 amostras, correlação 0,995):
- O iPhone declara no SPS do H.264 só a faixa (`video_full_range_flag` 1). Matriz, primária e transferência vêm como "unspecified" (código 2). O Safari negocia a extensão RTP `color-space`, mas não a envia. Nenhum dado de cor além da faixa vem do celular.
- O que o agente decodifica já é igual ao que o Safari mostra, a menos da curva de tom: o Safari exibe o vídeo com uma curva de cerca de 1,96 (a do ColorSync da Apple), mais clara nos meios-tons. A câmera WCam, lida pelo Windows como BT.709 limitada, fica com ΔE2000 médio de 2,49 contra a prévia (ΔL* −2,8, até 11 códigos nos meios-tons). Com a curva medida, cai para cerca de 1,2.
- A matriz não foi decidível na cena medida (pouca cor: BT.709 contra BT.601 deu ΔE2000 0,44, abaixo do ruído de 1,2).

Decisão do usuário (2026-11-06): o que o celular mostra tem que ser o que o PC mostra, para qualquer aparelho, sem ajuste por modelo e sem ação da pessoa. Por isso a cor é **medida a cada conexão**, contra o que o próprio celular exibe.

Web:
- Com a sessão `live` e o celular em paisagem, o `/cam` desenha o quadro atual do visor num canvas 160x90 (sem espelho; `colorSpace` `display-p3` quando o navegador aceita, senão `srgb`) e envia `color_sample` (contrato) uma vez por segundo, 5 vezes. Repete as 5 a cada troca de câmera. Em retrato, espera o paisagem. Sem texto nem elemento novo na tela.
- A captura do canvas fica num hook em `media/`; a montagem da mensagem é função pura em `data/`, testada no Vitest.

Agent:
- Guarda os quadros decodificados dos últimos 2 s, reduzidos, só enquanto há amostras a comparar. Para cada amostra, escolhe o quadro de maior correlação de luminância. Amostra com correlação abaixo de 0,8 é descartada.
- Com pelo menos 3 amostras válidas, ajusta a correção: uma curva de tom monotônica no Y e um ganho de saturação no U e V, que minimizam o ΔE2000 entre a amostra e a saída corrigida lida como BT.709 em faixa limitada, no espaço de cor da amostra.
- A correção é aplicada como tabela de consulta no Y e no U e V, composta com a tabela de faixa que já existe, no mesmo worker, sem passar por RGB e sem tocar em resolução. O custo por quadro não muda.
- Só aplica se reduzir o ΔE2000; senão, fica a faixa sem curva (estado `default`). A troca de tabela é de um quadro para o outro.
- A matriz anunciada continua BT.709; a calibração não converte matriz. Se um aparelho real mostrar diferença de matiz que só a matriz explica, isso vira escopo de outra versão.
- Tudo vale só para a conexão atual: ao encerrar, a correção e as amostras são descartadas. Nada é gravado em disco nem associado ao aparelho (CA-4). A troca de câmera recomeça a medição.
- `session.video.colorCalibration` no status (contrato).
- `color_sample` antes do `live` é ignorado com registro no log, como `set_quality_preset`.

Console:
- Na área de detalhes, uma linha: `console.color_matched` quando a calibração foi aplicada, `console.color_default` nos outros casos. Nada na mensagem principal.

Vcam:
- Verificação de ponta a ponta, sem nenhum passo do usuário além de conectar o celular, com a ferramenta `vcam/tools/Wcam.ColorVerify` (fora da DLL e do publish AOT):
  - leitura do Chrome: o probe publica uma grade de cores YUV conhecidas, a ferramenta lê o que o Chrome entrega (`getUserMedia`, como no Meet, canvas em `display-p3` e `srgb`) e ajusta o modelo YUV para RGB do Chrome, registrando o desvio conhecido do azul;
  - do agente, com `WCAM_COLOR_TRACE_DIR` (desenvolvimento, vazia por padrão): cada `color_sample`, o quadro casado e as tabelas aplicadas;
  - resultado: ΔE2000 médio entre cada amostra do celular e o que o Chrome mostraria do quadro casado, antes e depois da correção. O relatório descreve o método e registra os números.

## 2. Imagem preta por alguns segundos

O diagnóstico de 2026-11-04 descartou a câmera nativa e o Frame Server. O preto mais provável é o placeholder do agente por silêncio de mais de 1 s, com duas origens que os dados não separaram: um pacote perdido sem recuperação trava o buffer de recepção do aiortc (medido em laboratório: de 2 a 8 s sem quadro com o buffer de 2048 pacotes, conforme a taxa) ou o vídeo parou de chegar pelo Wi-Fi.

Decisão do usuário (2026-11-06): numa falha curta, **congelar a última imagem** em vez de preto.

Agent:
- **Congelar.** Sem quadro novo do celular, a câmera repete o último quadro bom por até 3 s. Depois disso, preto, como hoje. Substitui o CA 4 da v0.5.0 ("nunca imagem congelada") só para esses 3 s.
- **Recuperar.** Se os pacotes RTP continuam chegando mas nenhum quadro sai do buffer de recepção por mais de 500 ms, o agente descarta o trecho travado e pede um quadro-chave ao celular (PLI). O mecanismo exato sai do teste de laboratório abaixo e fica no relatório.
- **Registrar.** Cada episódio sem quadro novo por mais de 500 ms com sessão `live` vira uma linha JSON em `<WCAM_DATA_DIR>/logs/episodes.log` (rotação em 1 MB, um arquivo antigo guardado): início e fim em UTC, duração, causa (`silence`, `stalled`, `portrait`), ação (`frozen`, `black`), bytes RTP recebidos durante o episódio e PLIs enviados. Nada de token, URL de pareamento ou IP completo no arquivo.
- **Teste de laboratório**, automatizado no pytest: um cliente aiortc envia vídeo, um pacote e o seu reenvio são descartados, e o teste mede o tempo sem quadro de ponta a ponta.

## 3. Escolha de qualidade

Decisão do usuário (2026-11-06): o seletor fica no celular e no console, e uma mudança feita num aparece no outro em menos de 300 ms (§5.4). Nesta versão só muda a taxa de dados; resolução e fps ficam para a v0.7.0.

| Opção | Chave | Taxa máxima | Uso |
|---|---|---|---|
| Máxima | `maximum` | 20 Mbit/s | a imagem mais próxima da prévia; exige Wi-Fi bom |
| Equilibrada | `balanced` | 10 Mbit/s | padrão, o valor da v0.5.0 |
| Leve | `light` | 5 Mbit/s | Wi-Fi fraco ou PC sobrecarregado |

- O celular aplica a taxa em `maxBitrate` do envio (`setParameters`, sem renegociar). O agente ajusta o teto da estimativa de banda (REMB) ao mesmo valor.
- A escolha vale até o agente fechar; guardar entre reinícios é da persistência.
- Os valores são confirmados no iPhone do usuário antes da entrega: a Máxima sustenta 10 min sem episódio de congelamento no Wi-Fi dele, ou o relatório propõe outro valor.
- Os textos de interface seguem o glossário (§5.7): os nomes das opções na mensagem principal, a taxa em Mbit/s só em detalhes.

## 4. QR fora de arquivo de log

O terminal imprime o QR e a URL com token só quando a saída é um terminal interativo. Com a saída redirecionada para arquivo (como nas rodadas desta sessão), imprime só a orientação de abrir o console. Hoje a URL de pareamento vai parar no arquivo.

## 5. Medição para a v0.7.0

Nada aqui muda o formato da câmera; é só levantamento, registrado nos relatórios.

- Web: depois que o DataChannel abre, o celular envia as capacidades da câmera em uso (`getCapabilities()`: largura, altura e fps máximos, por câmera frontal e traseira quando disponível) e os codecs de vídeo que o navegador sabe enviar (`RTCRtpSender.getCapabilities("video")`, só os `mimeType`). O agente expõe isso no status.
- Agent: script de desenvolvimento `python -m wcam.tools.decode_benchmark` que decodifica H.264 sintético em 1280x720, 1920x1080, 2560x1440 e 3840x2160, a 30 e 60 fps, e mede a CPU do processo.
- Usuário, no iPhone dele: o relatório registra as capacidades reais e o resultado do benchmark nesta máquina.

## 6. Comparação lado a lado (ferramenta de desenvolvimento)

Motivo: no teste final de 2026-11-07, a calibração chegou a `applied` com `deltaE` 1,01 medido pelo agente, e o usuário viu a WCam no app Câmera "bem diferente" do celular. Comparar a olho entre duas telas não separa as causas possíveis (a amostra do canvas não ser o que a tela do iPhone mostra, o app do PC, os monitores). Pedido do usuário (2026-11-07): um botão no console que captura ao mesmo tempo a prévia do celular e a câmera WCam, mostra as duas lado a lado no mesmo monitor, permite baixar as imagens e traz os dados para validar a calibração.

Só existe com `WCAM_DEV_TOOLS=1` (desenvolvimento); sem a variável, as rotas respondem `404`, as mensagens novas são ignoradas com log e o botão não aparece. Nada vai para o disco do agente: as comparações ficam em memória (as últimas 5) e o usuário baixa o que quiser pelo navegador.

Console (web):
- Com `devTools` no status e a sessão `live`, o painel da sessão mostra `console.dev_compare`. O clique chama `POST /api/dev/comparisons` e, no mesmo instante, captura um quadro da câmera WCam no navegador do PC (`getUserMedia` com o dispositivo "WCam", canvas `srgb` no tamanho do vídeo, PNG), enviado por `PUT /api/dev/comparisons/{id}/pc`.
- Quando a comparação fica `ready`, mostra as duas imagens lado a lado no mesmo tamanho, com o horário de cada captura, e na área de detalhes os dados do relatório. Botões para baixar a imagem do celular, a do PC e o relatório JSON.
- Acesso à câmera e canvas em `media/`; formatação dos dados em `data/`, com Vitest.

Celular (web):
- Ao receber `snapshot_request` em `live`, desenha o quadro atual do visor num canvas no tamanho nativo do vídeo, sem espelho, no `colorSpace` `display-p3` quando aceito, e envia o PNG pelo DataChannel em pedaços (contrato). Sem texto nem elemento novo na tela.

Agent:
- `POST /api/dev/comparisons` cria a comparação, guarda o horário e manda `snapshot_request` ao celular; remonta os pedaços e confere o tamanho.
- Com as duas imagens, monta o relatório: horários das duas capturas e a diferença entre eles; estado e `deltaE` da calibração e as tabelas em uso; e a diferença de cor entre as duas imagens, depois de alinhar (redução por média de área para 320x180, casamento por correlação de luminância com e sem espelho, células de detalhe fino excluídas como na calibração): ΔE2000 médio, mediano e p90, ΔL*, razão de croma, desvio de matiz e uma grade 8x4 com o ΔE2000 médio de cada região. A imagem do celular é lida no seu `colorSpace`, a do PC em sRGB.
- Prazo de 10 s para o celular responder; senão `failed` com o motivo.

Uso esperado: o usuário compara as duas imagens no mesmo monitor. Se elas estiverem iguais no PC e a tela do iPhone parecer diferente, a amostra do canvas não representa o que a tela do celular mostra, e a calibração mede a coisa errada. Se forem diferentes no PC, os números dizem onde (tom, saturação, matiz, região).

## Contrato (`docs/contrato.md` vai para 0.6.0)

Console:
- `PUT /api/quality-preset` com `{"preset": "maximum" | "balanced" | "light"}`: `204`; `422 invalid_request` com valor desconhecido. Vale para a sessão atual e as próximas.
- `GET /api/status` ganha `qualityPreset` no primeiro nível (sempre presente), `virtualCamera.source` ganha o valor `frozen`, `session.cameraCapabilities` (`null` até o celular enviar), e `session.video` ganha `colorRange` e `colorMatrix`, como declarados pelo celular.

DataChannel `control`:
- Agente para o celular: `{"type": "quality_preset", "preset": "<chave>"}` quando o canal abre e a cada mudança.
- Celular para o agente (primeira vez que o celular envia mensagens): `{"type": "set_quality_preset", "preset": "<chave>"}` e `{"type": "camera_capabilities", "width": <max>, "height": <max>, "frameRate": <max>, "facingMode": "user" | "environment" | null, "codecs": ["video/H264", ...]}`. Mensagem desconhecida ou inválida é ignorada e registrada.
- Celular para o agente: `{"type": "color_sample", "colorSpace": "display-p3" | "srgb", "width": 160, "height": 90, "rgb": "<base64>", "capturedAt": <ms>}` (§1.1). Cabe no `max-message-size` de 65 536 do aiortc.

Status: `session.video.colorCalibration` com `state` (`measuring`, `applied`, `default`) e `deltaE` (ΔE2000 médio depois da correção, `null` até medir).

WebRTC: `maxBitrate` deixa de ser fixo em 10 000 000 e segue a opção.

## Textos

Chaves novas em `locales/en.json` e `locales/pt-BR.json` no mesmo commit, na branch de integração: nome e descrição curta de cada opção, rótulo do seletor e o aviso do terminal sem QR. A lista exata vai no handoff.

Calibração: `console.color_matched` ("Cor igual à do celular" / "Color matched to the phone") e `console.color_default` ("Cor padrão" / "Standard color"). A palavra "calibração" fica só no código e nos documentos, porque na tela sugere uma tarefa do usuário.

## Fora do escopo

- Resolução e fps à escolha do usuário, e a câmera anunciar outros formatos (v0.7.0).
- Avaliação de codecs mais eficientes que o H.264 (VP9, AV1, HEVC) (v0.7.0); esta versão só registra quais o celular oferece.
- Console definitivo, SSE e revisão de linguagem de todas as superfícies (v0.8.0).
- Guardar a escolha entre reinícios (persistência).
- Reconexão automática depois de queda longa (robustez).
- Falha de segurança achada no teste final (2026-11-06), existente desde a v0.3.0: o celular envia vídeo, e as capacidades, assim que conecta, e o agente recebe e decodifica os quadros antes do Confirmar; o portão só impede que cheguem à câmera. Um falso computador receberia o vídeo antes da comparação do código. Por decisão do usuário, a correção (confirmação nos dois lados, nada sai do celular antes) vai para a v0.8.0, registrada no planejamento §6.

## Critérios de aceitação

1. Faixa de cor: teste unitário confirma a tabela de normalização (0 vira 16, 255 vira 235, 128 de croma fica 128) e que quadro de faixa limitada passa sem mudança. Com um quadro real do iPhone em pouca luz, nenhum pixel que era acima de 0 na origem vira 16 ou menos na saída. O status mostra `colorRange` e `colorMatrix` declarados; o relatório registra os valores de cada aparelho testado (o iPhone do usuário, e um Android se houver um disponível).
2. A WCam declara faixa, matriz, primária e transferência; o relatório da vcam mostra a medição das barras de cor que escolheu a matriz.
3. O usuário compara lado a lado, no mesmo ambiente com pouca luz, a prévia do celular e a WCam no app Câmera do Windows, e aprova que sombras e cores estão no mesmo nível.
3.1. Calibração: em toda conexão do iPhone do usuário, `colorCalibration.state` chega a `applied` sem nenhuma ação dele, com `deltaE` abaixo de 2. Na verificação de ponta a ponta da vcam (§1.1), o que o Chrome mostra da câmera WCam fica com ΔE2000 médio abaixo de 2 contra as amostras do celular. Testes: o ajuste recupera uma curva e um ganho conhecidos a partir de amostras sintéticas; amostra com correlação baixa é descartada; sem 3 amostras válidas o estado é `default` e a saída é byte a byte a da v0.6.0 sem calibração; ao encerrar a sessão nada fica guardado e a conexão seguinte começa em `measuring`; `color_sample` antes do `live` é ignorado. O e2e com a câmera falsa do Chromium mede e aplica a calibração a cada conexão, e o SSIM continua acima de 0,98, medido contra a referência passada pela mesma tabela de cor aplicada (decisão 8).
3.2. Nenhum valor ligado a modelo, marca ou aparelho no código; conferido na revisão do orquestrador.
3.3. Comparação lado a lado (§6): com `WCAM_DEV_TOOLS=1`, um clique no console traz as duas imagens e o relatório em até 10 s, e as três baixam. Sem a variável, rotas `404`, mensagens ignoradas e nenhum botão. Testes: remontagem dos pedaços (inclusive pedaço faltando e tamanho errado), prazo de 10 s, limite de 5 comparações em memória, relatório com uma diferença conhecida entre duas imagens sintéticas, rota `404` sem a variável; e2e com a câmera falsa do Chromium e uma câmera WCam simulada, se o Chromium do compose não enxergar a WCam (registrar no relatório). Usado pelo usuário no iPhone antes de aprovar o CA 3.
4. Congelar: sem quadro novo, a câmera repete o último quadro bom por 3 s (tolerância de 0,2 s) e então mostra preto (Y=16, UV=128). Teste automatizado e verificação no Frame Server.
5. Recuperação: no teste de laboratório, com um pacote e o seu reenvio perdidos a 5 Mbit/s, o vídeo volta em até 1 s.
6. Registro: cada episódio gera uma linha em `episodes.log` com todos os campos; teste confirma que token, URL de pareamento e IP completo nunca aparecem no arquivo.
7. Reunião real de pelo menos 30 min no novo Teams com o iPhone na opção Máxima: nenhum preto visto pelo usuário; o `episodes.log` da reunião vai para o changelog.
8. Qualidade: mudar a opção no celular aparece no console, e no console aparece no celular, em menos de 300 ms; a taxa medida pelo agente acompanha a opção em até 5 s. Teste e2e com a câmera falsa do Chromium e verificação no iPhone.
9. Terminal: com a saída redirecionada, nenhuma URL com `#t=` é escrita; teste automatizado.
10. Medição: capacidades e codecs do iPhone do usuário e o benchmark de decodificação nesta máquina registrados nos relatórios.
11. O e2e de qualidade continua com SSIM de pelo menos 0,98; CI verde nos cinco jobs; versão 0.6.0 no agente, no web e no projeto .NET.
12. Contrato 0.6.0 e emenda do CA-2 no planejamento registrados antes do código.

## Decisões registradas

1. Aprovação do usuário em 2026-11-06, com a emenda do CA-2 (ajustar a faixa de cor, sem tocar em resolução nem matiz).
2. Opção de qualidade padrão: Equilibrada. Pode passar para Máxima se o CA 7 provar a Máxima no Wi-Fi do usuário; a mudança passa pelo usuário.
3. Congelamento de 3 s antes do preto.
4. Faixa e matriz são as declaradas pelo celular em cada quadro, nunca supostas pelo modelo do aparelho.
5. Calibração de cor automática a cada conexão (§1.1), aprovada pelo usuário em 2026-11-06, com nova redação da emenda do CA-2: a única transformação permitida é igualar a cor ao que o próprio celular exibe, medida automaticamente a cada conexão, sem tocar em resolução nem enquadramento.
6. O teste com aparelho real é só no iPhone do usuário (decisão dele, 2026-11-06). Outro aparelho é coberto pelo e2e com a câmera falsa do Chromium e pela ausência de valores por modelo no código (CA 3.2).
7. Nome: "calibração de cor" no código e nos documentos (`color_calibration`); na tela, só o resultado ("Cor igual à do celular").
8. O SSIM mede perda de detalhe na transmissão, não a correção de cor, que é intencional (emenda do CA-2). Com a calibração aplicada, a referência do SSIM passa pela mesma tabela de Y aplicada ao vídeo. No e2e com a referência y4m (BT.601, C420jpeg), antes desta decisão o SSIM era 0,985 em `measuring` e 0,973 contra a referência original depois do `applied`; o ΔE de cerca de 4,4 que sobra nesse arquivo é de matriz, fora do escopo, e o e2e não exige ΔE abaixo de 2 com ele, só com a câmera falsa padrão do Chromium.
9. Ferramenta de comparação lado a lado (§6) entra na v0.6.0, aprovada pelo usuário em 2026-11-07, porque é o instrumento de verificação do CA 3.

## Changelog
