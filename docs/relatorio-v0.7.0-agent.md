# Relatório v0.7.0, sessão agent

Branch: `feature/formato-agent`, PR para `feature/formato`. Spec: `docs/specs/spec-v0.7.0.md`; handoff: `docs/handoff-v0.7.0.md` (Sessão agent e adendos).

## Itens do handoff

| Item | Estado | Onde |
|---|---|---|
| 1. Spike `h264-levels` | Feito, tabela aceita (contrato, "Formato de vídeo") | branch local `spike/h264-levels-agent` |
| 2. Formato | Feito | `media/video_format.py`, `media/camera_format.py`, `sessions/manager.py`, `api/` |
| 3. Pipeline no tamanho do formato | Feito; 720p60 remedido com o iPhone (abaixo) | `media/pipeline.py` |
| 4. Retrato | Feito | `media/pipeline.py`, `media/episodes.py` |
| 5. Ctrl+C | Feito, teste com o processo real | `app.py`, `cli.py`, `tests/integration/test_shutdown.py` |
| 6. Modos da câmera | Feito | `sessions/phone_messages.py`, `api/schemas.py` |
| 7. Referência e SSIM | Feito: `make_reference --width --height --fps`; quadro de tamanho diferente da referência não é medido | `tools/make_reference.py`, `media/quality.py` |
| 8. Medição de codec com o iPhone | Feito, menos 720p30 (Pipeline, medição por estágio) | |
| 9. Versão 0.7.0 | Feito | `agent/pyproject.toml` |

## Formato (item 2)

- `PUT /api/video-format`: `204`; chave desconhecida ou fora de `available`: `422 invalid_request`. `PUT /api/quality-preset`, `qualityPreset`, `quality_preset` e `set_quality_preset` saíram.
- `videoFormat` no status: `selected` é a escolha; `camera` e `virtualCamera.output` vêm do formato anunciado pela câmera; `pending` vem de `WcamFormatGet`.
- `available` vem da última `camera_capabilities` (paisagem, tolerância de 0,5 fps); até a primeira, só `1080p30`. A escolha e `available` valem até o agente fechar. Capacidade nova sem o formato escolhido: passa ao maior oferecido.
- O celular segue o formato anunciado pela câmera (ADR 0013): `video_format` sai ao abrir o canal, a cada `camera_capabilities` e a cada mudança do anunciado (inclusive de `pending`), com o teto do REMB do formato anunciado. Durante a troca pendente, o celular fica no formato antigo.
- `set_video_format` só em `live`; fora de `available` é ignorado com log e o `video_format` atual é reenviado.
- `WcamFormatSet` roda no worker de quadros (fora do event loop e em série com o envio, sem corrida no buffer NV12 nem no OBS reaberto). `WcamFormatGet` é consultado a cada 150 ms por uma tarefa com dono, só quando o sink é a câmera nativa, cancelada no encerramento. DLL sem `WcamFormatSet` ou `WcamFormatGet` é falha da DLL nativa: `native_error` em `auto`, `unavailable` com `error` em `media_foundation` explícito.
- O sink falso simula a pendência (`S_FALSE` e aplicação depois) e o cancelamento ao pedir de novo o formato anunciado; os testes cobrem os dois caminhos.
- Sem câmera anunciando formato (OBS indisponível, por exemplo), `camera` e `output` mostram o escolhido, para o status manter o formato do contrato.

## Pipeline (item 3)

- A saída segue o formato anunciado: quadro de paisagem no tamanho anunciado vai sem conversão de tamanho; de outro tamanho não vai à câmera (repete o último bom e congela como na v0.6.0); o último quadro bom de um formato anterior não é reenviado depois da troca (preto até chegar quadro no tamanho novo). O ritmo do quadro de espera segue o fps anunciado.
- Tempo do worker por quadro neste PC (i5-8500), quadro sintético de ruído aleatório, mediana de 60 execuções; `deliver` inclui tabelas de cor e cópia, NV12 medido à parte:

| Caso | Cor | `deliver` mediana (p95) | `i420_to_nv12` | Orçamento |
|---|---|---|---|---|
| 720p60 paisagem | só faixa | 0,5 (0,6) ms | 0,3 ms | 16,7 ms |
| 720p60 paisagem | Apple | 2,4 (3,1) ms | 0,3 ms | 16,7 ms |
| 1080p30 paisagem | Apple | 5,3 (7,2) ms | 0,7 ms | 33,3 ms |
| 1440p30 paisagem | Apple | 9,3 (12,1) ms | 1,5 ms | 33,3 ms |
| 2160p30 paisagem | só faixa | 4,9 (6,0) ms | 3,1 ms | 33,3 ms |
| 2160p30 paisagem | Apple | 20,8 (31,2) ms | 3,0 ms | 33,3 ms |
| 2160p30 retrato 2160x3840 | Apple | 13,7 (20,2) ms | 3,5 ms | 33,3 ms |
| 1080p30 retrato 1080x1920 | Apple | 3,4 (4,2) ms | 0,8 ms | 33,3 ms |

- Cabe num worker só em todos os formatos da tabela final (2160p60 saiu). O pior caso, 2160p30 com a curva Apple, fica em cerca de 24 ms de mediana com o NV12; o ruído aleatório é o pior caso das tabelas (`bytes.translate`), imagem de câmera é mais rápida.
- Remedição com o iPhone na seção abaixo.

### Medição por estágio com o iPhone e a câmera nativa (10/11)

CSV `stages-20261110-195613.csv` (sonda fora do repositório, um registro por segundo; mediana dos segundos estáveis, sem os 10 s iniciais de cada trecho nem os pendentes). Tempos em ms por quadro; `accept` é `to_ndarray` mais tabelas de cor; `deliver` é `accept` mais `i420_to_nv12` mais `WcamFramePublish`.

| Formato | Segundos | Celular fps | Descartes/s | CPU processo | CPU sistema | decode | deliver mediana (p95) | accept | nv12 | publish | atraso do event loop |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 720p60 | 6 | 60 | 0 | 8% | 34% | 2,5 | 2,3 (4,0) | 1,7 | 0,4 | 0,2 | 11 |
| 1080p30 | 56 | 30 | 0 | 9% | 29% | 5,9 | 6,2 (7,3) | 4,8 | 1,0 | 0,3 | 14 |
| 1440p30 | 9 | 30 | 0 | 16% | 33% | 10,6 | 11,3 (12,9) | 8,3 | 1,9 | 0,7 | 10 |
| 2160p30 | 1122 em 3 trechos | 30 | 0 (p90 2 a 3) | 22% a 24% | 61% a 67% | 19 a 23,5 | 25,5 a 27,7 (34,8 a 37,7) | 19,5 a 20,7 | 3,8 a 4,4 | 1,7 a 2,1 | 20 |

- 720p60 entregou 60 fps sem descarte, mas com poucos segundos estáveis; o achado de 6 a 10 fps da rodada B não se repetiu. 720p30 não foi medido.
- 2160p30: a mediana do `deliver` cabe nos 33,3 ms; o p95 passa. O custo está no `accept` (cerca de 75% do `deliver`). Decomposição em 2160p com ruído (pior caso): `to_ndarray` 3,9 ms, tabela de luma 10,1 ms, tabela de croma 8,9 ms. `translate_in_place` copia o plano para `bytes`, traduz e copia de volta: três passagens sobre 12 MB, com o GIL preso.
- O p95 acompanha a disputa de CPU, não um estágio novo: correlação do p95 do `deliver` com o p95 do `accept` 0,89, com o p95 do decode 0,87, com a CPU do sistema 0,64. O decode do aiortc (20 a 23 ms em 2160p30) e as tabelas disputam núcleos com o sistema já em 65%; o atraso do event loop sobe de 10 a 14 ms para 20 ms de mediana (pico de 200 ms) porque `bytes.translate` não solta o GIL.
- Efeito visível: o celular segue em 30 fps de mediana; a fila de um quadro descarta 2 a 3 quadros/s no p90, repetindo o quadro anterior.
- Otimização possível dentro da spec, sem contrato nem dependência nova: traduzir direto dos planos do `VideoFrame` para o array de saída, sem `to_ndarray` e sem a cópia de ida e volta (`translate` direto do plano: 6,5 ms contra 10,1 ms na luma). Estimativa: `accept` de cerca de 20 para 13 ms e `deliver` de 27 para 20 ms de mediana em 2160p30, o que deixa folga para o p95 sob a mesma disputa. A medir antes de adotar: `numpy.take` com a tabela, que solta o GIL, contra `bytes.translate`; e gerar o NV12 no mesmo passo da tradução de croma (economiza os 4 ms do `i420_to_nv12`). Fica para decisão do orquestrador (PATCH ou item novo).

## Retrato (item 4)

- Quadro de retrato é reduzido por área (`sws_scale` com `AREA`, no YUV, sem RGB) para a altura do formato anunciado e centralizado com faixas Y=16, UV=128; as tabelas de cor valem só na imagem. 1080x1920 vira 608x1080 em 1920x1080 (coluna 656); em 1280x720, 404x720 na coluna 438. `framesScaled` conta só esses quadros; `session.video.orientation` é `landscape` ou `portrait`.
- A causa `portrait` saiu do `episodes.log` (`silence` ou `stalled`).

## Verificação

- `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` (strict): limpos.
- `uv run pytest`: 257 unitários e 52 de integração passando, 1 pulado (precisa de DLL do Windows fora do Windows). Portas 8080/8443 conferidas livres antes da integração.
- Não verificado: fluxo real com o iPhone e a câmera WCam nativa (formato, pendência, 720p60, retrato visto no app), DLL real com `WcamFormatGet`, e2e da sessão web contra esta branch. Fica para a rodada combinada com o orquestrador e o usuário.
