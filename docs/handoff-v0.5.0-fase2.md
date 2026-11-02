# Handoff v0.5.0 fase 2, sessões vcam e agent

De: orquestrador (`wcam-98`)
Spec: `docs/specs/spec-v0.5.0.md` (Aprovada), seção "Fase 2" e "Decisões registradas"
ADR: `docs/adr/0011-camera-nativa-media-foundation.md`
Contrato: `docs/contrato.md` (versão 0.5.0)

As duas sessões trabalham ao mesmo tempo. O ponto de encontro é a API C da DLL, definida abaixo. Qualquer mudança nela passa por mim antes do código.

## API C entre agente e DLL

Exportada por `Wcam.VirtualCamera.dll`, chamada pelo agente com `ctypes` (convenção `stdcall`, retorno `HRESULT` como `int32`):

| Função | Assinatura | Comportamento |
|---|---|---|
| `WcamCameraStart` | `HRESULT WcamCameraStart(void)` | grava o SID do usuário atual pelo caminho confiável do item 1 da vcam, cria e inicia a câmera "WCam" |
| `WcamCameraStop` | `HRESULT WcamCameraStop(void)` | remove a câmera; idempotente |
| `WcamFramePublish` | `HRESULT WcamFramePublish(const uint8_t* nv12, uint32_t length, uint32_t width, uint32_t height)` | copia um quadro NV12 para a seção; `E_INVALIDARG` se `length != width*height*3/2` ou se o tamanho for diferente de 1920x1080; `S_FALSE` se a seção ainda não existe (o agente segue sem erro) |

O agente nunca abre a seção diretamente: só a DLL conhece o formato do canal.

## Sessão vcam

Pasta: `G:\Dev\Projetos\WCam\.worktrees\vcam-camera-nativa`, branch `feature/camera-nativa-vcam`. Comece com `git merge origin/feature/camera-nativa`.

1. **Primeiro, a prova do caminho do SID.** Implemente a proposta do relatório (entrada de registro ou propriedade do dispositivo gravada antes do `Start`) e prove na máquina do usuário que a media source, no Frame Server, lê o SID. Me traga o resultado antes de seguir. Se não funcionar, me traga as alternativas com o custo de cada uma.
2. Seção `Global\` com DACL: escrita só para o SID do dono; leitura e escrita para `SYSTEM` e `LOCAL SERVICE`; nada para `INTERACTIVE` ou para outros usuários. Sem SID, a source não cria a seção e entrega preto.
3. `WcamFramePublish` na API C, como na tabela acima.
4. Quadro mais recente com menos de 1 s, senão preto. O padrão de teste sai do caminho do produto e fica só no probe (`--pattern`).
5. Log em `SetStreamState`.
6. Testes xUnit: DACL montado só com os SIDs esperados, validação de tamanho no `WcamFramePublish`, regra de 1 s.
7. Proposta do job de CI `vcam` (YAML no relatório ou em mensagem): eu integro em `.github/workflows/ci.yml`. O job compila, testa e publica com Native AOT sem avisos, com `vswhere` no PATH.
8. Versão 0.5.0 no projeto .NET.

## Sessão agent

Pasta: `G:\Dev\Projetos\WCam\.worktrees\agent-camera-nativa` (worktree novo), branch `feature/camera-nativa-agent`.

1. `virtualcam/media_foundation_sink.py`: implementação do `VirtualCameraSink` com `ctypes` sobre a API C. Carrega a DLL de `%ProgramFiles%\WCam\Wcam.VirtualCamera.dll` (caminho em configuração, `WCAM_VCAM_DLL`, com esse padrão).
2. I420 para NV12: o plano Y é copiado como está, e U e V são intercalados (UVUV). É só reorganização, sem conversão de cor. Faça com numpy, fora do event loop, no worker que já existe. Teste: Y igual byte a byte e cada par UV na posição certa.
3. Escolha do backend em `auto`: `media_foundation` se o Windows for 22000 ou maior e a DLL existir e iniciar; senão `obs`; fora do Windows, `fake`. Preencha `fallbackReason` como no contrato. Teste cada caminho com DLL e plataforma simuladas.
4. Status e terminal: `virtualCamera.backend` `media_foundation` e o nome "WCam" em `terminal.virtual_camera_active` (`{name}`). Use `terminal.virtual_camera_fallback` quando cair para o OBS.
5. A câmera é iniciada quando o agente sobe e removida quando ele encerra, inclusive por Ctrl+C e SIGTERM (`WcamCameraStop` no encerramento).
6. Versão 0.5.0.

Testes do agent com a DLL real só rodam no Windows do usuário; no CI, use um duplo da API C.

## Verificação

- vcam: `dotnet build` sem avisos, `dotnet test`, `dotnet publish -r win-x64 -c Release` sem avisos.
- agent: `uv run ruff check`, `uv run ruff format --check`, `uv run pyright`, `uv run pytest`.

## Teste final, com o usuário

Agente com o backend `media_foundation`, celular ao vivo e a "WCam" mostrando a imagem do celular no novo Teams, no Meet, no Opera e no app Câmera (CA 2 da spec), mais a coleta de 10 minutos como na v0.4.0.

## Relatórios

`docs/relatorio-v0.5.0-vcam.md` e `docs/relatorio-v0.5.0-agent.md`, no formato de sempre. Commits sem referência a Claude ou Anthropic; push liberado; PR não. Me avisem (`wcam-98`).
