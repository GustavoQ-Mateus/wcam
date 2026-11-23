# Relatório v0.10.0, sessão agent

Branch: `feature/performance-agent`, PR para `feature/performance`. Spec: `docs/specs/spec-v0.10.0.md`, com as emendas de 2026-11-22 (NV12) e 2026-11-23 (CA 1 e CA 2). Handoff: `docs/handoff-v0.10.0.md` (Sessão agent). ADRs: 0018, 0019, 0020 e 0021.

Máquina de todas as medições: i5-8500 (6 núcleos), UHD 630 com driver 31.0.101.2141, iPhone com Safari, Meet no Chrome. CPU em % da máquina, salvo onde diz "de um núcleo".

## Itens do handoff

| Item | Estado | Onde |
|---|---|---|
| 1. Antes e spike (§1.6) | Feito; decidiu a ADR 0018 | scratchpad, números abaixo |
| 2. Decodificação na placa (§1.1) | Feito; no celular ao vivo ficou em software pela ADR 0019 | `decoding/`, `media/decode_timing.py`, `media/latency_limit.py` |
| 3. Tradução de cor (§1.2) | Feito, e depois em NV12 direto (emenda de 2026-11-22) | `media/plane_translation.py`, `media/pipeline.py` |
| 4. Vídeo como câmera (§1.5) | Feito; CA 8 da v0.9.0 em 4K cumprido | `video/`, `decoding/` |
| 5. Quedas de fps (§1.3) | Medido em reunião; ADR 0021 | `diagnostics/dev_console.py`, `api/events.py` |
| 6. Troca de formato (§1.4) | Medido; ADR 0020, sem mudança no `vcam` | tabela abaixo |
| 7. Limite do "Processamento p95" | `budgetMs` (33,3 ms em 30 fps), mandado à web | web |
| 8. Testes e versão | Feito; `version` 0.10.0 | `tests/`, `agent/pyproject.toml` |

## Critérios de aceitação

| CA | Resultado |
|---|---|
| 1 (emendado, ADR 0021) | Cumprido em 1080p30. Em 2160p30, melhor esforço: o p95 passa, mas sobram 3 quedas do PC em 15 min |
| 2 (emendado) | `IMG_0641.MOV`: 74% menor, cumprido. Celular em 2160p30: 11,6% menor, dado como cumprido por decisão do usuário |
| 3 | Cumprido: `off`, falha ao abrir e falha no meio do fluxo caem para software sem derrubar a sessão (testes com WebRTC real) |
| 4 | Cumprido: placa igual ao software byte a byte no vídeo de referência; e2e com SSIM verde |
| 5 | Causa explicada com números; as do PC corrigidas em 1080p30, em 4K ficam 3 (ADR 0021) |
| 6 | ADR 0020 com a medição por app |
| 7 | `decoder` no status e evento `decoder` no `/dev`; limite em `budgetMs` na web |
| 8 | Verificação completa e `npm run test:e2e` verdes (seção Verificação) |

## Spike (§1.6)

- `hwaccel` no PyAV 17.1 instalado: cuda, dxva2, qsv, d3d11va, d3d12va, amf. A UHD 630 decodifica H.264 CB e High, HEVC Main e Main 10 em d3d11va, dxva2, d3d12va e qsv.
- Igualdade byte a byte com o software em 300 de 300 quadros nos quatro caminhos.
- O bloqueio: com cópia da placa para a memória (d3d11va, dxva2, d3d12va), o PyAV chama `av_hwframe_transfer_data` sem soltar o GIL. Isso prende o event loop de 14 a 30 ms por quadro em 4K. Por isso a decodificação foi para um processo filho (ADR 0018).

Tempo por quadro e CPU (de um núcleo), H.264 CB 2160p30 como o celular manda:

| Caminho | Tempo | CPU | GIL |
|---|---|---|---|
| software (aiortc) | 14,4 ms | 42% | livre |
| dxva2 com cópia | 21,7 ms | 41% | preso ~14 ms |
| d3d11va com cópia | 31,6 ms | 27% | preso ~30 ms |
| qsv | 25 a 30 ms | 45% | livre |
| só decodificar, quadro fica na placa | 3,1 a 3,5 ms | ~1% | livre |

## Decodificação na placa (§1.1, ADR 0018) e celular em software (ADR 0019)

- `wcam/decoding`: um processo filho por fonte com dxva2. Os pacotes vão por `Pipe`, e os quadros voltam por `SharedMemory`, com 4 posições de 3840x2160. O filho repõe pts, `key_frame`, `color_range` e `colorspace`, que o PyAV perde na cópia.
- Encaixe pela troca de `aiortc.rtcrtpreceiver.get_decoder`, com verificação na partida. VP8 (só no e2e) vai para software com reason `unsupported`.
- Fallback ao abrir e no meio do fluxo (10 erros seguidos, filho morto ou 2 s sem resposta), sem derrubar a sessão.
  - O PLI sai pelo `RecoveringJitterBuffer` da sessão, que pede o quadro-chave no próximo pacote. A ADR previa chamar `_send_rtcp_pli` direto; o efeito é o mesmo, com menos acoplamento ao aiortc. O orquestrador aceitou.
  - Na reprodução, o software retoma do último quadro entregue.
- A etapa `transfer` mede a passagem para I420 no filho e a cópia entre processos. A cópia da placa fica dentro de `decode`, porque no PyAV ela acontece dentro da decodificação e não dá para medir à parte.
- HEVC Main 10 da biblioteca fica em software, para manter a igualdade de bytes.

Diagnóstico da fila com o celular em 4K na placa (2026-11-18):
- O usuário viu atraso de cerca de 2 s. O aiortc põe cada quadro numa fila sem limite antes do decodificador.
- Na placa, decode (~22 ms, já com a cópia) mais transfer (~15 ms) davam ~37 ms por quadro, acima dos 33,3 ms. A fila crescia sem parar, e o fps recebido oscilava de 12 a 40.
- A UHD 630 é dividida com o app que usa a câmera; o loopback do spike não pegou isso.
- Com `WCAM_HW_DECODE=off` o atraso sumiu: decode 13,3 ms de mediana, total p95 típico de 19,4 ms, e CPU de 26,7% contra ~38% na placa (29% do processo principal mais 9% do filho).

ADR 0019 (9732ffe):
- No `auto`, o celular ao vivo decodifica em software (reason `live_phone`), e o vídeo da biblioteca continua na placa. `on` força a placa e `off` força o software.
- Limite de atraso de 200 ms no decodificador do celular, nos dois caminhos.
  - Compara o relógio do RTP com o relógio real. Passou do limite: descarta até o próximo IDR e pede um quadro-chave uma vez.
  - Reancora no IDR, e a linha de base pode subir 1 ms/s.
- Teste: com decode de 40 ms por quadro a 30 fps por 20 s, a fila fica em no máximo 7 quadros; sem o limite, ela crescia sem parar.

Threads do decode: o aiortc usa `SLICE` com contagem automática. Medi `SLICE` contra `FRAME` com 2 e 3 threads, e o `SLICE` ganhou. `FRAME` ainda soma um quadro de atraso por thread, então nada mudou.

## Tradução de cor (§1.2) e NV12 direto (emenda de 2026-11-22)

Primeira versão (ec772c0):
- Filtro `lut` do FFmpeg mais `hflip`, num `av.filter.Graph` cujo push e pull soltam o GIL. O grafo é guardado enquanto o tamanho, o formato, as tabelas e o espelho não mudam.
- Antes (`bytes.translate` e numpy): 5,6 ms em 1080p e 21 ms em 4K, segurando o GIL.
- Depois: 0,65 ms e 3,3 ms. `np.take` foi descartado (6 vezes mais lento).

NV12 direto (42f3af1):
- O vcam já recebia NV12, e o sink convertia I420 para NV12 em numpy só para a DLL.
- Agora o grafo termina em `scale` com `in_range=full:out_range=full` e `format=nv12`, e o quadro interno do pipeline é NV12 do começo ao fim.
- O sink só copia. O preto, a câmera desligada, o vídeo da biblioteca e o retrato com faixas são montados em NV12.
- Faixa: sem o `scale` com a mesma faixa, o `format=nv12` deixava o `swscale` converter um yuv420p marcado como faixa cheia, e o retrato em yuvj420p saía diferente. Com a mesma faixa na entrada e na saída, ele só entrelaça.
- Teste: NV12 igual byte a byte ao caminho anterior (tradução, depois I420, depois NV12) no vídeo de referência, com tabela da Apple e espelho, além dos casos de faixa cheia, limitada, retrato e espelhado. Também há um teste de que o sink não converte.

Custo por quadro em 4K, sem disputa:

| Etapa | Mediana | p95 |
|---|---|---|
| Antes: cor 5,6 ms mais `i420_to_nv12` 3,0 ms | 8,7 ms | 12,0 ms |
| NV12 direto | 6,3 ms | 9,2 ms |
| NV12 direto com espelho | 8,9 ms | 11,7 ms |

O spike prometia 3,9 ms. A diferença de ~1,8 ms é a alocação a frio do quadro de 12 MB a cada quadro. Reaproveitar buffers ficou fora por decisão do orquestrador.

## Vídeo como câmera (§1.5)

`IMG_0641.MOV` com a câmera em 4K, 2 min, pipeline com câmera falsa, mesmo script nas duas versões (CPU de um núcleo):

| Versão | CPU | Quadros pulados |
|---|---|---|
| v0.9.0 | 198,9% | 0% |
| v0.10.0 em software | 195,1% | 0% |
| v0.10.0 na placa | 51,6% (74% menor) | 0,06% |

Na placa: decode 7,9/19,8 ms e transfer 5,2/6,2 ms (mediana/p95). Quando a placa falha, a troca para software não deixa buraco de quadros.

## CPU com o celular (CA 2, fase a)

1 min por formato, celular em 2160p30 com o app Câmera, 2026-11-18:

| Versão | CPU do WCam |
|---|---|
| v0.9.0 | 32,8% |
| v0.10.0 com a placa | 34,6% |
| v0.10.0 em software (o que vale pela ADR 0019) | 29,0% |

- Redução de 11,6%, longe dos 50%. O spike já mostrava o motivo: zerar a decodificação tira só ~7% da máquina.
- O usuário aceitou o CA 2 para o celular com esse número (emenda fb5a53e). A v0.10.0 entrega mais quadros que a v0.9.0 com essa CPU.

## Quedas de fps em reunião (§1.3, CA 1 e CA 5)

### Bug do `delivered.fps` desde a v0.8.0 (e8098a8 e ba4da86)

- Cada assinante de `/api/dev/events` chamava `DevConsole.metrics()` no seu ritmo. Esse método guarda o contador anterior de quadros e a janela das etapas num objeto único.
- Com o navegador e o coletor abertos juntos, quem chamava logo depois do outro recebia uma janela de milissegundos. Daí os 0 e 430 fps no CSV do usuário.
- O bug existe desde e56b56f (v0.8.0, primeiro commit do console de desenvolvedor), então a v0.9.0 também o tem.
- Correção (e8098a8): os envios de métricas ficam alinhados ao mesmo segundo do loop para todos os assinantes, e o `DevConsole` devolve a mesma leitura a quem pedir em menos de 0,5 s.
- Correção seguinte (ba4da86): a primeira leitura sai na hora da conexão, e o tick alinhado seguinte podia cair na janela de 0,5 s e reenviar o mesmo snapshot, com o mesmo `at`. O stream agora não reenvia um snapshot que já mandou.
- As comparações de antes e depois deste relatório usam o JSONL do meu coletor, que pegava a janela cheia. Conferi o `delivered.fps` contra a contagem de quadros:
  - reunião de 2026-11-22: bateu em 900 de 901 segundos;
  - fases da v0.9.0 e da v0.10.0: bateu em todos os segundos;
  - reunião de 2026-11-23, já com a correção: média de 28,89 fps pelo campo contra 28,90 pela contagem.

### Reuniões de 15 min no Meet

Duração reduzida de 30 para 15 min por decisão do usuário. A contagem começa sozinha com o celular ao vivo, o formato certo e o Meet recebendo. Decodificação software/`live_phone` em todas. Uma queda conta quando o fps entregue fica abaixo de 25 por mais de 1 s.

| Reunião | Segundos | p95 / p99 por quadro | fps entregue | Segundos abaixo de 25 | Quedas (do PC) | CPU do WCam |
|---|---|---|---|---|---|---|
| 2160p30, 2026-11-22, I420 | 897 | 53,4 / 95,4 ms | 27,5 | 149 | 20 (16) | 29,2% |
| 2160p30, 2026-11-23, NV12 | 896 | 30,5 / 55,7 ms | 28,9 | 82 | 22 (3) | 37,1% |
| 1080p30, 2026-11-23, NV12 | 297 | 11,5 / 21,9 ms | 29,7 | 7 | 2 (0) | 25,7% |

Etapas, mediana/p95 em ms:

| Reunião | decode | color | deliver | total |
|---|---|---|---|---|
| 2160p30 NV12 | 17,8 / 81,7 | 10,2 / 46,0 | 2,6 / 17,2 | 14,4 / 73,2 |
| 1080p30 NV12 | 8,4 / 48,1 | 2,7 / 17,9 | 0,6 / 8,0 | 4,2 / 27,3 |

- Nas três reuniões, o celular enviou de 29,6 a 30,1 fps com `qualityLimitationReason` `none` o tempo todo.
- Em 2160p30 com NV12: 555 pacotes perdidos, jitter de 12 ms, ida e volta de 26 ms, bitrate até ~34 Mbit/s (teto de 35).
- A CPU maior na reunião com NV12 acompanha mais quadros entregues e bitrate mais alto; não é comparação no mesmo conteúdo.

Classificação das quedas:
- Celular: fps enviado abaixo de 25 ou limitação diferente de `none`.
- Rede: perda ou fps recebido abaixo de 25 com o celular mandando 30.
- PC: quadros chegando e não sendo entregues.

As 3 quedas do PC em 2160p30 com NV12:

| Horário (UTC) | Recebidos | Entregues | O que aconteceu |
|---|---|---|---|
| 12:55:33 a 35 | 25 a 30 fps | até 1,4 fps | decode p95 658 ms, total p95 687 ms |
| 13:03:52 a 53 | 28 fps | 0 | nenhum quadro decodificado no segundo |
| 13:04:28 a 29 | 25 a 30 fps | 21 a 22 fps | total p95 de 69 a 94 ms |

Nas três, a CPU do WCam cai para 17 a 20%. Não é o WCam saturado: é a decodificação travando com a máquina disputada.

As duas quedas em 1080p30 não são do PC:
- 13:10:27: recebidos 18,9 fps, total p95 de 9 ms;
- 13:10:41: recebidos 11 fps, com perda, total p95 de 15 ms.

### Causa (CA 5)

É disputa de CPU com o próprio Meet: o Chrome recebe e recodifica 4K nos mesmos 6 núcleos.
- Na reunião de 2026-11-22, comparei os 395 segundos lentos (total p95 acima de 33,3 ms) com os 501 normais:
  - todas as etapas ficam mais lentas juntas: decode 31,9 contra 19,0 ms, cor 28,2 contra 14,0, entrega 22,6 contra 11,5;
  - a CPU do WCam cai ao mesmo tempo, 26,0% contra 30,6%.
  - Se o gargalo fosse uma etapa nossa, só ela cresceria e a nossa CPU subiria. Com tudo mais lento e a CPU mais baixa, é o WCam esperando processador.
- Sem o Meet, em 4K software, 35% dos segundos passavam de 33,3 ms; com o Meet, 44%.
- O bitrate aperta o decode, mas não é ele que derruba o CA 1. Por faixa de bitrate:

| Bitrate | Segundos | decode mediana / p95 | Segundos com total p95 acima de 33,3 ms | CPU do WCam |
|---|---|---|---|---|
| 0 a 5 Mbit/s | 519 | 11,9 / 20,6 ms | 297 (57%) | 26,7% |
| 5 a 15 | 142 | 12,7 / 18,6 | 44 (31%) | 28,8% |
| 15 a 25 | 22 | 21,6 / 31,2 | 8 (36%) | 32,7% |
| 25 a 35 | 213 | 29,0 / 39,1 | 46 (22%) | 39,3% |

Causas das quedas da v0.8.0 e o que foi feito:

| Causa | Correção |
|---|---|
| Tradução de cor segurando o GIL ~20 ms por quadro em 4K, o que tirava do event loop a folga para escoar as rajadas de RTP. No loopback, uma cópia de 12 MB sob GIL levava a perda de pacotes, PLI em ciclo e 1 a 8 fps; sem GIL, 30 fps sem perdas | Grafo do FFmpeg sem GIL (§1.2) |
| Fila sem limite antes do decodificador | Limite de 200 ms (ADR 0019) |
| Cor mais conversão para NV12 em série | NV12 direto |
| Disputa de CPU com o app da reunião em 4K | Resolvida em 1080p30; em 4K, melhor esforço (ADR 0021) |

Comparação em 2160p30 com o app Câmera, pela contagem de quadros:

| Versão | Segundos abaixo de 25 | Quedas |
|---|---|---|
| v0.9.0 | 39 | 7 |
| v0.10.0 com a placa | 78 | 24 |
| v0.10.0 com `off` | 31 | 7 |

### Outros achados

- Tela preta de 7,7 s (2026-11-18, 1080p): o celular quase parou de enviar, com 13 pedidos de quadro-chave. O WCam seguiu a regra da v0.6.0: congela até 3 s, depois mostra o preto. Congelar por mais tempo pede decisão nova de spec; o código não mudou.
- Coletores encerrados com código 4 em 2026-11-22: os dois caíram junto com o WCam de teste por falta de energia, antes da reunião. Nenhum dado de reunião se perdeu; a reunião foi refeita em 2026-11-23.

## Troca de formato com o app aberto (§1.4, ADR 0020)

Padrão de teste, uma troca a cada 5 s, 2026-11-22.
- "Reinício" é o stop, `set_format` e start da câmera.
- "Voltou" é quanto a contagem de apps da DLL levou para ficar acima de 0.
- "0,00 s" quer dizer que a contagem nunca zerou.

| App | Troca | Reinício | Voltou | Relato do usuário |
|---|---|---|---|---|
| Meet (Chrome) | para 2160p30 | 0,32 s | 0,00 s | |
| Meet (Chrome) | para 1080p30 | 6,15 s | não em 20 s | câmera indisponível depois de alguns segundos |
| Meet (Chrome) | para 2160p30 | 0,27 s | 0,00 s | |
| Meet (Chrome) | para 1080p30 | 0,50 s | 5,58 s | |
| Teams | para 2160p30 | 0,30 s | 0,00 s | |
| Teams | para 1080p30 | 0,61 s | não em 20 s | não pareceu ficar indisponível |
| Teams | para 2160p30 | 0,31 s | 0,00 s | |
| Teams | para 1080p30 | 0,60 s | 5,95 s | |
| app Câmera | para 2160p30 | 0,29 s | 0,00 s | fica indisponível |
| app Câmera | para 1080p30 | 0,60 s | 5,74 s | |
| app Câmera | para 2160p30 | 5,37 s | 0,00 s | |
| app Câmera | para 1080p30 | 0,14 s | 0,00 s | |

- A troca não é imediata em nenhum dos três apps.
- Pela ADR 0020, o formato continua pendente até o app reabrir a câmera, sem mudança no `vcam`.
- Zoom, Discord e OBS não entraram na medição.

## Limite do "Processamento p95"

- Proposto e aprovado: atenção quando o p95 passa de `budgetMs`, o tempo de um quadro (33,3 ms em 30 fps).
- O limite anterior, de 50% do orçamento, deixava o indicador em atenção em 83 a 98% dos segundos em 4K.
- Mandado ao web0.10.0, que aplicou.

## Verificação

- Agent: `ruff check`, `ruff format --check` e `pyright` strict limpos; `pytest` com 571 passando e 1 pulado. O pulado é a igualdade da placa sem placa de vídeo; aqui, na UHD 630, os testes de placa rodaram de verdade.
- `npm run test:e2e`, com esta branch mais `feature/performance-web` num worktree temporário, no Docker, sem portas no host, em e61aeb8 (ba4da86 mais a web em f9f5291): 33 de 33 passando. SSIM 0,984 (mínimo 0,9835) em 1080p com a prévia ligada, e o `/dev` exportando o CSV.
- Fluxo real com o celular e a câmera virtual: o Meet nas reuniões acima e o app Câmera e o Teams no teste de troca de formato.

## Não verificado

- `pyvirtualcam` em NV12 com o backend do OBS (Windows usa a câmera nativa; o OBS é alternativa).
- Spawn do processo filho dentro do executável do PyInstaller. Foi testado a partir de um zipapp, que é como o `wcam.exe` do uv roda.
- Zoom, Discord e OBS na troca de formato.
- SSIM em 4K com teto de bitrate menor (o teto de 18 Mbit/s ficou fora).
