# 0024. Atalho na tela em React dentro de janelas do app

Status: Aceita
Data: 2026-11-23
Substitui em parte: ADR 0023 (a prévia flutuante como janela nativa desenhada pelo D3D11)

## Contexto
Na primeira versão do atalho na tela (spec v1.0.0 §1.1), o ícone, o painel de controles rápidos e a prévia flutuante eram nativos do Windows (Win32 e WinUI), com outra cara que o console em React. O usuário viu e não gostou: quer o mesmo front em tudo, com cara de aplicativo, e um polimento pesado do front depois da 1.0.0.

Custos conhecidos do spike (ADR 0023): a prévia desenhada pela página com WebGL2 custa ~3 a 4% da máquina, contra ~1% da nativa; cada WebView2 a mais no mesmo app reaproveita o processo do navegador da janela do console.

## Decisão
- O ícone, o painel e a prévia flutuante passam a ser páginas do `web` (React), cada uma numa janela pequena do app com uma WebView2 que compartilha o ambiente da janela do console.
- O app continua dono do comportamento de janela: sempre por cima, sem roubar o foco no uso pelo mouse, exclusão de captura de tela, Ctrl + arrastar, grudar na borda, atalho global, lugar e tamanho lembrados. A página pede e recebe isso por mensagens do mesmo canal `chrome.webview`, documentadas no contrato antes do código.
- Os controles do painel usam a API do console, como o console já faz; o estado vem do SSE do console.
- A prévia flutuante usa o canal da prévia da ADR 0023 (`preview.*`) e desenha com WebGL2, como a janela do console.
- O menu da bandeja continua o menu nativo do Windows.
- O polimento visual pesado de todo o front, com cara de aplicativo, fica para a v1.4.0.

## Consequências
- Um front só, em React, para console, `/dev` e atalho na tela; as regras de design e os tokens do `web` valem para todos.
- A prévia flutuante custa mais que a nativa (~3 a 4% contra ~1%), medida na validação.
- O código nativo de desenho do ícone e da prévia sai do app; o código de janela fica.
