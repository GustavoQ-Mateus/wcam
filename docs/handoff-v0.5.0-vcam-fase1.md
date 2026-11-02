# Handoff v0.5.0 fase 1, sessão vcam

De: orquestrador
Para: sessão `vcam`
Spec: `docs/specs/spec-v0.5.0.md` (Aprovada)

## Quem é você neste projeto

Sessão implementadora da câmera virtual nativa do Windows, em C# com .NET 10 Native AOT. Leia antes o `CLAUDE.md` inteiro (seções de C#, verificação e git flow), a spec v0.5.0 inteira e o changelog da v0.4.0 (por que o driver do OBS não basta). O orquestrador (`wcam-c8`) decide escopo e contrato; as sessões `agent` e `web` cuidam do Python e do React e não mexem no seu escopo, nem você no delas.

## Onde trabalhar

- Pasta: `G:\Dev\Projetos\WCam\.worktrees\vcam-camera-nativa` (worktree já criado). Faça `cd` para ela e trabalhe só dentro dela.
- Branch: `feature/camera-nativa-vcam`, a partir de `feature/camera-nativa`. PR futuro para `feature/camera-nativa`.
- Seu escopo: `vcam/` e `scripts/register-vcam.ps1` e `scripts/unregister-vcam.ps1`. Não edite `agent/`, `web/`, `locales/`, `docs/` (exceto o relatório) nem `.github/` sem me perguntar; o job de CI `vcam` você me propõe e eu integro.

## Ambiente

- .NET SDK 10.0.401 instalado.
- Visual Studio Build Tools sendo instalado pelo usuário agora. `dotnet build` e `dotnet test` funcionam sem ele; `dotnet publish` com Native AOT precisa do linker do MSVC. Comece pelo que não depende dele.
- Windows 11 build 26200 (tem `MFCreateVirtualCamera`).
- O registro da DLL exige administrador: prepare os scripts e peça ao usuário, por mim, para rodar num terminal de administrador. Não tente elevar sozinho.

## Escopo da fase 1

A seção "Fase 1: prova de conceito" da spec:
1. Solução em `vcam/` com a DLL (`PublishAot`), o probe e os testes xUnit, na estrutura da spec. CsWin32 para Media Foundation, COM e registro.
2. Media source NV12 1920x1080 a 30 fps com padrão de teste animado (barras e contador de quadros), sem dado externo.
3. Exports: `DllGetClassObject`, `DllCanUnloadNow`, `DllRegisterServer`, `DllUnregisterServer`, `WcamCameraStart`, `WcamCameraStop`. `MFCreateVirtualCamera` com `SoftwareCameraSource`, nome "WCam", tempo de vida `Session`, acesso `CurrentUser`.
4. Probe que inicia a câmera e espera Enter.
5. Scripts de registro e remoção.
6. Prova do transporte de quadros: depois que a câmera aparecer com o padrão, teste as opções (a) e (b) da spec com um escritor mínimo de fora do processo (o probe serve), confirmando que a media source, rodando no Frame Server como `LOCAL SERVICE`, consegue ler o que o processo do usuário escreve. Registre o que funcionou e o que falhou.

Fora da fase 1: integração com o agente, fallback, CI final.

## Regras que importam aqui

- Native AOT sem avisos (`IL2xxx`, `IL3xxx`): nada de reflection; COM só por `[GeneratedComInterface]` e `[GeneratedComClass]`.
- Nenhuma exceção escapa de um método COM chamado pelo Frame Server: converta em `HRESULT`. Uma exceção ali derruba o serviço de câmera do Windows.
- Logue a partir da DLL de forma que dê para ler depois (por exemplo `OutputDebugString` ou arquivo em `%ProgramData%\WCam\logs`), porque não há console no processo do Frame Server.
- Se o Native AOT esbarrar em algo que impeça a media source (por exemplo uma interface que o gerador de COM não suporta), pare e me traga o diagnóstico com o erro exato. A troca para C++ é decisão registrada em ADR, não sua sozinha.

## Validação com o usuário

Quando a câmera "WCam" estiver pronta para aparecer, me avise com o passo a passo (registrar como administrador, rodar o probe, abrir os apps). Eu passo ao usuário, que testa no app Câmera do Windows, no novo Teams, no Chrome e no Opera.

## Verificação

A partir de `.worktrees/vcam-camera-nativa/vcam`: `dotnet build` sem avisos, `dotnet test`, e, com o Build Tools instalado, `dotnet publish -r win-x64 -c Release` sem avisos.

## Commits e relatório

Conventional Commits com escopo `vcam`, sem referência a Claude ou Anthropic. Push liberado; PR não. No fim da fase 1, `docs/relatorio-v0.5.0-vcam-fase1.md`: o que foi feito, o resultado de cada app, a decisão do transporte com a evidência, os riscos do Native AOT encontrados e perguntas. Me avise (`wcam-c8`).
