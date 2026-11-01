# Spec v0.4.0, Câmera virtual

Status: Draft
Branch de integração: `feature/camera-virtual`
Sessões: `agent` (principal) e `web` (console e e2e), em paralelo
Referências: `docs/planejamento.md` §1 (CA-1, CA-2), §4 (fluxo, passo 5), §8 (riscos); ADRs 0002 e 0005

## Objetivo

Os quadros que passam pelo portão vão para a câmera virtual, e o WCam vira webcam de verdade: Meet, Teams, Zoom e os outros apps do CA-1 passam a ver a imagem do celular. É o MVP do produto.

Esta versão também mede a qualidade do CA-2 de ponta a ponta: um teste automático compara a imagem que entra no celular com a que sai na câmera virtual, e o teste no celular real roda 10 minutos em 1080p.

## Pré-requisito no PC

OBS Studio instalado, com o driver "OBS Virtual Camera" registrado no Windows. Conferido em 2026-11-01 na máquina do usuário: o CLSID `{A3FCE0F5-3493-419F-958A-ABA1250EC20B}` está registrado em 64 e 32 bits. O OBS não precisa estar aberto e não pode estar com a câmera virtual dele ligada ao mesmo tempo.

Limitação conhecida (ADR 0005): o nome que os apps mostram é "OBS Virtual Camera", não "WCam". O nome próprio só vem com a câmera nativa Media Foundation.

## Contrato

O orquestrador atualiza `docs/contrato.md` na aprovação.

### `GET /api/status` ganha

```json
{
  "virtualCamera": {
    "state": "active",
    "backend": "obs",
    "reason": null,
    "output": {"width": 1920, "height": 1080, "fps": 30},
    "source": "phone"
  },
  "session": {
    "video": {"width": 1920, "height": 1080, "fps": 30.0, "bitrateKbps": 9800, "codec": "H264", "framesScaled": 0}
  },
  "process": {"cpuPercent": 12.5},
  "quality": null
}
```

- `virtualCamera.state`: `active` ou `unavailable`. `reason` (só com `unavailable`): `driver_missing`, `device_in_use` ou `error`.
- `backend`: `obs` ou `fake`.
- `source`: `phone` quando os quadros vêm do celular; `placeholder` em qualquer outro momento.
- `session.video.codec`: o codec negociado (`H264` ou `VP8`). `framesScaled`: quantos quadros precisaram ser redimensionados na sessão (o esperado é 0; ver "Formato de saída").
- `process.cpuPercent`: uso de CPU do processo do agente, média da última janela de 1 s, via psutil.
- `quality`: só existe com `WCAM_QUALITY_REFERENCE` definido (desenvolvimento e e2e); fora disso é sempre `null`. Ver "Qualidade".

### Variáveis de ambiente novas

| Variável | Padrão | Uso |
|---|---|---|
| `WCAM_VIRTUAL_CAMERA` | `auto` | `auto` (Windows usa `obs`, o resto usa `fake`), `obs` ou `fake` |
| `WCAM_QUALITY_REFERENCE` | vazio | caminho de um arquivo `.y4m` de referência; liga a medição de SSIM |

## Formato de saída

- A câmera virtual abre uma vez, ao iniciar o agente, em 1920x1080 a 30 fps, e fica aberta enquanto o agente estiver ativo.
- Caminho normal, sem perda evitável (CA-2): o quadro decodificado em YUV 4:2:0 vai para o sink em I420, sem redimensionar e sem passar por RGB. O pyvirtualcam reorganiza os planos de I420 para NV12 para o driver do OBS; isso é uma troca de layout, não uma conversão de cor.
- Quadro em paisagem com outro tamanho (o navegador baixou a resolução, por exemplo): é redimensionado para caber em 1920x1080, mantendo a proporção e com bordas pretas se a proporção for outra, e conta em `framesScaled`. O relatório e o console mostram isso como degradação.
- Quadro em retrato: não vai para a câmera; a saída mostra o quadro de espera.
- Conversão de quadro sempre fora do event loop, em um único worker para manter a ordem.

## Quadros de espera

Quando não há quadro do celular para mostrar (sem sessão, aguardando confirmação, celular em retrato, mais de 1 s sem quadro numa sessão `live`), a câmera virtual recebe um quadro de espera, no ritmo de 30 fps.

Nesta versão o quadro de espera é preto puro, sem texto: é o que os apps já mostram com a câmera desligada, não exige fonte nem dependência de desenho, e nunca congela a reunião numa imagem parada. Quadros com texto ("Aguardando celular", "Sem sinal") ficam para depois, se o usuário quiser (ver "Decisões em aberto").

## Qualidade (CA-2)

Medição automática:
- Com `WCAM_QUALITY_REFERENCE` definido, o agente lê o arquivo `.y4m` de referência (1920x1080, um quadro estático de alto detalhe) e compara cada quadro entregue ao sink com ele: SSIM no plano Y, janela de 8x8, implementado com numpy. Os quadros dos primeiros 3 s da sessão `live` são ignorados, enquanto o codificador estabiliza.
- `quality` no status: `{"ssim": <média>, "minimum": <menor>, "frames": <quantos>}`.
- O arquivo de referência é gerado por um script do agente (`python -m wcam.tools.make_reference <saida.y4m>`), deterministicamente, com padrão de alto detalhe (texto fino, linhas de 1 px, gradientes, ruído). Ele não é commitado.
- No e2e, o Chromium recebe a referência como câmera falsa (`--use-file-for-fake-video-capture`), faz o fluxo completo até `live`, e o teste confere `quality.ssim >= 0.98` depois de pelo menos 30 quadros medidos.

Medição real: ver CA 4 e 5.

## Escopo da sessão agent

- `virtualcam/sink.py`: `Protocol` `VirtualCameraSink` (abrir com tamanho e fps, enviar quadro I420, fechar, estado).
- `virtualcam/pyvirtualcam_sink.py`: implementação com pyvirtualcam, backend OBS, formato I420. Falha ao abrir vira `unavailable` com o motivo, e o agente continua funcionando sem câmera virtual (o terminal e o status explicam).
- `virtualcam/fake_sink.py`: guarda contagem, último quadro e, com referência, alimenta a medição de qualidade. É o sink do compose e dos testes.
- `media/pipeline.py`: liga o portão ao sink; escolhe entre quadro do celular e quadro de espera; aplica a regra de formato; conta `framesScaled`.
- `media/placeholder.py`: quadro preto I420 de 1920x1080.
- `media/quality.py`: SSIM puro com numpy e leitura do `.y4m`.
- `tools/make_reference.py`: gerador do `.y4m` de referência.
- `codec` e `cpuPercent` no status.
- `docker-compose.yml`: `WCAM_VIRTUAL_CAMERA=fake` no `agent`; o serviço `e2e` recebe o arquivo de referência gerado no `agent` (volume compartilhado ou passo de geração; a escolha é da sessão, registrada no relatório) e o agente recebe `WCAM_QUALITY_REFERENCE`.
- Dependências novas: `pyvirtualcam` (câmera virtual, ADR 0005) e `numpy` (quadros para o pyvirtualcam e SSIM).
- Versão 0.4.0.

Testes do agente:
- `test_phone_frame_reaches_sink_unchanged_when_size_matches` (bytes do quadro I420 iguais na entrada e no sink)
- `test_landscape_frame_with_other_size_is_scaled_and_counted`
- `test_portrait_frame_is_replaced_by_placeholder`
- `test_sink_receives_placeholder_without_session`
- `test_sink_receives_placeholder_while_awaiting_confirmation`
- `test_sink_receives_placeholder_after_one_second_without_frames`
- `test_unavailable_driver_keeps_agent_running_and_reports_reason`
- `test_ssim_of_identical_frames_is_one`
- `test_ssim_drops_with_noise`
- `test_reference_generator_is_deterministic`
- integração aiortc com aiortc até o sink falso, com o quadro chegando em 1920x1080 I420.

## Escopo da sessão web

- Console provisório: linha da câmera virtual (ativa ou indisponível, com o motivo traduzido), origem (celular ou espera), codec, CPU do agente e aviso quando `framesScaled > 0`. Textos novos em `locales/`, adicionados pelo orquestrador.
- e2e no compose: o fluxo completo agora confere `virtualCamera.source` passando de `placeholder` a `phone` depois do Confirmar, e de volta a `placeholder` depois de Desconectar.
- e2e de qualidade com a referência como câmera falsa, conferindo `quality.ssim >= 0.98`.
- Versão 0.4.0.

## Textos

| Chave | en | pt-BR |
|---|---|---|
| `console.virtual_camera_active` | Virtual camera on | Câmera virtual ligada |
| `console.virtual_camera_unavailable` | Virtual camera unavailable | Câmera virtual indisponível |
| `console.virtual_camera_driver_missing` | Install OBS Studio to get the virtual camera. | Instale o OBS Studio para ter a câmera virtual. |
| `console.virtual_camera_device_in_use` | Turn off the OBS virtual camera and restart WCam. | Desligue a câmera virtual do OBS e reinicie o WCam. |
| `console.virtual_camera_error` | The virtual camera failed to start. | A câmera virtual não iniciou. |
| `console.source_phone` | Showing the phone | Mostrando o celular |
| `console.source_placeholder` | Showing a black frame | Mostrando quadro preto |
| `console.frames_scaled` | {count} frames had to be resized. Check the Wi-Fi. | {count} quadros precisaram ser redimensionados. Confira o Wi-Fi. |
| `console.cpu` | Agent CPU {percent}% | CPU do agente {percent}% |
| `terminal.virtual_camera_active` | Virtual camera: OBS Virtual Camera, 1920 × 1080 at 30 fps | Câmera virtual: OBS Virtual Camera, 1920 × 1080 a 30 fps |
| `terminal.virtual_camera_unavailable` | Virtual camera unavailable: {reason} | Câmera virtual indisponível: {reason} |

## Fora do escopo

Quadros de espera com texto, espelhar a saída, pausa, troca de câmera pelo PC (v0.5.0), câmera nativa Media Foundation, áudio.

## Critérios de aceitação

1. CA-1 completo, testado pelo usuário no Windows com o celular em `live`: a câmera "OBS Virtual Camera" aparece e mostra a imagem do celular no Google Meet (Chrome e Edge), no Microsoft Teams (app e web), no Zoom (app), no Discord (app), no OBS Studio (fonte "Dispositivo de captura de vídeo") e num site com `getUserMedia`. App não instalado fica registrado como não testado. Registrar também o app Câmera do Windows (o esperado é não aparecer; ADR 0005).
2. Sem sessão, aguardando confirmação ou com o celular em retrato, os apps mostram quadro preto, nunca uma imagem congelada.
3. Teste automático: SSIM médio de pelo menos 0,98 entre a referência e o que chega ao sink, no e2e do compose.
4. Teste real de 10 minutos em `live`, em paisagem: `video` mostra 1920x1080 do começo ao fim, fps médio de pelo menos 29, `framesScaled` igual a 0. Registrar aparelho, navegador, codec, bitrate médio e CPU média do agente (meta informativa do planejamento: até 20%).
5. Caminho sem perda evitável: teste automático confirma que o quadro do celular com o tamanho de saída chega ao sink com os mesmos bytes I420.
6. Driver ausente ou ocupado: o agente sobe, o terminal e o console dizem o motivo, e o resto (pareamento, sessão) funciona.
7. Depois de Desconectar, a câmera volta ao quadro preto em menos de 1 s.
8. Verificação completa dos dois lados, CI e CodeQL verdes, versão 0.4.0 nos dois lados, contrato e textos atualizados.

## Decisões em aberto para o usuário

1. Quadro de espera preto (proposta, sem dependência nova) ou com texto curto como "WCam: aguardando celular" (exige desenhar texto: Pillow e um arquivo de fonte)?
2. Quais apps do CA-1 você tem instalados para o teste.
