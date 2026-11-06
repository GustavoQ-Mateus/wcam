# Relatório v0.6.0, sessão agent

De: sessão `agent`
Para: orquestrador (`wcam-ae`)
Spec: `docs/specs/spec-v0.6.0.md` (Aprovada)
Contrato: `docs/contrato.md` (0.6.0, com `ca1bc24` e `66a142b`, já mesclados)
Branch: `feature/qualidade-agent`

## 1. O que foi feito

### Opção de qualidade e mensagens do celular (handoff 5 e 6)
- `media/quality_preset.py`: `QualityPreset` (`maximum`, `balanced`, `light`) com a taxa máxima de cada uma (20, 10 e 5 Mbit/s). Padrão `balanced`.
- `SessionManager` guarda a opção só em memória. `set_quality_preset` limita a taxa do peer e envia `quality_preset` ao celular. Quando o canal abre, o agente envia `session_state` e logo depois `quality_preset`. Toda sessão nova começa com a taxa da opção em uso.
- `PUT /api/quality-preset` responde `204`, ou `422 invalid_request` com uma chave desconhecida. `qualityPreset` aparece no primeiro nível do status. `session.cameraCapabilities` é `null` até a primeira mensagem do celular.
- O agente passou a ler o DataChannel (`sessions/phone_messages.py`, Pydantic em modo estrito com união discriminada por `type`):
  - `set_quality_preset` só vale com a sessão `live`; antes disso, é ignorado com log e sem eco;
  - `camera_capabilities` vale em qualquer estado e fica em `session.cameraCapabilities`;
  - qualquer outra mensagem é ignorada com um aviso no log, que não reproduz o conteúdo, e a sessão continua.
- Teto do REMB: `CappedRateControl`, subclasse do `AimdRateControl` do aiortc, entra no lugar do `rate_control` do estimador. Ele começa no teto, volta ao teto a cada mudança de opção e nunca anuncia mais que o teto. Substitui o `PHONE_MAX_BITRATE_BPS` fixo. Antes, o REMB começava em 10 Mbit/s e podia crescer sem limite.

### Faixa de cor (handoff 1)
- `media/color_range.py` lê a declaração de cada quadro: faixa cheia é `yuvj420p` ou `color_range` JPEG; faixa limitada é `color_range` MPEG; o resto é não declarada. A matriz vem de `colorspace`: `bt709`; `bt601` para `bt470bg` e `smpte170m`; outro nome do FFmpeg; ou `unspecified`.
- Faixa cheia passa por tabela: Y vira `16 + Y × 219 / 255` e U, V viram `128 + (C − 128) × 224 / 255`, arredondados ao inteiro mais próximo (nenhum valor cai exatamente em ,5, então o modo de arredondamento não muda nada). Faixa limitada e não declarada passam byte a byte.
- A extração dos planos não deixa o swscale mexer na faixa: no caminho com letterbox, o `reformat` recebe `src_color_range` igual a `dst_color_range`. Antes, um `yuvj420p` reformatado era convertido de faixa implicitamente pelo swscale.
- `session.video.colorRange` e `colorMatrix` aparecem no status.
- Desempenho, a pedido do orquestrador. O tempo do worker por quadro 1080p `yuvj420p` real (extração, tabela e NV12; mínimo de 5 × 40) caiu de 11,6 a 12,0 ms para 6,4 ms. A tabela, que custava 11,1 ms com indexação do numpy, agora usa `bytes.translate` direto no array do quadro: cerca de 4,5 ms, sem dependência nova. Variantes descartadas: `np.take` com `out=` (21,6 ms) e aritmética em `uint16` (13,3 ms só no plano Y).

### Congelar (handoff 2)
- Sem quadro novo, o último quadro bom é publicado a cada tick, a 30 fps, por até 3 s. Depois disso, vem o preto (Y=16, UV=128). Antes, o preto vinha em 1 s.
- `virtualCamera.source` passa a `frozen` depois de 0,5 s sem quadro novo. Antes disso é o intervalo normal entre quadros, e o source continua `phone`. Quadro em retrato vai direto para o preto, como antes.

### Recuperação e teste de laboratório (handoff 3)
- Teste de laboratório (`tests/integration/test_stall_recovery.py`):
  - um cliente aiortc envia H.264 1080p30 pré-codificado pelo PyAV, porque o codificador do aiortc trava em 3 Mbit/s;
  - o clipe é codificado a 4,1 Mbit/s, o que dá cerca de 4,9 Mbit/s de carga útil no fio, e o teste confere 5 Mbit/s ± 10%;
  - o cliente responde ao PLI voltando ao IDR;
  - um filtro no `_send_rtp` do cliente descarta um pacote e o reenvio RTX dele;
  - o teste mede o maior intervalo entre quadros que chegam ao pipeline.
- A trava: o `_remove_frame` do aiortc para no primeiro slot vazio, então nenhum quadro sai até o buffer de 2048 pacotes encher e o próprio aiortc descartar o trecho.
- Mecanismo (`media/recovering_jitter_buffer.py`): subclasse do `JitterBuffer` do aiortc, instalada no lugar do buffer de 2048 pacotes.
  - Com pacotes chegando e nenhum quadro saindo por mais de 500 ms, ela pula até o início do primeiro quadro inteiro depois do buraco e devolve `pli_flag`. Com isso, o próprio aiortc envia o PLI.
  - Depois disso, os quadros decodificados só voltam à câmera a partir do primeiro `key_frame`, para não mostrar imagem corrompida. Enquanto o quadro-chave não chega, o PLI se repete a cada 500 ms.
  - O buffer também conta os bytes de carga útil, os PLIs e as travas, que o registro de episódios usa.

| Laboratório, 5 rodadas cada | Maior intervalo sem quadro | Taxa no fio | Travas detectadas | PLI |
|---|---|---|---|---|
| Antes (buffer de 2048, sem recuperação) | 3,86 a 3,92 s | 4,87 a 4,92 Mbit/s | 0 | 1 (do aiortc, ao encher o buffer) |
| Depois | 0,57 a 0,60 s | 4,87 a 4,91 Mbit/s | 1 | 1 |

### Registro de episódios (handoff 4)
- `media/episodes.py`: `EpisodeTracker` puro. O peer o alimenta a cada 100 ms numa tarefa própria, criada no Confirmar e cancelada no `close`, que também fecha um episódio que ainda esteja aberto. Cada amostra traz:
  - a idade do último quadro bom (paisagem);
  - se o último quadro veio em retrato;
  - se a saída está em preto;
  - os contadores do buffer.
- Uma linha JSON por episódio de mais de 500 ms, em `<WCAM_DATA_DIR>/logs/episodes.log`, com `RotatingFileHandler` (1 MB, um arquivo antigo). O logger `wcam.episodes` não propaga para o resto do log.
- Campos:
  - `startedAt` e `endedAt`, em UTC com milissegundos;
  - `durationMs`;
  - `cause`: `portrait` se houve retrato, `stalled` se o buffer detectou trava durante o episódio, senão `silence`;
  - `action`: `black` se a saída chegou ao preto, senão `frozen`;
  - `rtpBytes`;
  - `pliSent`.
- Exemplo do laboratório: `{"startedAt": "...Z", "endedAt": "...Z", "durationMs": 590, "cause": "stalled", "action": "frozen", "rtpBytes": ..., "pliSent": 1}`.

### QR fora de arquivo (handoff 7)
- `cli.announce_pairing`: com a saída num terminal interativo (`isatty`), abre a janela de pareamento e mostra o QR. Senão, nem gera token: escreve `terminal.scan_in_console` com a URL do console e a dica de parar. Antes, o QR (e o token dentro dele) ia para o arquivo quando a saída era redirecionada.

### Benchmark (handoff 8)
`python -m wcam.tools.decode_benchmark` usa `tools/synthetic_h264.py`, que também serve aos testes. Ele decodifica 2 s de H.264 sintético a 20 Mbit/s (a taxa da Máxima), com `libx264` `ultrafast` e `zerolatency`, sem B-frames, como no WebRTC. O decodificador é um `CodecContext("h264")` com os padrões, igual ao do aiortc. A CPU é medida por `cpu_times` do processo, relativa à duração do vídeo.

Esta máquina: Intel Core i5-8500 a 3,0 GHz, 6 núcleos.

| Formato | fps | Decodificação (ms/quadro, tempo de parede) | CPU de um núcleo | CPU da máquina |
|---|---|---|---|---|
| 1280x720 | 30 | 1,5 | 11% | 1,8% |
| 1280x720 | 60 | 1,0 | 12% | 2,1% |
| 1920x1080 | 30 | 1,5 | 16% | 2,6% |
| 1920x1080 | 60 | 1,6 | 23% | 3,9% |
| 2560x1440 | 30 | 2,2 | 18% | 3,0% |
| 2560x1440 | 60 | 2,2 | 34% | 5,6% |
| 3840x2160 | 30 | 6,3 | 34% | 5,7% |
| 3840x2160 | 60 | 5,4 | 74% | 12,4% |

O tempo de parede por quadro fica abaixo do tempo de CPU por quadro porque o FFmpeg decodifica em várias threads. Para a v0.7.0, o custo que cresce com o formato é o do worker: extração, tabela de faixa e NV12, cerca de 6,4 ms em 1080p. Em 4K a área é 4 vezes maior, o que daria cerca de 26 ms por quadro, perto do orçamento de 16,7 ms a 60 fps num worker só. Isso é estimativa, não medição.

### Calibração de cor (adendo de 2026-11-06)
- `color_sample` é validado pelo contrato: `colorSpace` `display-p3` ou `srgb`, `width` e `height` positivos, e `rgb` em base64 com exatamente `width × height × 3` bytes. Fora disso, a mensagem é ignorada com o log de mensagem fora do contrato. Antes do `live`, é ignorada com log próprio. `camera_capabilities` (enviada a cada troca de câmera) recomeça a medição.
- Anel dos últimos 60 quadros (2 s), reduzidos a 320x180 e normalizados pela faixa declarada. Fica ativo só enquanto faltam amostras: até 5 amostras da medição atual ou 30 s sem amostra.
- Cada amostra é comparada 0,7 s depois de chegar, porque a mensagem chega antes do quadro correspondente. O quadro escolhido é o de maior correlação de luminância, com e sem espelho; abaixo de 0,8, a amostra é descartada.
- Ajuste, com pelo menos 3 amostras válidas e repetido a cada amostra nova até a quinta: curva de tom monotônica de 9 pontos no Y e um ganho de saturação no U e V.
  - O ponto de partida vem da mediana por faixa de luminância e de mínimos quadrados no croma. Depois vem uma busca por coordenadas que minimiza o ΔE2000 médio.
  - O ΔE é medido entre a amostra (no espaço de cor dela) e a saída corrigida lida como BT.709 limitada e exibida em sRGB, que é como o Windows mostra a câmera.
  - Só aplica se o ΔE cair; senão, fica `default` com o ΔE medido. Com menos de 3 amostras válidas em 5, também fica `default`, com `deltaE` nulo.
  - O ajuste roda num executor próprio (`wcam-color`), fora do event loop e do worker de quadros.
- Aplicação: uma tabela de 256 entradas para o Y e outra para o U e V, já compostas com a tabela de faixa, no mesmo `translate` de antes. Sem calibração, a tabela é a de faixa da v0.6.0, byte a byte (teste), e faixa limitada continua sem tradução.
- `session.video.colorCalibration` no status. Tudo recomeça em `measuring` ao iniciar e ao encerrar a conexão e a cada troca de câmera; nada vai para o disco.
- `WCAM_COLOR_TRACE_DIR` (só desenvolvimento), no formato combinado com a vcam:
  - um `color-sample-<n>.json` por amostra aceita em `live`: campos da mensagem, `receivedAt`, `calibrationState`, `correlation`, `mirrored`, `colorRange` e `matchedFrame` com Y, U e V no tamanho da amostra, em códigos decodificados antes de qualquer tabela;
  - `color-calibration.json` ao fechar, com `rangeTables` e `appliedTables`.
- Números:
  - Laboratório de ponta a ponta (pareamento real, vídeo codificado pelo aiortc, 5 `color_sample` com curva e saturação conhecidas, duas conexões seguidas): ΔE2000 de 4,08 sem correção e 0,17 depois, contra 0,16 da correção verdadeira, nas duas conexões. Correlação de 0,988. Cada conexão começa em `measuring`.
  - Amostras do iPhone medidas no spike (10 amostras, 18:56): com 3 amostras, o ajuste leva o ΔE2000 de 2,49 a 1,21, o limite do modelo de curva e saturação, em cerca de 1 s no executor.
  - Custo por quadro no worker, num quadro real do iPhone: 4,69 ms só com a faixa, 4,75 ms com a calibração aplicada. Durante a medição, o anel acrescenta cerca de 6 ms por quadro, por cerca de 6 s por conexão.

### Versão
0.6.0 no `pyproject.toml` e no `uv.lock`; `wcam --version` confirma 0.6.0.

Commits:
- `63d92b3`: opção de qualidade e mensagens do celular;
- `cec1f29`: faixa de cor;
- `795488f`: congelar;
- `f910247`: recuperação e laboratório;
- `8ff80db`: teste do congelado a cada tick;
- `350b6b7`: episódios;
- `fd425d5`: QR;
- `735a5e8`: desempenho da tabela;
- `c4dc0f3`: versão;
- `3716148`: benchmark;
- `3e09bca`: merge de `origin/feature/qualidade`.

## 2. Critérios de aceitação

| CA | Estado | Evidência |
|---|---|---|
| 1 | Parcial (agent) | Testes de unidade: a tabela leva 0 a 16 e 255 a 235, e o croma 128 fica 128 (0 vira 16, 255 vira 240). Todo Y acima de 0 sai acima de 16. Faixa limitada e não declarada saem byte a byte iguais. Faixa cheia com letterbox é convertida uma vez só. Um quadro codificado em `yuvj420p` pelo libx264 e decodificado pelo `h264` sai `yuvj420p`, `color_range` 2, matriz não declarada (o mesmo perfil medido no iPhone) e é reconhecido como faixa cheia. `colorRange` e `colorMatrix` aparecem no status (teste com WebRTC real). Faltam o quadro real do iPhone em pouca luz e os valores declarados por cada aparelho. |
| 3.1 | Parcial (agent) | Testes: o ajuste recupera curva e saturação conhecidas (erro abaixo de 0,03 em cada ponto, ΔE abaixo de 1); amostra de outra cena é descartada; sem 3 amostras válidas o estado é `default` e a saída é a tabela de faixa byte a byte; ao recomeçar, nada fica guardado; `color_sample` antes do `live` é ignorado; o trace grava o formato combinado. No laboratório, as duas conexões chegam a `applied` com ΔE2000 de 0,17. Faltam o iPhone do usuário (ΔE abaixo de 2 em toda conexão), o e2e da web e a verificação da vcam. |
| 3.2 | Para revisão | Nenhum valor por modelo, marca ou aparelho no código do agente. A correção só depende das amostras da conexão. |
| 4 | Parcial (agent) | Teste com relógio controlado: congelado em 2,8 s, preto (Y=16, UV=128) em 3,2 s, e o mesmo quadro enviado ao sink em cada tick a 30 fps durante todo o intervalo. Falta a verificação no Frame Server, que depende da DLL nova da vcam. |
| 5 | Verificado | Laboratório a 4,9 Mbit/s com um pacote e o reenvio perdidos: o vídeo volta em 0,57 a 0,60 s (antes, 3,86 a 3,92 s). O teste falha acima de 1 s. |
| 6 | Verificado (agent) | No laboratório, a trava gera uma linha `stalled`/`frozen` com `pliSent` de pelo menos 1 e `rtpBytes` maior que 0. O teste confere que o arquivo não contém o IP do emissor, `#t=` nem `https://`. Testes de unidade cobrem os campos, as causas, as ações, o fim da sessão e uma linha por episódio no arquivo. |
| 8 | Parcial (agent) | O lado do agente está coberto. Teste com DataChannel real: `set_quality_preset` do celular gera eco, e o `PUT` do console chega ao celular como `quality_preset`. O teto do REMB por opção foi verificado nas três opções (o primeiro REMB fica em pelo menos 90% do teto, e nenhum passa dele). O e2e de menos de 300 ms e da taxa em até 5 s é da web. |
| 9 | Verificado | Com a saída redirecionada, sai só a orientação do console e nenhum `#t=`, e a janela de pareamento nem é aberta (teste). |
| 10 | Parcial (agent) | O benchmark desta máquina está acima. As capacidades e os codecs do iPhone dependem da web e do usuário. |
| 11 (agent) | Parcial | Em `agent/`, no estado final com o merge: `ruff check` e `ruff format --check` limpos, `pyright` com 0 erros, `pytest` com 215 passed e 1 skipped (o teste da DLL real, opcional). Versão 0.6.0. CI não verificado. |

## 3. Decisões e pontos para registrar

1. Já confirmados por você e registrados no contrato: o `set_quality_preset` do celular só vale em `live` (`ca1bc24`), e o `frozen` só aparece depois de 0,5 s (`66a142b`).
2. `rtpBytes` é a carga útil RTP que chega ao buffer de recepção (inclui reenvios, sem cabeçalhos RTP nem SRTP). É o que o agente vê sem chamar `getStats` a cada amostra.
3. Causa do episódio: `stalled` quando o buffer detectou trava durante o episódio. Uma falta de sinal no Wi-Fi seguida de uma rajada com buraco sai como `stalled`, porque a trava é o que segurou a imagem no fim.
4. Se o primeiro quadro depois do Confirmar demorar mais de 0,5 s, isso conta como episódio `silence`. No uso real o vídeo já está chegando antes do Confirmar, então o primeiro quadro vem em menos de um tick.
5. Mexidas em partes internas do aiortc 1.15:
   - continua o atributo privado do buffer de recepção, já usado desde a v0.4.0;
   - o buffer novo usa os membros protegidos `_origin`, `_packets` e `_remove_frame` do `JitterBuffer`;
   - o teto do REMB troca o atributo público `rate_control` do estimador.
   Testes que quebram se o aiortc mudar: `test_aiortc_buffer_alone_still_stalls_on_a_lost_packet` (laboratório) e `test_plain_aiortc_buffer_stays_stalled_on_the_same_packets` (unidade). Os testes de unidade do buffer novo e do REMB por opção também quebram se esses membros mudarem.
6. `tools/synthetic_h264.py` tipa o PyAV com `Protocol`, porque os stubs do PyAV 17 deixam `Packet` sem parâmetro e o pyright estrito rejeita qualquer chamada a `encode` e `decode`.
7. Matriz: ainda nenhum aparelho real declarou uma matriz diferente da anunciada pela WCam. Isso fica para o teste com o iPhone.
8. Calibração:
   - O laboratório só passa com folga se as amostras começarem depois que o codificador do aiortc estabiliza, cerca de 3 s depois do `live`. Com amostras logo no `live`, o ajuste continua igual à correção verdadeira, mas o ΔE fica entre 1,5 e 2,0, por causa da perda de compressão do começo e não do ajuste. No iPhone, com as amostras desde o `live`, a medição do spike deu 1,21. Se o iPhone mostrar o mesmo efeito, a web pode esperar cerca de 2 s depois do `live` antes da primeira amostra; isso é decisão sua.
   - Se a primeira amostra chegar com o anel vazio (por exemplo, quando o celular passa de retrato para paisagem depois de 30 s), ela é registrada e não conta; as quatro seguintes bastam.
   - Custo do `bytes.translate`: com dados aleatórios uniformes, uma tabela de croma com muitos pontos fixos (saturação perto de 1) fica até 4 vezes mais lenta, por erro de previsão de desvio na CPU. Em imagem de câmera o custo é igual ao da tabela de faixa (medido acima).

## 4. Dependências

Nenhuma nova. Pydantic, numpy, PyAV, psutil e aiortc já estavam no projeto, e o `bytes.translate` é da biblioteca padrão.

## 5. Pendências

1. Com o usuário, combinado por você:
   - o quadro real do iPhone em pouca luz e o `colorRange`/`colorMatrix` declarados (CA 1);
   - a verificação do congelar no Frame Server, com a DLL nova (CA 4);
   - 10 min na Máxima sem episódio no Wi-Fi dele (spec §3);
   - reunião de 30 min no novo Teams, com o `episodes.log` guardado (CA 7);
   - capacidades do iPhone (CA 10).
   - calibração no iPhone: ΔE2000 antes e depois em cada conexão, com troca de câmera (CA 3.1).
2. CI na integração.
