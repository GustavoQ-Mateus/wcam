# 0025. Interface do app em Avalonia UI, com identidade visual própria

Status: Aceita
Data: 2026-11-23
Substitui: ADR 0024 inteira e, em parte, a ADR 0022 (WinUI e WebView2) e a ADR 0023 (canal da prévia para a página)

## Contexto
Depois de ver a primeira versão do app, o usuário apontou o problema principal: o console funcionava bem, mas dentro da janela continuava parecendo uma página, com componentes soltos, sem identidade visual nem marca. E o ícone na tela parecia velho. O WinUI amarra o visual ao Windows; a WebView2 com o console React mantém a cara de página.

Opções avaliadas com o usuário: WinUI redesenhado, WPF (sem Native AOT), .NET MAUI (usa WinUI no Windows), Electron ou Tauri (saem do C#) e Avalonia UI. O Avalonia é C#, tem desenho próprio (Skia) com visual totalmente nosso, roda em Windows, Linux e macOS com o mesmo código (prepara a 1.x) e está em evolução ativa (versão 12.1, de 2026). O suporte a Native AOT na versão atual é confirmado no spike.

Escolha do usuário em 2026-11-23: Avalonia.

## Decisão
- A interface do app (janela principal, bandeja, ícone na tela, painel e prévia flutuante) é feita em Avalonia UI, em C#, na pasta `app`. Sem WebView2 e sem páginas web dentro do app.
- A janela principal é um aplicativo de verdade, não o console embutido: tem a sua própria estrutura (barra de título, navegação, áreas fixas) e cobre o que o console faz para o usuário, inclusive a biblioteca e a linha do tempo de vídeo. O `/dev` continua só no navegador, como ferramenta de desenvolvimento.
- Identidade visual própria do WCam, definida antes das telas: marca, ícone do app, tipografia, grade, componentes e movimento, a partir dos tokens de cor do planejamento §5.6. Registrada em `docs/design-v1.0.0.md`.
- O app fala com o agente pela API do console (HTTP e SSE em `127.0.0.1:8080`), como o console React; as prévias leem a seção `Local\WCamFrames` (ADR 0023) e desenham pelo próprio Avalonia.
- O console React continua para o navegador e o `/cam` não muda. O polimento do front web fica para a v1.4.0, já com a identidade definida aqui.
- Ficam valendo da ADR 0022: o agente Python como processo filho, o Job Object, o modo `--child` e a prioridade pelo próprio agente.

## Consequências
- O canal da prévia para a página e as mensagens do atalho em React saem do contrato antes de qualquer entrega.
- Uma parte maior da 1.0.0 vai para a sessão app; a sessão web fica quase sem trabalho nesta versão.
- O app passa a reimplementar telas que o console React já tem; o contrato da API do console é a fonte comum dos dois.
