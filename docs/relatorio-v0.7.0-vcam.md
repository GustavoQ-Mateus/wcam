# Relatório v0.7.0, sessão vcam

Status: em andamento (spike e código prontos; falta a verificação no Frame Server com a DLL final)
Branch: `feature/formato-vcam` (spike em `spike/vcam-format`)
Spec: `docs/specs/spec-v0.7.0.md` §0 e §1.3; ADR 0013; handoff `docs/handoff-v0.7.0.md`, seção vcam e adendos

## Spike `vcam-format` (spec §0, CA 1)

Medição de 2026-11-10 com a DLL do spike (SHA-256 `A9812F8179FBD2DD98E238C12724E775BDADDC771E0887808FB1DB1D8E2D5494`), registrada pelo usuário, e o probe publicando um padrão em movimento com o tamanho e o fps desenhados.

Formato anunciado com a câmera virtual iniciada nele, lido no Google Chrome 157 pelo Playwright e no log de entrega da DLL:

| Formato | Chrome | Entregue pela DLL |
|---|---|---|
| 720p30 | 1280x720, 29,9 fps | 30,0 quadros/s |
| 720p60 | 1280x720, 55,2 fps (leitor com canvas) | 60,0 quadros/s |
| 1080p30 | 1920x1080, 29,4 fps | 30,0 quadros/s |
| 1440p30 | 2560x1440, 28,5 fps (leitor com canvas) | 30,0 quadros/s |
| 2160p30 | 3840x2160, 28,9 fps por `track.stats`, 0 descartados | 30,0 quadros/s |

- Nenhum quadro de tamanho diferente do anunciado chegou ao Chrome.
- O leitor com canvas (desenho e leitura de cada quadro) pesa no próprio Chrome: em 2160p30 ele caía para 12,8 fps, enquanto a contagem por `track.stats`, sem canvas, deu 28,9. Os 2 min por formato do CA 2 ficam para a verificação final, contados por `track.stats`.

Achados:
1. **O Frame Server cria a media source quando a câmera virtual inicia, não quando o app abre, e guarda os tipos dessa criação.** Com o canal mudado para 720p sem app aberto, o Chrome abriu a câmera em 1920x1080 e recebeu preto. Mesmo com o tipo do stream trocado, uma nova abertura ainda informou 1920x1080. O formato só muda de forma confiável parando e iniciando a câmera virtual (`IMFVirtualCamera`), o que leva cerca de 5 s.
2. **Troca imediata por `MEStreamFormatChanged` não serve.** O handler aceita o tipo novo, mas o Chrome encerra a faixa (`ended`) cerca de 0,3 s depois, e o app Câmera entra num laço de parar e reiniciar o stream a cada 0,65 s.
3. **Manter o formato antigo com o app aberto** é estável no Chrome: sem erro e sem fim da faixa, com preto se o canal já estiver noutro tamanho. Por isso o agente mantém o celular no formato anunciado enquanto a troca está pendente.
4. **O agente sabe quem está usando a câmera sem a media source escrever no canal.** O monitor de atividade de sensores do Media Foundation (`MFCreateSensorActivityMonitor`) lista a WCam com o pid e o estado `streaming` de cada processo. O Chrome passou de `false` para `true` ao abrir o vídeo e saiu da lista ao fechar. Opera, Teams e Chrome aparecem com `streaming false` só por segurarem o dispositivo. O formato não vem no relatório, mas é o do último início da câmera virtual.

Decisão registrada na ADR 0013 (aceita): o formato novo vale na próxima abertura, com reinício da câmera virtual quando nenhum app recebe vídeo.

## O que foi feito (spec §1.3)

1. **Canal `WCamFrames`, layout versão 2.** O cabeçalho passa de 64 para 128 bytes, com largura, altura e fps do formato e um contador de sequência do formato, para o leitor nunca ver um formato pela metade. As três posições têm tamanho para 3840x2160 NV12 (o canal tem 37,3 MB). `SetFormat` zera o índice do último quadro, então nenhum quadro do formato anterior é lido como do novo.
2. **Formatos:** `FrameFormat` aceita só os cinco do contrato: 720p30, 720p60, 1080p30 (padrão), 1440p30 e 2160p30.
3. **Media source:** o stream lê o formato do canal ao ser criado e anuncia só esse tipo; o pacer e os quadros de espera e de preto usam esse formato.
4. **Troca de formato:** `FormatSwitch` decide sem COM (aplicar, reiniciar ou deixar pendente), e `VirtualCameraHost` executa. O monitor de sensores roda dentro da DLL entre `WcamCameraStart` e `WcamCameraStop` e conta só os processos com `streaming` verdadeiro na WCam. Quando o último para com uma troca pendente, a DLL reinicia a câmera numa thread do pool. Iniciar, parar e reiniciar usam uma trava; o estado e a publicação usam outra, curta, para o reinício de 5 s não segurar `WcamFramePublish` nem `WcamFormatGet`. O canal continua aberto durante o reinício.
5. **API C** (aprovada pelo orquestrador e registrada no handoff):
   - `int WcamFormatSet(uint32 width, uint32 height, uint32 fps)`: `E_INVALIDARG` fora da tabela; antes de `WcamCameraStart`, guarda e vale no início (`S_OK`); com a câmera rodando e nenhum app recebendo vídeo, reinicia a câmera antes de retornar (`S_OK`); com app recebendo, `S_FALSE` (pendente); pedir o formato anunciado cancela a pendência (`S_OK`); falha no reinício devolve o `HRESULT` e deixa `running` em 0.
   - **`WcamFormatSet` pode bloquear cerca de 5 s** no reinício da câmera virtual: o agente chama fora do event loop. O teste `Request_WithNoAppReceivingVideo_RestartsCameraBeforeReturning` cobre a decisão de reiniciar antes de retornar.
   - `int WcamFormatGet(WcamFormatState* state)`: `S_OK` ou `E_POINTER`. Nove `uint32` em sequência: `width`, `height`, `fps` (anunciado), `requestedWidth`, `requestedHeight`, `requestedFps`, `pending`, `streamingApps`, `running`.
   - `WcamFramePublish` aceita só o formato anunciado; outro tamanho volta `E_INVALIDARG`, sem nenhuma regra nova.
   - `WcamCameraStart` e `WcamCameraStop` não mudaram.
6. **Regra que já existia, mantida:** a media source mostra preto quando o canal não tem quadro novo no formato anunciado há 1 s (`FrameTransport.FreshnessTicks`). O congelamento de 3 s e o preto do CA 4 da v0.6.0 continuam no agente.
7. **Probe:** `--moving` desenha o tamanho, o fps e um contador; `--format <w>x<h>@<fps>` define o formato inicial; `--control <arquivo>` aceita `format`, `state` e `stop`; o padrão é publicado sempre no formato anunciado por `WcamFormatGet`, como o agente fará.
8. Versão 0.7.0 em `vcam/Directory.Build.props`.

## Achado do agent: `WcamFramePublish` não bloqueia

Na rodada B do spike `h264-levels`, o pipeline do agente entregou de 6 a 10 quadros/s esperando em `sink.send`. Medido sem câmera, com o mesmo código da seção em processo, produtor contínuo e leitor a 30/s por 60 s: publicação de 1080p com mediana 0,5 ms e máximo 6,2 ms, sem piora ao longo do tempo. Não há fila nem espera pelo consumidor. A conversão I420 para NV12 do agente leva 0,8 ms em 1080p e 3,1 ms em 2160p (mediana). A causa está antes da DLL; repassado à sessão agent.

## Verificação

- `dotnet build`: 0 avisos.
- `dotnet test`: 138 de 138, entre eles `FrameFormatTests`, `FrameChannelTests` (troca de formato, quadro de outro tamanho recusado, leitura no formato antigo recusada, formato sendo escrito), `FormatSwitchTests`, `WcamFormatStateTests` (layout de 36 bytes) e `StreamingMonitorTests`.
- `dotnet publish -r win-x64 -c Release` da DLL e do probe: 0 avisos de trimming ou AOT. DLL final (commit 140e464) publicada em pasta separada, SHA-256 `F093581B0092697B9640397ABCFF245C417706D2EA3A04210C91A5B66166B50D`; a publicação AOT não é reprodutível, então o hash vale para esse arquivo.
- **Não verificado ainda**, porque a DLL final não está registrada:
  - o reinício feito pela própria DLL e o monitor dentro dela no Frame Server;
  - os 2 min por formato (CA 2);
  - o modo de manter o formato no app Câmera, só pelo log;
  - com o usuário, Teams e OBS, inclusive app que segura a câmera sem receber vídeo durante o reinício.
