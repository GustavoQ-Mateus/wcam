# Spec v0.6.0, Fidelidade de imagem

Status: Aprovada (2026-11-06)
Branch de integração: `feature/qualidade`
Sessões: `agent`, `web`, `vcam`
Referências: `docs/planejamento.md` §1 (CA-2), §5.4; ADRs 0011 e 0012; changelog da v0.5.0 (diagnóstico da faixa de cor); diagnóstico da reunião de 2026-11-04 (imagem preta por alguns segundos)

## Objetivo

A imagem da câmera "WCam" no PC tem que estar no mesmo nível da prévia no celular. Esta versão corrige o que hoje a deixa pior, sem mudar o formato da câmera (continua 1920x1080 a 30 fps):

1. **Faixa de cor.** O Safari do iPhone envia faixa cheia (0 a 255), e a WCam é lida como faixa limitada (16 a 235). Sombras viram preto e altas luzes viram branco.
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
- Isso emenda o CA-2 do produto ("sem converter cor"): a única transformação permitida é ajustar a faixa ao formato anunciado pela câmera, sem tocar em resolução nem matiz. O planejamento §1 registra a emenda.

Vcam:
- O tipo de mídia passa a declarar `MF_MT_VIDEO_NOMINAL_RANGE` (16 a 235) e a matriz de cor, a primária e a função de transferência, hoje omitidas.
- A matriz anunciada (BT.709 ou BT.601) é escolhida por medição, não suposta: o probe publica barras de cor de valores conhecidos, e o relatório compara o RGB lido no Chrome e no app Câmera com o esperado para cada matriz. Como o iPhone não declara a matriz, a mesma medição é feita com um quadro real dele contra a prévia.

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

## Contrato (`docs/contrato.md` vai para 0.6.0)

Console:
- `PUT /api/quality-preset` com `{"preset": "maximum" | "balanced" | "light"}`: `204`; `422 invalid_request` com valor desconhecido. Vale para a sessão atual e as próximas.
- `GET /api/status` ganha `qualityPreset` no primeiro nível (sempre presente), `virtualCamera.source` ganha o valor `frozen`, `session.cameraCapabilities` (`null` até o celular enviar), e `session.video` ganha `colorRange` e `colorMatrix`, como declarados pelo celular.

DataChannel `control`:
- Agente para o celular: `{"type": "quality_preset", "preset": "<chave>"}` quando o canal abre e a cada mudança.
- Celular para o agente (primeira vez que o celular envia mensagens): `{"type": "set_quality_preset", "preset": "<chave>"}` e `{"type": "camera_capabilities", "width": <max>, "height": <max>, "frameRate": <max>, "facingMode": "user" | "environment" | null, "codecs": ["video/H264", ...]}`. Mensagem desconhecida ou inválida é ignorada e registrada.

WebRTC: `maxBitrate` deixa de ser fixo em 10 000 000 e segue a opção.

## Textos

Chaves novas em `locales/en.json` e `locales/pt-BR.json` no mesmo commit, na branch de integração: nome e descrição curta de cada opção, rótulo do seletor e o aviso do terminal sem QR. A lista exata vai no handoff.

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

## Changelog
