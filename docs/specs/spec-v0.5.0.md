# Spec v0.5.0, Câmera nativa do Windows

Status: Draft
Branch de integração: `feature/camera-nativa`
Sessões: `vcam` (nova, C# com .NET 10 Native AOT), `agent` (integração Python); `web` sem trabalho
Referências: `docs/planejamento.md` §1 (CA-1, CA-2); ADR 0005 (a ser substituída); changelog da v0.4.0

## Objetivo

Trocar o driver do OBS por uma câmera virtual própria do Windows 11, criada com `MFCreateVirtualCamera` (Media Foundation). Ela aparece com o nome "WCam" para todos os apps, inclusive os empacotados como o novo Microsoft Teams, que na v0.4.0 não enxergou a câmera do OBS. O OBS deixa de ser necessário.

## Por que isso é difícil (e por que há uma prova de conceito)

- A câmera virtual nativa não é um processo nosso. O Windows registra a câmera, e quem produz os quadros é uma *media source*: um objeto COM numa DLL que o serviço Windows Camera Frame Server carrega no **processo dele**, como `LOCAL SERVICE`, na sessão 0.
- O agente roda na sessão do usuário. Os quadros precisam atravessar processos, sessões e contas: memória compartilhada com permissão explícita para `LOCAL SERVICE`.
- O registro da DLL como servidor COM exige administrador.
- Não há como testar isso no CI: o `windows-latest` do GitHub não tem o Frame Server de cliente. A verificação real é na máquina do usuário.

Por isso a versão tem uma fase 1 que só prova que a câmera aparece no Teams com um padrão de teste gerado pela própria DLL, antes de ligar o agente.

## Pré-requisitos na máquina do usuário

- Windows 11 build 22000 ou maior (a máquina tem 26200).
- .NET SDK 10 (instalado: 10.0.401).
- Visual Studio Build Tools com "Desenvolvimento para desktop com C++" e Windows SDK: o Native AOT usa o linker do MSVC. Ainda não instalado em 2026-11-02.
- Terminal de administrador uma vez, para registrar a DLL em desenvolvimento.

## Linguagem: C# com .NET 10 Native AOT

A media source precisa ser uma DLL nativa carregada pelo Frame Server. Avaliação feita com o usuário:
- C# com .NET 10 Native AOT: gera DLL nativa sem runtime instalado; `[UnmanagedCallersOnly]` exporta `DllGetClassObject`, `DllRegisterServer` e a API C; COM gerado por código (`[GeneratedComInterface]`, `[GeneratedComClass]`, `ComWrappers`) implementa as interfaces sem reflection; as interfaces de Media Foundation e as funções Win32 vêm do CsWin32. É a stack de trabalho do usuário. **Escolhida.**
- C++: caminho dos exemplos oficiais, mas fora da stack do usuário. Fica como alternativa se a fase 1 provar que o Native AOT não serve, registrada em ADR.
- Go: descartado. A DLL levaria o runtime do Go (GC e threads próprias) para dentro do processo do serviço, só um runtime por processo, e COM todo à mão.

Riscos específicos: poucas referências públicas de media source em Native AOT; restrições de trimming (nada de reflection); depurar código dentro do processo do Frame Server. A fase 1 existe para expor esses riscos cedo.

## Estrutura nova

```
vcam/                            solução .NET da sessão vcam
  Wcam.VirtualCamera.sln
  src/Wcam.VirtualCamera/        DLL nativa (PublishAot, OutputType Library)
    MediaSource.cs               IMFMediaSourceEx, IKsControl, atributos da câmera
    MediaStream.cs               IMFMediaStream2, entrega de amostras NV12
    FrameChannel.cs              leitura dos quadros publicados pelo agente
    TestPattern.cs               padrão de teste da fase 1
    Exports.cs                   DllGetClassObject, DllRegisterServer, DllUnregisterServer e a API C para o agente
    NativeMethods.txt            lista do CsWin32
  src/Wcam.VirtualCamera.Probe/  executável de teste da fase 1 (também Native AOT)
  tests/Wcam.VirtualCamera.Tests/  xUnit: canal de quadros, seqlock, padrão de teste
scripts/
  register-vcam.ps1              registra a DLL (administrador)
  unregister-vcam.ps1
```

## Fase 1: prova de conceito (sessão vcam)

- Media source NV12 1920x1080 a 30 fps que gera um padrão de teste animado (barras e um contador de quadros), sem nenhum dado externo.
- Uma API C exportada pela mesma DLL (`WcamCameraStart`, `WcamCameraStop`) chama `MFCreateVirtualCamera` com tipo `SoftwareCameraSource`, nome "WCam", tempo de vida `Session` e acesso `CurrentUser`, e `Start` na câmera.
- Um executável mínimo de teste (`Wcam.VirtualCamera.Probe.exe`) chama a API e fica rodando até Enter.
- Registro e remoção por script de administrador.

Saída da fase 1:
- "WCam" aparece e mostra o padrão no app Câmera do Windows, no novo Teams, no Chrome e no Opera;
- a câmera some quando o probe termina;
- `docs/relatorio-v0.5.0-vcam-fase1.md`, com a decisão sobre o transporte de quadros (próxima seção) justificada por teste real.

O usuário valida a fase 1 antes da fase 2.

## Transporte de quadros (decidido na fase 1)

O canal entre o agente (sessão do usuário) e a media source (sessão 0, `LOCAL SERVICE`) é memória compartilhada. A fase 1 testa e escolhe entre:

- (a) arquivo mapeado em `%ProgramData%\WCam\frames.bin` com ACL para o usuário e para `LOCAL SERVICE`;
- (b) seção nomeada em `Global\`, criada pela media source com descritor de segurança que dá escrita ao usuário (criar objeto em `Global\` exige um privilégio que usuários comuns não têm, por isso quem cria é o lado do serviço);
- outra, se as duas falharem, com justificativa.

Formato fixo, nas duas opções: cabeçalho (magic, versão, largura, altura, fourcc NV12, índice do quadro, timestamp) e três posições de quadro NV12 rotativas, com sequência de escrita para leitura sem rasgo (seqlock). A escolha vira a ADR 0011, que substitui a ADR 0005.

## Fase 2: integração com o agente (sessões vcam e agent)

- vcam: a media source lê o quadro mais recente do canal; sem quadro novo há mais de 1 s, entrega preto. A API C ganha a escrita de quadro (`WcamFramePublish`), usada pelo agente.
- agent: `virtualcam/media_foundation_sink.py`, implementação do `VirtualCameraSink` via `ctypes` sobre a API C da DLL. O I420 decodificado vira NV12 por reorganização dos planos de cor (sem conversão de cor, como na v0.4.0).
- `WCAM_VIRTUAL_CAMERA`: `auto` passa a escolher `media_foundation` quando a DLL está registrada e o Windows é 22000 ou maior; senão, `obs`; senão, `fake`. `virtualCamera.backend` ganha o valor `media_foundation`.
- O agente inicia a câmera ao subir e a remove ao encerrar (tempo de vida `Session`).

## CI

- Job `vcam` em `windows-latest`: `dotnet test` e `dotnet publish -r win-x64 -c Release` com Native AOT, sem avisos de trimming ou AOT; DLL e probe como artefatos.
- Os testes do agente com a DLL real só rodam na máquina do usuário; no CI, o `media_foundation_sink` é testado com uma DLL falsa ou com a API simulada.

## Textos

Ficam com o orquestrador, a partir dos relatórios: o nome da câmera ("WCam"), as mensagens de terminal e console sobre o backend e o motivo de indisponibilidade (DLL não registrada, Windows antigo). Seguem o glossário de `docs/planejamento.md` §5.7.

## Fora do escopo

Instalador (v1.0.0), assinatura de código da DLL, console definitivo (v0.6.0), áudio, Windows 10.

## Critérios de aceitação

1. Fase 1 validada pelo usuário: "WCam" com o padrão de teste no app Câmera, no novo Teams, no Chrome e no Opera.
2. CA-1 completo com o celular ao vivo, pelo usuário: "WCam" mostra a imagem do celular no novo Teams (app), no Teams web, no Chrome (webcamtests e Instagram), no Opera e no app Câmera do Windows. App não disponível fica registrado.
3. A câmera "WCam" existe só enquanto o WCam está aberto; ao fechar, ela some da lista dos apps.
4. Sem celular, ou sem quadro novo há mais de 1 s, a câmera mostra preto, nunca imagem congelada.
5. Caminho sem perda: teste confirma que o NV12 publicado pelo agente chega à media source com os mesmos bytes.
6. Fallback: com a DLL não registrada, o agente usa o backend `obs` e diz o motivo; sem os dois, `fake`, e diz o motivo.
7. O e2e de qualidade continua acima de 0,98 (no compose, com o sink falso).
8. CI verde, incluindo o job `vcam`, com o publish Native AOT sem avisos; versão 0.5.0 no agente, no web e no projeto .NET.
9. ADR 0011 aceita, substituindo a 0005; contrato atualizado (`backend` `media_foundation`, motivos novos).

## Decisões em aberto para o usuário

1. Uma sessão nova `vcam` para o projeto .NET (recomendado: escopo, linguagem e ferramentas diferentes), ou o .NET também com a sessão `agent`?
2. Instalar o Visual Studio Build Tools (C++ desktop e Windows SDK) antes de começar. Sem ele, o publish Native AOT não linka.
