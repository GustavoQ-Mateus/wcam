# 0022. App Windows em C# com o agente Python como processo filho

Status: Aceita, substituída em parte pela ADR 0025 (interface em Avalonia, sem WebView2)
Data: 2026-11-23
Substitui em parte: ADR 0008 e planejamento §3 (bandeja com `pystray` e janela com `pywebview` no agente Python)

## Contexto
A v1.0.0 transforma o WCam num app Windows instalável: bandeja, janela do console e, a pedido do usuário, um atalho na tela com controles rápidos e uma prévia flutuante. O plano original fazia isso em Python (`pystray`, `pywebview`, PyInstaller). O usuário quer ampliar a parte em C# do projeto, e o repositório já tem C# com .NET 10 Native AOT e CsWin32 no `vcam`.

Opções consideradas:
- **Tudo em Python**: menos código novo, mas janelas sempre por cima, exclusão de captura de tela, atalhos globais e prioridade de processo ficam atrás de bibliotecas pequenas ou de chamadas Win32 sem tipos.
- **App em C# com o agente Python como processo filho**: a interface nativa do Windows fica em C#, com acesso direto à API do Windows pelo CsWin32; o agente continua com celular, vídeo e câmera, sem reescrita.
- **Reescrever o agente em C#**: descartado (backlog, "Descartadas").

Escolha do usuário em 2026-11-23: app em C#.

## Decisão
- Nova pasta `app`: .NET 10, WinUI, Native AOT, WebView2, CsWin32 e xUnit, nas mesmas regras de C# do `vcam`.
- O app é o processo principal: abre o agente Python empacotado (PyInstaller em pasta) como processo filho, acompanha a saúde dele, sobe de novo se cair e encerra junto.
- App e agente conversam só pela API do console em `127.0.0.1:8080` (HTTP e SSE). Sem porta nem canal novos.
- A bandeja Python (`pystray`) sai do produto; `pywebview` não entra.
- Textos de interface continuam em `locales/`, lidos também pelo app.
- Se o spike mostrar que o WinUI não publica com Native AOT sem avisos, a alternativa entra por ADR nova com os números.

## Consequências
- Uma sessão nova (`app`) e mais uma verificação de C# no CLAUDE.md.
- O agente ganha um modo filho, sem bandeja, que encerra quando o processo pai morre.
- A interface nativa do Windows (bandeja, atalho na tela, prévia flutuante, prioridade de processo) fica num só lugar.
