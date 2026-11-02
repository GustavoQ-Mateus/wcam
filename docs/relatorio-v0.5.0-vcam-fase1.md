# Relatório v0.5.0 fase 1, sessão vcam

Status: em andamento (falta publish Native AOT e validação nos apps)
Branch: `feature/camera-nativa-vcam`
Spec: `docs/specs/spec-v0.5.0.md`

## O que foi feito

- Solução `vcam/Wcam.VirtualCamera.sln` com a DLL (`PublishAot`), o probe (Native AOT) e os testes xUnit.
- Interfaces de Media Foundation e funções Win32 pelo CsWin32 0.3.367 com `useComSourceGenerators` (`CsWin32RunAsBuildTask`): todas saem como `[GeneratedComInterface]`, e as classes da DLL usam `[GeneratedComClass]`. `PreserveSig` só em `IClassFactory`, `IMFActivate.ActivateObject`, `IMFGetService` e `IKsControl`.
- Media source: `IMFActivate` (delega `IMFAttributes` a um armazenamento criado por `MFCreateAttributes`), `IMFMediaSourceEx` + `IMFGetService` + `IKsControl`, `IMFMediaStream2` + `IKsControl`. NV12 1920x1080 a 30 fps com barras BT.709, bloco em movimento e contador de quadros.
- Ritmo: `RequestSample` só enfileira o pedido; uma thread com timer de alta resolução entrega uma amostra a cada 1/30 s. Tempo da amostra por `MFGetSystemTime`.
- Exports: `DllGetClassObject`, `DllCanUnloadNow` (sempre `S_FALSE`, o runtime Native AOT não descarrega), `DllRegisterServer`, `DllUnregisterServer`, `WcamCameraStart`, `WcamCameraStop`. CLSID `{F2F06D1E-FA8A-4930-83F6-D85D4E2190C3}`, `ThreadingModel` `Both`.
- Log em `OutputDebugString` e em `%ProgramData%\WCam\logs\vcam.log`.
- Scripts `scripts/register-vcam.ps1` e `scripts/unregister-vcam.ps1`.

## Verificação

- `dotnet build`: 0 avisos.
- `dotnet test`: 14 de 14.
- `dotnet publish -r win-x64 -c Release` da DLL e do probe: 0 avisos de AOT e de trimming. A DLL publicada (2,4 MB) é nativa, sem cabeçalho CLR, e exporta as seis funções (conferido com `dumpbin /exports`).
- Teste no próprio processo, sem registro: a DLL publicada é carregada, `DllGetClassObject` e `IClassFactory` criam o `IMFActivate`, que ativa a media source. O `IMFSourceReader` do Media Foundation leu 90 quadros NV12 1920x1080 de 3.110.400 bytes em 3,00 s, com 2,94 s entre o primeiro e o último timestamp: 30 fps.

Ambiente: o `vcvarsall.bat` chama `vswhere.exe` pelo PATH, e a pasta `C:\Program Files (x86)\Microsoft Visual Studio\Installer` não está no PATH desta máquina. A mensagem de erro ("'vswhere.exe' não é reconhecido") vai parar no caminho do linker que o ILCompiler monta, e o link falha com código 123. Isso acontecia com a instalação Insiders e continuou depois que o usuário a removeu, já com a Community. Contorno usado: chamar `G:\Microsoft\VisualStudio\18\Community\VC\Auxiliary\Build\vcvarsall.bat amd64` e depois publicar com `/p:IlcUseEnvironmentalTools=true`. Correção definitiva: pôr a pasta do Installer no PATH. No CI isso não acontece.

## Resultado nos apps

Registro feito em 2026-11-02 com o script de administrador, autorizado pelo usuário pelo UAC. O probe rodou como usuário comum.

| Consumidor | Resultado | Evidência |
|---|---|---|
| Frame Server | A DLL carrega no serviço | Log: `pid` do `svchost` do serviço `FrameServer` (`NT AUTHORITY\LocalService`) com "media source created" e "media source started"; contador do stream: 30,0 fps entregues, 30,0 pedidos/s, 0 ticks ociosos, 0,9 a 1,8 ms por amostra |
| Lista de câmeras do Media Foundation (`MFEnumDeviceSources`) | Aparece | Nome exposto pelo Windows: "WCam (Câmera Virtual do Windows)", link `\\?\swd#vcamdevapi#...` |
| Chrome (headless, `getUserMedia`) | Funciona | "WCam (Câmera Virtual do Windows)" na lista; `getSettings` 1920x1080, 30 fps, `resizeMode` `none`; 29,9 fps medidos por `requestVideoFrameCallback` em 10 s; as 8 barras em RGB 255,255,255 / 254,255,0 / 0,254,255 / 0,255,1 / 255,0,254 / 255,1,0 / 1,0,255 / 0,0,0 |
| Câmera some ao encerrar | Verificado | Depois de `WcamCameraStop`, `MFEnumDeviceSources` não lista mais a câmera |
| App Câmera do Windows, novo Teams, Opera | Pendente | Teste do usuário |

Observações:
- O Windows acrescenta " (Câmera Virtual do Windows)" ao nome "WCam". O texto que o console vai mostrar precisa considerar isso.
- Quando `MFCreateVirtualCamera` valida a source no processo do probe, a DLL tenta criar `Global\WCamFrames` e recebe acesso negado (falta privilégio ao usuário). Isso fica logado como erro e não atrapalha nada, porque só a instância que roda no serviço precisa da seção. Na fase 2 a seção deve ser criada só no processo do serviço.
- Um cliente de teste em .NET lendo pelo Frame Server parou depois de cerca de 19 quadros, enquanto a DLL seguia entregando 30 fps. A causa provável é o cache de wrappers COM do cliente com as amostras que o Frame Server recicla. É um problema do cliente de teste, não da câmera: o Chrome leu 30 fps sem parar.

### Teste do usuário (sem transporte)

| App | Resultado |
|---|---|
| App Câmera do Windows | Aparece e mostra o padrão, com o contador rodando |
| Novo Teams (app) | Aparece como "WCam (Câmera Virtual do Windows)" e mostra o padrão (contador 000223, espelhado pela opção do Teams) |
| Google Meet no navegador | Aparece e mostra o padrão |
| Opera | Aparece e mostra o padrão |

### Vários consumidores ao mesmo tempo

Achado do usuário: com o app Câmera aberto, a prévia do Teams fica preta, e só funciona depois de fechar o app Câmera.

Diagnóstico pelo `vcam.log` (serviço `FrameServer`, pid 26992):
- Uma única media source é criada (14:05:38) e reaproveitada por todos os apps. Cada app novo provoca um `Start` na mesma source (14:07:21, 14:09:39, 14:11:17), às vezes dois seguidos, sem erro.
- Com o segundo app aberto, a source continua recebendo 30 pedidos/s e entregando 30,0 fps. Quem distribui os quadros entre os apps é o Frame Server; a source vê um consumidor só.
- O stream já declara `MF_DEVICESTREAM_FRAMESERVER_SHARED` = 1.

Conclusão: a limitação é a política de compartilhamento do Frame Server (um cliente com controle; os outros só em modo compartilhado), não a media source. Decisão do orquestrador: nenhum código para vários consumidores. Resta verificar a opção do Windows 11 em Configurações > Bluetooth e dispositivos > Câmeras > (câmera) > "Permitir que vários aplicativos usem a câmera ao mesmo tempo" para a WCam. Resultado: pendente do usuário.

Lacuna de log: há intervalos sem entrega sem que o `Stop` da source seja chamado (14:10:01 a 14:11:17), provavelmente via `IMFMediaStream2.SetStreamState`, que não loga. Uma linha de log em `SetStreamState` está aprovada para a fase 2.

## Transporte de quadros

Pendente do teste real. As duas opções estão no código para a prova:
- (a) `%ProgramData%\WCam\frames.bin`, criado pelo probe (`--write file`), lido pela media source.
- (b) `Global\WCamFrames`, criado pela media source com SDDL `D:(A;;GA;;;SY)(A;;GA;;;LS)(A;;GA;;;BA)(A;;GRGW;;;IU)`, aberto pelo probe (`--write section`).

### Restrição para a fase 2

Na fase 1, como prova, a escrita fica aberta a `INTERACTIVE` (seção) e ao usuário do console (ACL do diretório). No produto isso não pode ficar assim: qualquer usuário logado na máquina conseguiria injetar imagem na câmera. Na fase 2, a escrita fica restrita ao SID do usuário que iniciou o WCam. No caso (b), a media source não conhece esse usuário: o SID tem que chegar a ela por um caminho confiável, e esse caminho será proposto com a decisão do transporte.

## Riscos do Native AOT encontrados

Nenhum bloqueio: o publish Native AOT e a media source no próprio processo funcionaram. Observações:
- `SelfContained=false` no `Directory.Build.props` quebra o publish AOT (NETSDK1102); foi removido.
- É preciso `[assembly: DisableRuntimeMarshalling]` para o código gerado pelo CsWin32 compilar.
- O TFM `net10.0-windows10.0.22000.0` é necessário para as APIs de câmera virtual passarem pelo analisador de plataforma.
- Os wrappers de objetos nativos usados a cada quadro (amostra, buffer) são liberados com `ComObject.FinalRelease()`, para não depender do GC com 3 MB por quadro.

## Perguntas

Nenhuma por enquanto.
