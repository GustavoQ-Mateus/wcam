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

Ambiente: a máquina tem duas instalações do MSVC, Visual Studio 18 Insiders em `C:\Program Files` e Community em `G:\Microsoft\VisualStudio\18\Community`. O ILCompiler escolhe a Insiders (`vswhere -latest -prerelease`), e o `vcvarsall` dela falha ("'vswhere.exe' não é reconhecido"). Contorno: rodar o publish depois do `vcvarsall.bat amd64` da Community, com `/p:IlcUseEnvironmentalTools=true`. No CI isso não acontece. A outra saída é reparar ou remover a Insiders.

## Resultado nos apps

Pendente.

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
