# 0008. App Windows de bandeja para o usuário final; Docker só em desenvolvimento e CI

Status: Aceita
Data: 2026-10-31

## Contexto
No Windows, o Docker roda containers Linux numa VM (WSL2). Um container não cria câmera virtual visível para os apps do Windows, fica atrás de NAT para as portas UDP dinâmicas do WebRTC e não conhece o IP do PC na rede Wi-Fi, que o QR precisa conter. Exigir Docker Desktop para usar uma webcam é atrito excessivo. No celular, o usuário não deve instalar nada.

## Decisão
- PC: app Windows. Executável PyInstaller, ícone na bandeja (pystray), console numa janela WebView2 (pywebview), instalador Inno Setup que cria a regra de firewall.
- Celular: só a página web no navegador padrão.
- Docker Compose apenas para desenvolvimento e CI: agente headless, web e Playwright.

## Consequências
- A câmera virtual real só é testada fora do Docker, no Windows.
- O CI precisa de um runner Windows para o agente.
- Contribuidores em Linux sobem o ambiente com um comando.
- O teste com celular real usa o agente nativo (`uv run wcam`), não o compose.
