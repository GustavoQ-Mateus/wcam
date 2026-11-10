# Relatório v0.7.0, sessão agent

Branch: `feature/formato-agent`, PR para `feature/formato`. Spec: `docs/specs/spec-v0.7.0.md`; handoff: `docs/handoff-v0.7.0.md` (Sessão agent e adendos).

## Itens do handoff

| Item | Estado | Onde |
|---|---|---|
| 1. Spike `h264-levels` | Feito, tabela aceita (contrato, "Formato de vídeo") | branch local `spike/h264-levels-agent` |
| 2. Formato | Feito | `media/video_format.py`, `media/camera_format.py`, `sessions/manager.py`, `api/` |
| 3. Pipeline no tamanho do formato | Feito; remedição do 720p60 com o iPhone pendente (abaixo) | `media/pipeline.py` |
| 4. Retrato | Feito | `media/pipeline.py`, `media/episodes.py` |
| 5. Ctrl+C | Feito, teste com o processo real | `app.py`, `cli.py`, `tests/integration/test_shutdown.py` |
| 6. Modos da câmera | Feito | `sessions/phone_messages.py`, `api/schemas.py` |
| 7. Referência e SSIM | Feito: `make_reference --width --height --fps`; quadro de tamanho diferente da referência não é medido | `tools/make_reference.py`, `media/quality.py` |
| 8. Medição de codec com o iPhone | Pendente, com o usuário | |
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
- Pendente, com o iPhone e combinado com o orquestrador: remedir o achado do 720p60 (6 a 10 quadros/s na rodada B) com a câmera anunciada a 60 fps, por estágio (`WcamFramePublish`, `i420_to_nv12`, tabelas) e com a contenção do GIL. Pelos números acima, nenhum estágio do worker explica a queda sozinho.

## Retrato (item 4)

- Quadro de retrato é reduzido por área (`sws_scale` com `AREA`, no YUV, sem RGB) para a altura do formato anunciado e centralizado com faixas Y=16, UV=128; as tabelas de cor valem só na imagem. 1080x1920 vira 608x1080 em 1920x1080 (coluna 656); em 1280x720, 404x720 na coluna 438. `framesScaled` conta só esses quadros; `session.video.orientation` é `landscape` ou `portrait`.
- A causa `portrait` saiu do `episodes.log` (`silence` ou `stalled`).

## Verificação

- `uv run ruff check`, `uv run ruff format --check`, `uv run pyright` (strict): limpos.
- `uv run pytest`: 257 unitários e 52 de integração passando, 1 pulado (precisa de DLL do Windows fora do Windows). Portas 8080/8443 conferidas livres antes da integração.
- Não verificado: fluxo real com o iPhone e a câmera WCam nativa (formato, pendência, 720p60, retrato visto no app), DLL real com `WcamFormatGet`, e2e da sessão web contra esta branch. Fica para a rodada combinada com o orquestrador e o usuário.
