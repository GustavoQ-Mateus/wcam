# Spec v0.7.0, Resolução e fps

Status: Draft
Branch de integração: `feature/formato`
Sessões: `agent`, `web`, `vcam`
Referências: `docs/planejamento.md` §1 (CA-2), §6 (roteiro da 0.7.0); ADRs 0011 e 0012; spec v0.6.0 §5 e changelog (capacidades do iPhone, benchmark de decodificação, achados)

## Objetivo

Hoje a câmera WCam tem um formato só, 1920x1080 a 30 fps, e o seletor de qualidade da v0.6.0 muda só a taxa de dados, sem diferença visível para o usuário. Esta versão:

1. **Formato à escolha do usuário.** O usuário escolhe resolução e fps no celular ou no console, entre os que o celular entrega, e a câmera WCam passa a anunciar esse formato. A taxa de dados acompanha o formato, sem escolha separada. O seletor da v0.6.0 sai.
2. **Celular em pé.** Em retrato, a câmera mostra a imagem inteira no centro com faixas pretas dos lados, em vez de preto.
3. **Codec.** Mede se o H.264 sustenta os formatos novos com qualidade, CPU no PC e aquecimento do celular aceitáveis. Codec novo só numa spec futura, se os números pedirem.
4. **Exposição, balanço de branco, luz e sombra automáticos.** Garante que a câmera do celular trabalha no modo automático contínuo e mede o que ainda separa a imagem da WCam da câmera do próprio celular.
5. **Encerramento.** Ctrl+C no terminal encerra sem rastro de erro.

## 0. Spikes antes do código

Cada sessão roda o seu spike numa branch `spike/<nome>` e registra os números no relatório antes de implementar as seções que dependem dele. O resultado do spike não muda esta spec: ele só decide quais formatos da tabela da §1 entram e qual dos dois comportamentos da §1.3 vale. Qualquer outra surpresa volta ao orquestrador.

- **`spike/h264-levels` (agent e web, iPhone do usuário):** para cada formato da §1, o Safari entrega a captura no tamanho e fps pedidos (`getSettings()` depois de `applyConstraints`), o codificador H.264 do Safari envia esse formato pelo WebRTC para o aiortc, e o agente decodifica no fps pedido. O aiortc responde com `profile-level-id` de nível 3.1, que limita o tamanho que o celular pode enviar; o spike mede se o celular respeita esse nível e, se respeitar, qual ajuste na resposta SDP libera os níveis 4.2 (1080p60), 5.1 (1440p60 e 2160p30) e 5.2 (2160p60). Mede também a taxa real de cada formato em 2 min de cena com movimento, para confirmar a tabela da §1.
- **`spike/vcam-format` (vcam):** o Frame Server aceita uma media source que anuncia um formato decidido pelo processo do agente no momento em que o app abre a câmera, e entrega 1280x720, 2560x1440 e 3840x2160 a 30 e 60 fps no Chrome e no app Câmera. Se o formato mudar enquanto um app está com a câmera aberta, testar o evento de mudança de formato do Media Foundation (`MEStreamFormatChanged` ou equivalente) no Chrome, no app Câmera, no Teams e no OBS. Registrar também se o agente consegue saber, sem escrita da media source no canal, que um app está com a câmera aberta e em qual formato.

## 1. Formato à escolha do usuário

Decisão do usuário (2026-11-10): o usuário escolhe o formato no seletor, e a WCam anuncia só o formato escolhido. Os apps de reunião (Meet, Teams, Zoom) reduzem o que recebem para o que enviam na chamada; o formato maior serve a apps como o OBS e às gravações.

| Formato | Chave | Taxa máxima |
|---|---|---|
| 1280x720, 30 fps | `720p30` | 5 Mbit/s |
| 1280x720, 60 fps | `720p60` | 8 Mbit/s |
| 1920x1080, 30 fps (padrão) | `1080p30` | 10 Mbit/s |
| 1920x1080, 60 fps | `1080p60` | 16 Mbit/s |
| 2560x1440, 30 fps | `1440p30` | 18 Mbit/s |
| 2560x1440, 60 fps | `1440p60` | 28 Mbit/s |
| 3840x2160, 30 fps | `2160p30` | 35 Mbit/s |
| 3840x2160, 60 fps | `2160p60` | 50 Mbit/s |

- As taxas são valores iniciais. O spike `h264-levels` confirma cada uma; formato que não funcionar de ponta a ponta no iPhone do usuário e neste PC (i5-8500) sai da tabela, registrado no relatório e no changelog. Se funciona neste PC, a suposição é que funciona na maioria dos PCs; o console mostra o fps real na área de detalhes para quem tiver um PC mais fraco escolher um formato menor.
- Formatos oferecidos: os da tabela que cabem nas capacidades da câmera em uso (`camera_capabilities`: largura, altura e fps máximos). Até a primeira `camera_capabilities`, só o padrão.
- A escolha vale até o agente fechar, como a opção de qualidade da v0.6.0; guardar entre reinícios é da persistência (v0.9.0).

### 1.1 Celular (web)

- Aplica o formato com `applyConstraints` na faixa em uso (largura, altura e fps exatos) e a taxa em `maxBitrate` com `setParameters`, sem renegociar. `degradationPreference` continua `maintain-resolution`.
- Trocar de câmera mantém o formato; se a câmera nova não entregar o formato, o celular avisa o agente pelas capacidades novas, e o agente volta ao maior formato oferecido que caiba nelas.
- O seletor aparece só em `live`, como hoje, no lugar do seletor de qualidade.

### 1.2 Agent

- Guarda o formato escolhido, aplica o teto da estimativa de banda (REMB) da taxa do formato e avisa o celular e a câmera.
- A resposta SDP declara o nível H.264 que permite o maior formato oferecido, conforme o spike.
- O pipeline aceita o tamanho do formato escolhido em vez do 1920x1080 fixo. Quadro de paisagem em tamanho diferente do formato anunciado (por exemplo, durante a troca) não vai para a câmera: a câmera repete o último quadro bom, como no congelamento da v0.6.0, e conta `framesScaled` só nos quadros de retrato (§2).
- A conversão para NV12 e as tabelas de cor rodam fora do event loop, como hoje. Em 2160p60 o orçamento por quadro é 16,7 ms, e a estimativa do relatório da v0.6.0 é 26 ms num worker só; o relatório mede, e se não couber, o agente processa quadros em mais de um worker mantendo a ordem.

### 1.3 Vcam

- O canal `WCamFrames` (ADR 0012) passa a levar largura, altura e fps no cabeçalho, e as três posições têm tamanho para o maior formato (3840x2160 NV12, cerca de 12,4 MB cada). A API C ganha `WcamFormatSet(width, height, fps)`; `WcamFramePublish` aceita só o tamanho do formato atual.
- A media source anuncia um tipo de mídia só, o formato atual do canal no momento em que o app abre a câmera. Os quadros "aguardando", "congelado" e "sem sinal" saem nesse formato.
- Mudança de formato com um app usando a câmera, conforme o spike:
  - se os apps do CA-1 aceitarem a mudança de formato do Media Foundation, a troca é imediata;
  - senão, o app continua no formato antigo até reabrir a câmera; enquanto isso, o agente mantém o celular no formato antigo, o console mostra que o novo formato entra quando o app reabrir a câmera (`console.format_pending`), e a troca acontece sozinha quando nenhum app estiver usando a câmera.
- ADR nova (0013) registra o formato no canal e o comportamento escolhido, refinando a ADR 0012.

### 1.4 Console e desenho do seletor

O painel de qualidade da v0.6.0 foi achado "feio" pelo usuário e é refeito. O seletor tem duas escolhas (resolução e fps), não oito botões; formatos fora das capacidades da câmera não aparecem. Na mensagem principal, só o nome do formato (por exemplo, "1080p, 30 fps"); taxa, fps medido e codec ficam na área de detalhes. A sessão web registra em `docs/design-v0.7.0.md` a direção dada por `impeccable shape` e a revisão de `emil-design-eng`, e no celular as regras de `mobile-native` (controle na zona do polegar, uma mão).

## 2. Celular em pé

Decisão do usuário (2026-11-10): em retrato, a câmera mostra a imagem inteira com faixas laterais, em vez de preto.

- Agent: quadro de retrato (altura maior que largura) é reduzido para a altura do formato anunciado, mantendo a proporção, e centralizado com faixas pretas (Y=16, UV=128) dos lados. Por exemplo, 1080x1920 vira 608x1080 dentro de 1920x1080. Redução por área no YUV (`libyuv` via PyAV ou `sws_scale` com filtro de área), sem passar por RGB, fora do event loop, com as mesmas tabelas de cor. `framesScaled` conta esses quadros.
- `episodes.log`: a causa `portrait` deixa de existir, porque retrato não é mais episódio sem imagem.
- Web: o `/cam` deixa de bloquear "Ao vivo" em retrato e de pedir para girar. Em retrato, uma dica discreta (`cam.portrait_hint`) diz que deitar o celular aproveita a tela inteira do computador. Ao girar, a página aplica de novo o formato com largura e altura trocadas.
- É a única redução de tamanho permitida, e só em retrato. Emenda do CA-2 no planejamento (§6 desta spec).

## 3. Codec

Decisão do usuário (2026-11-10): só medir o H.264 nesta versão. O iPhone oferece H.265, VP9 e AV1, mas o aiortc só recebe H.264 e VP8, e um codec novo exige implementar a recepção.

Medição, registrada nos relatórios e na ADR 0014:
- Qualidade: SSIM no e2e com a referência em cada formato oferecido (o gerador `make_reference` ganha largura e altura), mínimo 0,98.
- CPU do agente neste PC em cada formato, com o iPhone, por 2 min.
- Aquecimento do celular: 10 min em 2160p60 (ou o maior formato que sobrar), com o fps médio medido pelo agente (queda de fps é o sinal de que o celular reduziu o desempenho por calor) e o relato do usuário sobre o aparelho.
- A ADR 0014 registra a decisão com os números: H.264 fica, ou uma spec futura implementa outro codec e por quê.

## 4. Exposição, balanço de branco, luz e sombra automáticos

Pedido do usuário (2026-11-10): exposição, balanço de branco, luz e sombra automáticos, para a imagem ficar igual à da câmera do celular, sem nenhum ajuste dele.

O que já é automático: a câmera do celular ajusta exposição, balanço de branco e foco sozinha antes de codificar o vídeo, e o PC recebe esses mesmos pixels (spike de 2026-11-08: ganho 0,995 em Y e PSNR de 37 a 38 dB entre o quadro cru da câmera e o decodificado no PC). A v0.6.0 já iguala a curva de exibição (luz e sombra) pela configuração de cor declarada. O que não chega a nenhuma página web é o processamento próprio do app Câmera do iPhone (HDR inteligente, Estilos Fotográficos, Deep Fusion), aplicado só nas fotos e vídeos do app nativo; o app nativo foi descartado pelo usuário em 2026-11-08. Calcular um ajuste a partir da imagem no PC também foi descartado (decisão 10 da v0.6.0).

Web:
- O `/cam` lê `getCapabilities()` e `getSettings()` da faixa em uso e, quando o navegador expõe, pede `exposureMode`, `whiteBalanceMode` e `focusMode` `continuous`. Nenhum controle manual na tela.
- `camera_capabilities` ganha `modes`: os três modos em uso (`getSettings()`), cada um `null` quando o navegador não informa.

Medição, com o usuário: na mesma cena, com a luz do quarto acesa e apagada, comparar a prévia do `/cam`, o app Câmera do iPhone e a WCam no PC. O relatório registra os modos informados pelo Safari e o que o usuário viu. Se a diferença que sobrar for do processamento do app Câmera nativo, ela fica registrada como limite do navegador, sem correção nesta versão.

## 5. Encerramento

Ctrl+C no terminal imprime hoje um rastro de `KeyboardInterrupt` que sai do `asyncio.run` (`cli.py`) em vez de `terminal.stopped`, embora o encerramento termine. Agent: Ctrl+C encerra os servidores, a sessão e a câmera e imprime só `terminal.stopped`, com código de saída 0. Existe desde antes da v0.6.0; achado em 2026-11-10.

## 6. Planejamento

Antes do código, o orquestrador emenda o CA-2 em `docs/planejamento.md` §1: a câmera virtual entrega a mesma resolução e fps da captura, no formato escolhido pelo usuário, sem redimensionar e com a única transformação de cor da emenda da v0.6.0; a única redução de tamanho permitida é a do celular em retrato, com faixas laterais. A linha "Captura em paisagem" vira a regra do retrato da §2.

## Contrato (`docs/contrato.md` vai para 0.7.0)

Sai, incompatível com a 0.6.0: `PUT /api/quality-preset`, `qualityPreset` no status, `quality_preset` e `set_quality_preset` no DataChannel, e a tabela "Opção de qualidade".

Console:
- `PUT /api/video-format` com `{"format": "<chave>"}`: `204`; `422 invalid_request` com chave desconhecida ou fora dos formatos oferecidos.
- `GET /api/status` ganha `videoFormat` no primeiro nível, sempre presente: `{"selected": "1080p30", "available": ["720p30", "720p60", "1080p30"], "camera": "1080p30", "pending": false}`. `camera` é o formato que a WCam anuncia agora; `pending` é `true` quando `selected` espera um app reabrir a câmera (§1.3). `virtualCamera.output` segue o formato anunciado.
- `session.video.orientation`: `landscape` ou `portrait`.

DataChannel `control`:
- Agente para o celular: `{"type": "video_format", "format": "<chave>", "width", "height", "fps", "maxBitrate", "available": [...]}` quando o canal abre, a cada mudança e a cada `camera_capabilities`.
- Celular para o agente: `{"type": "set_video_format", "format": "<chave>"}`, só em `live`, como o `set_quality_preset` de hoje; o agente aplica e responde com `video_format`.
- `camera_capabilities` ganha `"modes": {"exposureMode", "whiteBalanceMode", "focusMode"}`, cada um com o valor de `getSettings()` ou `null`.

`episodes.log`: `cause` passa a `silence` ou `stalled`.

## Textos

Chaves novas em `locales/en.json` e `locales/pt-BR.json` no mesmo commit, na branch de integração: rótulos do seletor de resolução e de fps, nome de cada formato, `console.format_pending` e `cam.portrait_hint`. Saem as chaves das opções de qualidade. A lista exata vai no handoff. Sem "agente", "sessão" ou nomes de protocolo (§5.7 do planejamento).

## Fora do escopo

- Codec novo (H.265, VP9, AV1), salvo spec futura pela ADR 0014.
- Controles manuais de câmera.
- Escolha do formato pelo app (a WCam anunciar vários formatos e o app escolher); descartada pelo usuário em 2026-11-10 em favor da escolha no seletor.
- Proporção diferente de 16:9.
- Falha de segurança e revisão de linguagem (v0.8.0); guardar a escolha (v0.9.0).

## Critérios de aceitação

1. Spikes registrados nos relatórios antes do código das seções que dependem deles, com a tabela da §1 final e o comportamento da §1.3 escolhido.
2. Formato: cada formato que fica na tabela funciona de ponta a ponta com o iPhone do usuário neste PC: a câmera WCam entrega o tamanho e o fps anunciados no Chrome e no app Câmera, com fps medido de pelo menos 95% do nominal por 2 min e `framesScaled` 0 em paisagem.
3. Seleção: mudar o formato no celular aparece no console, e no console aparece no celular, em menos de 300 ms; o tamanho que chega ao agente acompanha a escolha em até 3 s. Formatos fora das capacidades da câmera não aparecem nem são aceitos (`422`). Teste e2e com a câmera falsa do Chromium e verificação no iPhone.
4. Troca com app aberto: o comportamento da §1.3 escolhido pelo spike, verificado no Chrome, no app Câmera, no Teams e no OBS; nenhum quadro de tamanho errado chega a um app.
5. Retrato: com o celular em pé, a câmera mostra a imagem inteira centralizada com faixas pretas (Y=16, UV=128), sem preto da tela inteira; teste do pipeline com um quadro sintético de retrato confere posição e faixas; verificado no iPhone. Ao deitar o celular, volta ao formato inteiro sem reconectar.
6. Codec: ADR 0014 com SSIM, CPU e aquecimento de cada formato.
7. Exposição e balanço de branco: o relatório registra os modos informados pelo Safari e o resultado da comparação com o usuário (§4); nenhum controle manual na tela.
8. Encerramento: teste automatizado de Ctrl+C sem rastro de erro, com `terminal.stopped` e código de saída 0.
9. Desenho: `docs/design-v0.7.0.md` com as skills que guiaram o seletor; aprovação visual do usuário no console e no celular.
10. O e2e continua com SSIM de pelo menos 0,98 em 1080p30 e em cada formato oferecido ao e2e; CI verde nos cinco jobs; versão 0.7.0 no agente, no web e no projeto .NET.
11. Contrato 0.7.0, emenda do CA-2 e ADR 0013 registrados antes do código.

## Decisões registradas

1. Formato escolhido pelo usuário no seletor do celular e do console; a WCam anuncia só o formato escolhido (usuário, 2026-11-10).
2. Taxa de dados derivada do formato; o seletor de Máxima, Equilibrada e Leve sai.
3. Celular em pé com faixas laterais, única redução de tamanho permitida (usuário, 2026-11-10).
4. Codec: só medição do H.264 nesta versão (usuário, 2026-11-10).
5. Exposição, balanço de branco e foco automáticos pela própria câmera do celular, no modo contínuo, sem ajuste calculado pela imagem nem controle manual (usuário, 2026-11-10).
